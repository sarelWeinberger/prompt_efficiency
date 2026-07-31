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


def run_pi(model_id, prompt_text, slot, timeout_s, raw_path, thinking="medium",
           provider="together"):
    """Run one pi task. Multi-turn prompts (turns separated by <TURN-BREAK>)
    use a throwaway session dir inside the slot and continue with -c."""
    turns = prompt_text.split("\n<TURN-BREAK>\n")
    extra = {}
    if provider == "anthropic":
        from common import env_secret
        extra["ANTHROPIC_API_KEY"] = env_secret("ANTHROPIC_API_KEY")
    env = run_env(extra)
    t0 = time.time()
    timed_out = False
    stdout_all, stderr_all = [], []
    rc = None
    sess = Path(slot) / ".bench-session"
    deadline = t0 + timeout_s
    try:
        for i, turn_text in enumerate(turns):
            cmd = [str(PI), "--provider", provider, "--model", model_id,
                   "--mode", "json", "-p", "--thinking", thinking]
            if len(turns) == 1:
                cmd += ["--no-session"]
            else:
                cmd += ["--session-dir", str(sess)] + (["-c"] if i else [])
            cmd.append(turn_text)
            p = subprocess.Popen(cmd, cwd=slot, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, env=env,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
            try:
                stdout, stderr = p.communicate(timeout=max(10, deadline - time.time()))
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                stdout, stderr = p.communicate()
            stdout_all.append(stdout or "")
            stderr_all.append(stderr or "")
            rc = p.returncode
            if timed_out:
                break
    except OSError as e:
        return {"status": "infra_error", "error": str(e), "wall_s": time.time() - t0}
    wall = time.time() - t0
    stdout, stderr = "\n".join(stdout_all), "\n".join(stderr_all)

    raw_path = Path(raw_path)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(redact(stdout) + "\n--- STDERR ---\n" + redact(stderr))

    events = parse_events(stdout.splitlines())
    usage = parse_usage(events)
    trace = from_pi_events(events)
    return {
        "status": "timeout" if timed_out else ("completed" if events else "no_events"),
        "wall_s": round(wall, 2),
        "exit_code": rc if not timed_out else None,
        "usage": usage,
        "trace": trace,
        "estimate_no_cache_cost": estimate_no_cache_cost,
        "stderr_tail": redact((stderr or "")[-500:]),
    }
