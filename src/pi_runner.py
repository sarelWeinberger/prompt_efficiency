#!/usr/bin/env python3
"""Execute one PI.DEV run: fresh --no-session pi invocation in a fixed slot."""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import NODE_BIN, redact, run_env
from parse_pi_usage import parse_events, parse_usage, estimate_no_cache_cost
from parse_tool_trace import from_pi_events

PI = NODE_BIN / "pi"


def run_pi(model_id, prompt_text, slot, timeout_s, raw_path, thinking="medium"):
    cmd = [str(PI), "--provider", "together", "--model", model_id,
           "--mode", "json", "-p", "--no-session",
           "--thinking", thinking, prompt_text]
    env = run_env()
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

    raw_path = Path(raw_path)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(redact(stdout or "") + "\n--- STDERR ---\n" + redact(stderr or ""))

    events = parse_events((stdout or "").splitlines())
    usage = parse_usage(events)
    trace = from_pi_events(events)
    return {
        "status": "timeout" if timed_out else ("completed" if events else "no_events"),
        "wall_s": round(wall, 2),
        "exit_code": p.returncode if not timed_out else None,
        "usage": usage,
        "trace": trace,
        "estimate_no_cache_cost": estimate_no_cache_cost,
        "stderr_tail": redact((stderr or "")[-500:]),
    }
