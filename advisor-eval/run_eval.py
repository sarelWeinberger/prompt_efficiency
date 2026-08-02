#!/usr/bin/env python3
"""Run one advisor system over a dataset split and write predictions jsonl.

Systems:
  rules   deterministic regex baseline (no model)
  gemma   gemma-4-E2B-it via a local llama.cpp server (OpenAI-compatible API)
  hybrid  rules first; model only for soft-indicator "ambiguous" prompts
  judge   claude-opus-5 via the Anthropic API (reference judge, NOT ground truth)

Usage:
  run_eval.py --system gemma --data data/holdout.jsonl --out results/holdout/gemma.jsonl \
      [--url http://127.0.0.1:8080] [--constrained] [--limit N]

Determinism: local model runs use temperature=0, seed=0. The Anthropic API
does not accept sampling parameters on Claude 5 models; the judge is run
with default settings and is therefore not bit-deterministic (recorded in
PROTOCOL.md).
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from advisor.prompt import SYSTEM_PROMPT, build_messages  # noqa: E402
from advisor.rules import rules_predict, rules_detect, is_ambiguous  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = json.load(open(os.path.join(HERE, "schema.json")))


def parse_json_loose(text):
    """Extract the first JSON object from model output."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def call_llama(url, prompt_text, constrained, max_tokens=1400):
    import requests
    body = {
        "model": "gemma-4-E2B-it",
        "messages": build_messages(prompt_text),
        "temperature": 0,
        "seed": 0,
        "max_tokens": max_tokens,
    }
    if constrained:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "advisor", "schema": SCHEMA},
        }
    t0 = time.monotonic()
    r = requests.post(url.rstrip("/") + "/v1/chat/completions", json=body, timeout=600)
    dt = time.monotonic() - t0
    r.raise_for_status()
    d = r.json()
    text = d["choices"][0]["message"]["content"]
    usage = d.get("usage", {})
    timings = d.get("timings", {})
    return text, {
        "latency_s": round(dt, 3),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "prompt_ms": timings.get("prompt_ms"),
        "predicted_ms": timings.get("predicted_ms"),
    }


_ANTHROPIC = None


def call_judge(prompt_text):
    global _ANTHROPIC
    if _ANTHROPIC is None:
        import anthropic
        for line in open(os.path.join(HERE, "..", ".env")):
            if line.startswith("ANTHROPIC_API_KEY="):
                os.environ.setdefault("ANTHROPIC_API_KEY",
                                      line.split("=", 1)[1].strip())
        _ANTHROPIC = anthropic.Anthropic()
    msgs = build_messages(prompt_text)
    t0 = time.monotonic()
    resp = _ANTHROPIC.messages.create(
        model="claude-opus-5",
        max_tokens=4000,
        system=[{"type": "text", "text": msgs[0]["content"],
                 "cache_control": {"type": "ephemeral"}}],
        messages=[msgs[1]],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    dt = time.monotonic() - t0
    text = next(b.text for b in resp.content if b.type == "text")
    return text, {
        "latency_s": round(dt, 3),
        "prompt_tokens": resp.usage.input_tokens,
        "completion_tokens": resp.usage.output_tokens,
        "cache_read": resp.usage.cache_read_input_tokens,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True,
                    choices=["rules", "gemma", "hybrid", "judge"])
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--constrained", action="store_true",
                    help="enforce the JSON schema via llama.cpp grammar")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.data)]
    if args.limit:
        rows = rows[:args.limit]

    done = set()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    if args.resume and os.path.exists(args.out):
        done = {json.loads(l)["id"] for l in open(args.out)}
    mode = "a" if args.resume else "w"

    with open(args.out, mode) as f:
        for i, ex in enumerate(rows):
            if ex["id"] in done:
                continue
            prompt = ex["prompt"]
            rec = {"id": ex["id"], "system": args.system,
                   "constrained": args.constrained}
            try:
                if args.system == "rules":
                    rec["parsed"] = rules_predict(prompt)
                    rec["meta"] = {"latency_s": 0.0}
                elif args.system == "judge":
                    text, meta = call_judge(prompt)
                    rec["raw"], rec["meta"] = text, meta
                    rec["parsed"] = parse_json_loose(text)
                elif args.system == "gemma":
                    text, meta = call_llama(args.url, prompt, args.constrained)
                    rec["raw"], rec["meta"] = text, meta
                    rec["parsed"] = parse_json_loose(text)
                else:  # hybrid
                    hits = rules_detect(prompt)
                    if hits:
                        rec["parsed"] = rules_predict(prompt)
                        rec["meta"] = {"latency_s": 0.0, "route": "rules"}
                    elif not is_ambiguous(prompt):
                        rec["parsed"] = {"recommendation": "no_change",
                                         "risks": [], "revised_prompt": None,
                                         "confidence": 0.8}
                        rec["meta"] = {"latency_s": 0.0, "route": "clean"}
                    else:
                        text, meta = call_llama(args.url, prompt,
                                                args.constrained)
                        meta["route"] = "model"
                        rec["raw"], rec["meta"] = text, meta
                        rec["parsed"] = parse_json_loose(text)
            except Exception as e:  # record failures, keep going
                rec["error"] = repr(e)
                rec["parsed"] = None
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            print(f"[{i+1}/{len(rows)}] {ex['id']} -> "
                  f"{(rec.get('parsed') or {}).get('recommendation', 'PARSE_FAIL')}")


if __name__ == "__main__":
    main()
