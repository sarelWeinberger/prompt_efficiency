#!/usr/bin/env python3
"""Reasoning-token schema discovery (design §12).

For every model: one trivial and one moderate coding prompt through pi, with a
raw wire capture proxy between pi and Together. Documents, per model:
- raw Together usage fields (chat completions)
- whether reasoning tokens are explicit, and where
- whether cached-token fields appear
- the effective thinking/reasoning request parameters pi sends
- pi's normalized usage mapping
Writes results/schema_discovery/<model>.json and a summary markdown.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import NODE_BIN, ROOT, load_models, run_env
from parse_pi_usage import parse_events, parse_usage
from reset_workspace import reset_slot

OUT = ROOT / "results/schema_discovery"
CAPTURE = OUT / "pi_wire_capture.jsonl"
EXT = ROOT / "benchmark/gateway/pi-capture-extension.js"
PROXY_PORT = 8902


def start_proxy():
    proc = subprocess.Popen(
        [str(NODE_BIN / "node"), str(ROOT / "benchmark/gateway/capture-proxy.js"),
         str(PROXY_PORT), "https://api.together.xyz", str(CAPTURE), "pi-discovery"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    return proc


def run_pi_probe(model, prompt, cwd, thinking="medium", timeout=180):
    cmd = [str(NODE_BIN / "pi"), "--provider", "together", "--model", model,
           "--mode", "json", "-p", "--no-session", "--thinking", thinking,
           "-e", str(EXT), prompt]
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       timeout=timeout, env=run_env(), stdin=subprocess.DEVNULL)
    return parse_events(p.stdout.splitlines())


def capture_entries(offset):
    if not CAPTURE.exists():
        return [], 0
    text = CAPTURE.read_text()
    entries = []
    for ln in text.splitlines():
        try:
            entries.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    return entries[offset:], len(entries)


def analyze_model(model_id, slot):
    findings = {"model": model_id, "probes": {}}
    offset = 0
    _, offset = capture_entries(0)

    for name, prompt, cwd in (
            ("trivial", "Reply with exactly: OK", ROOT),
            ("moderate",
             "Fix the discount bug in shop/discount.py: apply_discount(price, pct) "
             "must return the price AFTER the discount. Run "
             "python3 -m unittest discover -s tests -t . and stop when tests pass.",
             slot)):
        if name == "moderate":
            reset_slot(slot, "py-low-01")
        try:
            events = run_pi_probe(model_id, prompt, cwd)
        except subprocess.TimeoutExpired:
            findings["probes"][name] = {"error": "timeout"}
            continue
        usage = parse_usage(events)
        new, offset = capture_entries(offset)
        reqs = [e for e in new if e.get("kind") == "request"
                and isinstance(e.get("body"), dict)
                and e["body"].get("model") == model_id]
        resps = [e for e in new if e.get("kind") == "response"]
        raw_usages = []
        for r in resps:
            raw_usages += r.get("usages") or []
            if isinstance(r.get("body"), dict) and r["body"].get("usage"):
                raw_usages.append(r["body"]["usage"])
        reasoning_fields = set()
        cached_fields = set()
        for u in raw_usages:
            for holder, fields in (("completion_tokens_details", u.get("completion_tokens_details")),
                                   ("output_tokens_details", u.get("output_tokens_details"))):
                if isinstance(fields, dict) and "reasoning_tokens" in fields:
                    reasoning_fields.add(f"{holder}.reasoning_tokens")
            for holder, fields in (("prompt_tokens_details", u.get("prompt_tokens_details")),
                                   ("input_tokens_details", u.get("input_tokens_details"))):
                if isinstance(fields, dict) and "cached_tokens" in fields:
                    cached_fields.add(f"{holder}.cached_tokens")
        req_reasoning = None
        if reqs:
            b = reqs[-1]["body"]
            req_reasoning = {k: b.get(k) for k in
                             ("reasoning", "reasoning_effort", "thinking",
                              "chat_template_kwargs", "max_tokens") if k in b}
        findings["probes"][name] = {
            "pi_normalized_totals": usage["totals"],
            "raw_usage_samples": raw_usages[-2:],
            "raw_reasoning_fields": sorted(reasoning_fields),
            "raw_cached_fields": sorted(cached_fields),
            "effective_request_reasoning_params": req_reasoning,
            "n_wire_requests": len(reqs),
        }

    # classify per design §12
    statuses = []
    for p in findings["probes"].values():
        t = p.get("pi_normalized_totals") or {}
        statuses.append(t.get("reasoning_token_status", "parse_error"))
    raw_explicit = any(p.get("raw_reasoning_fields") for p in findings["probes"].values()
                       if isinstance(p, dict))
    if raw_explicit and "explicit" in statuses:
        findings["reasoning_token_status"] = "explicit"
    elif raw_explicit:
        findings["reasoning_token_status"] = "explicit_upstream_only"
    elif "explicit" in statuses:
        findings["reasoning_token_status"] = "explicit"
    elif all(s == "parse_error" for s in statuses):
        findings["reasoning_token_status"] = "parse_error"
    else:
        findings["reasoning_token_status"] = "included_in_output_but_not_separable"
    return findings


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    EXT.write_text(
        'export default function (pi) {\n'
        f'  pi.registerProvider("together", {{ baseUrl: "http://127.0.0.1:{PROXY_PORT}/v1" }});\n'
        '}\n')
    proxy = start_proxy()
    slot = Path("/tmp/pi-prompt-benchmark/slot-discovery")
    results = []
    try:
        models = [m["id"] for m in load_models()]
        if len(sys.argv) > 1:
            models = [m for m in models if m in sys.argv[1:]]
        for mid in models:
            print("discovering", mid, flush=True)
            f = analyze_model(mid, slot)
            results.append(f)
            (OUT / (mid.replace("/", "__") + ".json")).write_text(json.dumps(f, indent=1))
            print(" ", mid, "->", f["reasoning_token_status"], flush=True)
    finally:
        proxy.terminate()

    lines = ["# Reasoning-token schema discovery (pi -> Together, chat completions)", "",
             "| model | status | raw reasoning field | raw cached field | effective request params |",
             "|---|---|---|---|---|"]
    for f in results:
        probes = [p for p in f["probes"].values() if isinstance(p, dict) and "error" not in p]
        rf = sorted({x for p in probes for x in p.get("raw_reasoning_fields", [])})
        cf = sorted({x for p in probes for x in p.get("raw_cached_fields", [])})
        rp = next((p.get("effective_request_reasoning_params") for p in probes
                   if p.get("effective_request_reasoning_params")), None)
        lines.append(f"| {f['model']} | {f['reasoning_token_status']} | "
                     f"{', '.join(rf) or '—'} | {', '.join(cf) or '—'} | "
                     f"`{json.dumps(rp)}` |")
    (OUT / "SCHEMA-DISCOVERY.md").write_text("\n".join(lines) + "\n")
    print("wrote", OUT / "SCHEMA-DISCOVERY.md")


if __name__ == "__main__":
    main()
