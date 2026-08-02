#!/usr/bin/env python3
"""Thinking-mode probe: does Gemma-4's thinking mode help enough to justify
its latency for this task?

Per the model card, thinking is enabled by including the `<|think|>` token at
the start of the system prompt. Runs a fixed 10-example holdout subset with
thinking ON (unconstrained decoding so the thinking block can stream) and
compares recommendation agreement + latency to the no-thinking runs.

Usage: probe_thinking.py --data data/holdout.jsonl --out results/holdout/think_probe.jsonl
"""
import argparse
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from advisor.prompt import SYSTEM_PROMPT  # noqa: E402
from run_eval import parse_json_loose  # noqa: E402
from bench_bf16 import SUBSET  # same frozen 10-example subset  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    args = ap.parse_args()
    rows = {json.loads(l)["id"]: json.loads(l) for l in open(args.data)}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        for sid in SUBSET:
            ex = rows[sid]
            body = {
                "model": "gemma-4-E2B-it",
                "messages": [
                    {"role": "system", "content": "<|think|>" + SYSTEM_PROMPT},
                    {"role": "user",
                     "content": "PROMPT TO REVIEW:\n<<<\n" + ex["prompt"] + "\n>>>"},
                ],
                "temperature": 0, "seed": 0, "max_tokens": 3000,
            }
            t0 = time.monotonic()
            r = requests.post(args.url + "/v1/chat/completions", json=body,
                              timeout=1200)
            dt = time.monotonic() - t0
            d = r.json()
            text = d["choices"][0]["message"]["content"]
            # strip a thinking block if the template surfaces one
            vis = text.split("<|/think|>")[-1] if "<|/think|>" in text else text
            rec = {"id": sid, "system": "gemma-think", "raw": text,
                   "parsed": parse_json_loose(vis),
                   "meta": {"latency_s": round(dt, 1),
                            "completion_tokens": d.get("usage", {}).get("completion_tokens")}}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            print(sid, round(dt), "->",
                  (rec["parsed"] or {}).get("recommendation", "PARSE_FAIL"))


if __name__ == "__main__":
    main()
