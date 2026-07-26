#!/usr/bin/env python3
"""Claude Code compatibility smoke suite (design §3).

Runs, per model, empirical probes through the gateway chain
(claude/curl -> :8903 anthropic capture -> :4000 litellm -> :8901 together capture)
and classifies 14 capabilities as supported / partially_supported / unsupported /
adapter_error / unknown.  Writes results/compatibility/cc_compat.json + .md.

A model must pass the tool-loop probe (D) before it may enter the Claude Code
benchmark (design §3: "A text response alone is not enough").
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NODE_BIN = Path.home() / ".nvm/versions/node/v22.23.1/bin"
CLAUDE = NODE_BIN / "claude"
GATEWAY = "http://127.0.0.1:8903"
CAPTURE = ROOT / "results/raw/gateway-live/together_capture.jsonl"
OUT_DIR = ROOT / "results/compatibility"
SMOKE_TIMEOUT = 150

CAPS = [
    "text_completion", "system_prompt", "streaming", "tool_definition",
    "single_tool_call", "sequential_tool_calls", "tool_result_continuation",
    "long_output", "reasoning_token_reporting", "cached_input_reporting",
    "error_propagation", "timeout_handling", "stop_reason", "context_continuation",
]


def env_key(name):
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError(f"{name} not in .env")


def messages_call(model, payload, stream=False, timeout=90):
    body = {"model": model, "max_tokens": 512, **payload}
    if stream:
        body["stream"] = True
    req = urllib.request.Request(
        GATEWAY + "/v1/messages",
        data=json.dumps(body).encode(),
        headers={
            "x-api-key": env_key("GATEWAY_MASTER_KEY"),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:2000]
    except Exception as e:
        return -1, str(e)


def capture_tail(n=200):
    if not CAPTURE.exists():
        return []
    lines = CAPTURE.read_text().splitlines()[-n:]
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    return out


def claude_agent_run(model, workdir, prompt, max_turns=8, timeout=SMOKE_TIMEOUT):
    home = workdir / "home"
    work = workdir / "work"
    for d in (home / ".claude", work):
        d.mkdir(parents=True, exist_ok=True)
    (home / ".claude.json").write_text(json.dumps({"hasCompletedOnboarding": True}))
    (home / ".claude" / "settings.json").write_text(
        json.dumps({"permissions": {"defaultMode": "acceptEdits"}}))
    env = {
        "HOME": str(home),
        "PATH": f"{NODE_BIN}:/usr/bin:/bin",
        "ANTHROPIC_BASE_URL": GATEWAY,
        "ANTHROPIC_AUTH_TOKEN": env_key("GATEWAY_MASTER_KEY"),
        "ANTHROPIC_SMALL_FAST_MODEL": model,
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "DISABLE_AUTOUPDATER": "1",
    }
    cmd = [str(CLAUDE), "-p", prompt, "--output-format", "json", "--model", model,
           "--permission-mode", "acceptEdits", "--max-turns", str(max_turns)]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True,
                           timeout=timeout, stdin=subprocess.DEVNULL)
        wall = time.time() - t0
        try:
            data = json.loads(p.stdout)
        except json.JSONDecodeError:
            return {"ok": False, "error": f"no_json rc={p.returncode} stderr={p.stderr[-300:]}",
                    "wall_s": wall}
        return {"ok": not data.get("is_error"), "data": data, "wall_s": wall, "work": work}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "wall_s": time.time() - t0}


def smoke_model(model_id, alias):
    r = {"model": model_id, "alias": alias, "caps": {}, "evidence": {}}
    caps, ev = r["caps"], r["evidence"]

    # A. text completion + system prompt + stop reason
    status, raw = messages_call(alias, {
        "system": "You are a terse assistant. Always answer in uppercase.",
        "messages": [{"role": "user", "content": "Say exactly: ok"}]})
    try:
        d = json.loads(raw)
        text = "".join(c.get("text", "") for c in d.get("content", []))
        caps["text_completion"] = "supported" if status == 200 and text else "adapter_error"
        caps["system_prompt"] = ("supported" if "OK" in text.upper() and text.isupper()
                                 else "partially_supported" if text else "unknown")
        caps["stop_reason"] = "supported" if d.get("stop_reason") else "partially_supported"
        ev["text"] = {"status": status, "text": text[:120], "stop_reason": d.get("stop_reason"),
                      "usage": d.get("usage")}
    except (json.JSONDecodeError, TypeError):
        caps["text_completion"] = "adapter_error"
        caps["system_prompt"] = caps["stop_reason"] = "unknown"
        ev["text"] = {"status": status, "raw": raw[:300]}

    # B. streaming
    status, raw = messages_call(alias, {
        "messages": [{"role": "user", "content": "Count to five, digits only."}]}, stream=True)
    is_sse = "event:" in raw or "data:" in raw
    caps["streaming"] = ("supported" if status == 200 and is_sse
                         else "adapter_error" if status != 200 else "partially_supported")
    ev["streaming"] = {"status": status, "sse_events": len(re.findall(r"^event:", raw, re.M)),
                       "sample": raw[:200]}

    # C. tool definition + single call
    status, raw = messages_call(alias, {
        "tools": [{"name": "read_file", "description": "Read a file",
                   "input_schema": {"type": "object",
                                    "properties": {"path": {"type": "string"}},
                                    "required": ["path"]}}],
        "messages": [{"role": "user",
                      "content": "Use the read_file tool to read /tmp/x.txt"}]})
    try:
        d = json.loads(raw)
        tool_uses = [c for c in d.get("content", []) if c.get("type") == "tool_use"]
        caps["tool_definition"] = "supported" if status == 200 else "adapter_error"
        caps["single_tool_call"] = ("supported" if tool_uses and
                                    tool_uses[0].get("input", {}).get("path")
                                    else "unsupported" if status == 200 else "adapter_error")
        ev["tool_call"] = {"status": status, "n_tool_uses": len(tool_uses),
                           "stop_reason": d.get("stop_reason")}
    except (json.JSONDecodeError, TypeError):
        caps["tool_definition"] = caps["single_tool_call"] = "adapter_error"
        ev["tool_call"] = {"status": status, "raw": raw[:300]}

    # D. full agent loop: sequential tool calls + tool-result continuation +
    #    context continuation.  Two dependent steps force >=2 tool rounds.
    wd = Path(f"/tmp/pi-prompt-benchmark/cc-smoke-{alias}")
    if wd.exists():
        shutil.rmtree(wd)
    res = claude_agent_run(
        alias, wd,
        "Create a file named alpha.txt containing exactly: 42\n"
        "Then read alpha.txt back, double the number, and create beta.txt "
        "containing only that doubled number.")
    if res.get("ok") and res.get("work"):
        alpha = (res["work"] / "alpha.txt")
        beta = (res["work"] / "beta.txt")
        two_steps = alpha.exists() and beta.exists() and beta.read_text().strip() == "84"
        nturns = res["data"].get("num_turns", 0)
        caps["sequential_tool_calls"] = "supported" if two_steps else (
            "partially_supported" if alpha.exists() else "unsupported")
        caps["tool_result_continuation"] = "supported" if two_steps else "unknown"
        caps["context_continuation"] = "supported" if nturns >= 2 else "partially_supported"
        ev["agent"] = {"num_turns": nturns, "wall_s": round(res["wall_s"], 1),
                       "alpha": alpha.exists(), "beta_ok": two_steps,
                       "cc_usage": res["data"].get("usage"),
                       "cc_cost_usd_unreliable": res["data"].get("total_cost_usd")}
    else:
        caps["sequential_tool_calls"] = "adapter_error"
        caps["tool_result_continuation"] = caps["context_continuation"] = "adapter_error"
        ev["agent"] = {"error": res.get("error"), "wall_s": round(res.get("wall_s", 0), 1)}

    # E. long output
    status, raw = messages_call(alias, {
        "max_tokens": 3000,
        "messages": [{"role": "user",
                      "content": "Write the numbers 1 to 200, one per line, no other text."}]},
        timeout=120)
    try:
        d = json.loads(raw)
        text = "".join(c.get("text", "") for c in d.get("content", []))
        lines = [l for l in text.splitlines() if l.strip()]
        caps["long_output"] = ("supported" if len(lines) >= 150
                               else "partially_supported" if len(lines) > 20 else "unsupported")
        ev["long_output"] = {"lines": len(lines), "stop_reason": d.get("stop_reason")}
    except (json.JSONDecodeError, TypeError):
        caps["long_output"] = "adapter_error"

    # F. reasoning / cache reporting: look at together-side capture for this model
    ents = [e for e in capture_tail(400)
            if e.get("kind") == "response"]
    reqs = {e["seq"]: e for e in capture_tail(400) if e.get("kind") == "request"
            and isinstance(e.get("body"), dict) and e["body"].get("model") == model_id}
    reasoning_seen = cached_seen = usage_seen = False
    for e in ents:
        if e["seq"] not in reqs:
            continue
        usages = e.get("usages") or []
        if isinstance(e.get("body"), dict) and e["body"].get("usage"):
            usages = usages + [e["body"]["usage"]]
        for u in usages:
            usage_seen = True
            od = u.get("output_tokens_details") or {}
            idt = u.get("input_tokens_details") or {}
            if "reasoning_tokens" in od:
                reasoning_seen = True
            if "cached_tokens" in idt:
                cached_seen = True
    caps["reasoning_token_reporting"] = ("supported" if reasoning_seen
                                         else "unknown" if not usage_seen else "unsupported")
    caps["cached_input_reporting"] = ("supported" if cached_seen
                                      else "unknown" if not usage_seen else "unsupported")
    ev["upstream_usage"] = {"usage_seen": usage_seen, "reasoning_seen": reasoning_seen,
                            "cached_seen": cached_seen}

    # G. error propagation: intentionally bad request (unknown alias)
    status, raw = messages_call("benchmark-nonexistent-model", {
        "messages": [{"role": "user", "content": "hi"}]})
    caps["error_propagation"] = ("supported" if status in (400, 401, 404, 429, 500)
                                 and raw else "partially_supported")
    ev["error_prop"] = {"status": status}

    # H. timeout handling: harness-level (runner kills the process); verified once
    # in tests/test_runner_resume.py rather than per model.
    caps["timeout_handling"] = "supported"

    # Verdict: tool loop must be fully valid to enter the benchmark.
    r["tool_loop_valid"] = (caps["sequential_tool_calls"] == "supported"
                            and caps["tool_result_continuation"] == "supported")
    r["compatibility_status"] = ("compatible" if r["tool_loop_valid"]
                                 else "incompatible_tool_loop")
    return r


def main():
    models = [
        ("deepseek-ai/DeepSeek-V4-Pro", "benchmark-deepseek-v4-pro"),
        ("moonshotai/Kimi-K2.6", "benchmark-kimi-k2-6"),
        ("moonshotai/Kimi-K2.7-Code", "benchmark-kimi-k2-7-code"),
        ("nvidia/nemotron-3-ultra-550b-a55b", "benchmark-nemotron-3-ultra"),
        ("thinkingmachines/Inkling", "benchmark-inkling"),
        ("zai-org/GLM-5.2", "benchmark-glm-5-2"),
    ]
    if len(sys.argv) > 1:
        models = [m for m in models if m[0] in sys.argv[1:] or m[1] in sys.argv[1:]]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for mid, alias in models:
        print(f"--- smoking {mid}", flush=True)
        t0 = time.time()
        try:
            r = smoke_model(mid, alias)
        except Exception as e:
            r = {"model": mid, "alias": alias, "compatibility_status": f"smoke_crash:{e}",
                 "caps": {}, "evidence": {}}
        r["smoke_wall_s"] = round(time.time() - t0, 1)
        results.append(r)
        print(json.dumps({k: r[k] for k in ("model", "compatibility_status", "smoke_wall_s")}),
              flush=True)
    (OUT_DIR / "cc_compat.json").write_text(json.dumps(results, indent=1))

    lines = ["# Claude Code compatibility matrix (gateway: litellm 1.93.0)", "",
             "| capability | " + " | ".join(r["alias"].replace("benchmark-", "") for r in results) + " |",
             "|---|" + "---|" * len(results)]
    for cap in CAPS:
        lines.append("| " + cap + " | " +
                     " | ".join(r["caps"].get(cap, "unknown") for r in results) + " |")
    lines.append("| **tool_loop_valid** | " +
                 " | ".join(str(r.get("tool_loop_valid")) for r in results) + " |")
    (OUT_DIR / "cc_compat.md").write_text("\n".join(lines) + "\n")
    print("wrote", OUT_DIR / "cc_compat.json")


if __name__ == "__main__":
    main()
