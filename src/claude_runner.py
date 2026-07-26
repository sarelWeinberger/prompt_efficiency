#!/usr/bin/env python3
"""Execute one Claude Code run through the gateway (design §5, §11, §16).

Uses the real claude CLI with an isolated per-run HOME. Authoritative usage
comes from the Together-facing capture slice for the run window; the harness's
own result JSON is retained for cross-checking (its total_cost_usd is known
to be wrong for aliased models).
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import NODE_BIN, ROOT, env_secret, load_config, model_cost, redact, run_env
from parse_tool_trace import from_cc_transcript

CLAUDE = NODE_BIN / "claude"
CAPTURE = ROOT / "results/raw/gateway-live/together_capture.jsonl"


def _capture_offset():
    return CAPTURE.stat().st_size if CAPTURE.exists() else 0


def _capture_slice(offset, upstream_model):
    """Parse capture entries appended after offset, filtered to upstream_model."""
    if not CAPTURE.exists():
        return []
    with open(CAPTURE) as f:
        f.seek(offset)
        lines = f.read().splitlines()
    entries = []
    for ln in lines:
        try:
            entries.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    reqs = {e["seq"]: e for e in entries if e.get("kind") == "request"
            and isinstance(e.get("body"), dict)
            and e["body"].get("model") == upstream_model}
    out = []
    for e in entries:
        if e.get("kind") == "response" and e["seq"] in reqs:
            out.append({"req": reqs[e["seq"]], "resp": e})
    return out


def upstream_usage_totals(pairs, cost):
    """Aggregate chat-completions usage from Together-side capture pairs."""
    tot = {"requests": len(pairs), "input_uncached": 0, "cache_read": 0,
           "output": 0, "reasoning": 0, "reasoning_reported": False}
    per_request = []
    for pr in pairs:
        usages = pr["resp"].get("usages") or []
        body = pr["resp"].get("body")
        if isinstance(body, dict) and body.get("usage"):
            usages = usages + [body["usage"]]
        if not usages:
            per_request.append(None)
            continue
        u = usages[-1]
        cached = ((u.get("prompt_tokens_details") or {}).get("cached_tokens")
                  or (u.get("input_tokens_details") or {}).get("cached_tokens") or 0)
        reasoning = ((u.get("completion_tokens_details") or {}).get("reasoning_tokens")
                     or (u.get("output_tokens_details") or {}).get("reasoning_tokens"))
        prompt = u.get("prompt_tokens", u.get("input_tokens", 0))
        completion = u.get("completion_tokens", u.get("output_tokens", 0))
        tot["input_uncached"] += max(0, prompt - cached)
        tot["cache_read"] += cached
        tot["output"] += completion
        if reasoning is not None:
            tot["reasoning"] += reasoning
            tot["reasoning_reported"] = True
        per_request.append({"prompt": prompt, "cached": cached,
                            "completion": completion, "reasoning": reasoning})
    tot["logical_input"] = tot["input_uncached"] + tot["cache_read"]
    tot["reported_cost_usd"] = round(
        tot["input_uncached"] * cost["input"] / 1e6
        + tot["cache_read"] * cost["cache_read"] / 1e6
        + tot["output"] * cost["output"] / 1e6, 6)
    tot["no_cache_cost_usd"] = round(
        tot["logical_input"] * cost["input"] / 1e6
        + tot["output"] * cost["output"] / 1e6, 6)
    if not tot["reasoning_reported"]:
        tot["reasoning"] = None
    tot["per_request"] = per_request
    return tot


def run_claude(model_id, alias, prompt_text, slot, timeout_s, run_dir,
               permission_mode="acceptEdits", max_turns=40):
    run_dir = Path(run_dir)
    home = run_dir / "home"
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    (home / ".claude.json").write_text(json.dumps({"hasCompletedOnboarding": True}))
    (home / ".claude" / "settings.json").write_text(json.dumps(
        {"permissions": {"defaultMode": permission_mode}}))

    env = {
        "HOME": str(home),
        "PATH": f"{NODE_BIN}:/usr/local/go/bin:/usr/bin:/bin",
        "ANTHROPIC_BASE_URL": "http://127.0.0.1:8903",
        "ANTHROPIC_AUTH_TOKEN": env_secret("GATEWAY_MASTER_KEY"),
        "ANTHROPIC_SMALL_FAST_MODEL": alias,
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "DISABLE_AUTOUPDATER": "1",
        "GOCACHE": "/tmp/pi-prompt-benchmark/gocache",
    }
    cmd = [str(CLAUDE), "-p", prompt_text, "--output-format", "json",
           "--model", alias, "--permission-mode", permission_mode,
           "--max-turns", str(max_turns)]
    if permission_mode == "bypassPermissions":
        cmd += ["--dangerously-skip-permissions"]

    offset = _capture_offset()
    t0 = time.time()
    timed_out = False
    try:
        p = subprocess.Popen(cmd, cwd=slot, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, env=env,
                             stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            stdout, stderr = p.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            stdout, stderr = p.communicate()
    except OSError as e:
        return {"status": "infra_error", "error": str(e), "wall_s": time.time() - t0}
    wall = time.time() - t0

    (run_dir / "claude_out.json").write_text(redact(stdout or ""))
    if stderr:
        (run_dir / "claude_err.txt").write_text(redact(stderr))

    data = None
    if not timed_out:
        try:
            data = json.loads(stdout)
        except (json.JSONDecodeError, TypeError):
            pass

    # Harvest per-message transcript for tool trace
    transcript_lines = []
    proj = home / ".claude" / "projects"
    if proj.exists():
        for f in sorted(proj.rglob("*.jsonl")):
            transcript_lines += f.read_text().splitlines()
        (run_dir / "claude_code_events.jsonl").write_text(
            redact("\n".join(transcript_lines)))
    trace = from_cc_transcript(transcript_lines)

    cost = model_cost(model_id)
    pairs = _capture_slice(offset, model_id)
    upstream = upstream_usage_totals(pairs, cost)
    (run_dir / "together_usage.json").write_text(json.dumps(upstream, indent=1))

    status = "timeout" if timed_out else (
        "completed" if data is not None else "no_json")
    model_ok = bool(pairs)  # the expected upstream model actually served requests
    return {
        "status": status,
        "wall_s": round(wall, 2),
        "exit_code": p.returncode if not timed_out else None,
        "cc_result": data,
        "upstream": upstream,
        "trace": trace,
        "model_validated": model_ok,
        "gateway_requests": len(pairs),
        "stderr_tail": redact((stderr or "")[-500:]),
    }
