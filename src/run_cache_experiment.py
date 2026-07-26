#!/usr/bin/env python3
"""Experiment C: session and cache behavior (design §17). Kept separate from
Experiment A. Writes results/runs_cache.jsonl (one record per session; per-turn
usage embedded).

pi conditions: cold / continuous_short / continuous_restate /
stable_prefix_new_session (two cold runs back-to-back, same cwd) /
changed_cwd / delayed_follow_up (60s).
claude-code conditions: cc_fresh / cc_continued_short (same isolated HOME, -c).
"""
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import NODE_BIN, ROOT, append_jsonl, env_secret, model_cost, run_env, sha256
from parse_pi_usage import cache_classification, parse_events, parse_usage
from claude_runner import _capture_offset, _capture_slice, upstream_usage_totals

OUT = ROOT / "results/runs_cache.jsonl"
PI = NODE_BIN / "pi"
CLAUDE = NODE_BIN / "claude"
P1 = "In one sentence, what is prompt caching in an LLM serving stack?"
P2_SHORT = "and how does prefix stability affect it? one sentence"
SLOT_A = Path("/tmp/pi-prompt-benchmark/slot-cache-a")
SLOT_B = Path("/tmp/pi-prompt-benchmark/slot-cache-b")


def pi_turn(model, prompt, cwd, session_dir=None, cont=False, timeout=120):
    cmd = [str(PI), "--provider", "together", "--model", model, "--mode", "json",
           "-p", "--thinking", "medium"]
    if session_dir:
        cmd += ["--session-dir", str(session_dir)]
        if cont:
            cmd += ["-c"]
    else:
        cmd += ["--no-session"]
    cmd.append(prompt)
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       timeout=timeout, env=run_env(), stdin=subprocess.DEVNULL)
    return parse_usage(parse_events(p.stdout.splitlines()))


def record(model, harness, condition, turns_usage, delay_s=None, cwd=None):
    per_turn = [t for u in turns_usage for t in u["per_turn"]]
    cache_cls = [cache_classification(t, i == 0)[0] for i, t in enumerate(per_turn)]
    cost = model_cost(model)
    uncached = sum(t["input_uncached"] for t in per_turn)
    cached = sum(t["cache_read"] for t in per_turn)
    output = sum(t["output"] for t in per_turn)
    logical = uncached + cached
    reported = sum(t["cost_usd"] for t in per_turn)
    nocache = (logical * cost["input"] + output * cost["output"]) / 1e6
    rec = {
        "run_id": f"cache_{harness}_{model.split('/')[-1]}_{condition}_{uuid.uuid4().hex[:6]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "experiment": "experiment_c", "experiment_family": "C",
        "harness": harness, "model": model, "session_condition": condition,
        "turns": len(per_turn), "delay_s": delay_s,
        "workdir_hash": sha256(str(cwd)) if cwd else None,
        "uncached_input_tokens": uncached, "cached_input_tokens": cached,
        "logical_input_tokens": logical, "visible_output_tokens": output,
        "cache_read_ratio": round(cached / logical, 4) if logical else None,
        "cache_classes_per_turn": cache_cls,
        "reported_cost_usd": round(reported, 6),
        "estimated_no_cache_cost_usd": round(nocache, 6),
        "estimated_cache_savings_usd": round(nocache - reported, 6),
        "per_turn_usage": [{k: t[k] for k in
                            ("input_uncached", "cache_read", "output", "reasoning")}
                           for t in per_turn],
        "status": "completed",
    }
    append_jsonl(OUT, rec)
    print(f"{condition:28s} {model.split('/')[-1]:24s} turns={len(per_turn)} "
          f"cached={cached} ratio={rec['cache_read_ratio']}", flush=True)
    return rec


def _safe(fn, model, condition):
    try:
        fn()
    except Exception as e:
        append_jsonl(OUT, {"model": model, "harness": "pi",
                           "session_condition": condition, "status": "infra_error",
                           "experiment": "experiment_c", "error": str(e)[:200],
                           "timestamp": datetime.now(timezone.utc).isoformat()})
        print(f"{condition}: ERROR {str(e)[:80]}", flush=True)


def pi_conditions(model, reps=2):
    SLOT_A.mkdir(parents=True, exist_ok=True)
    SLOT_B.mkdir(parents=True, exist_ok=True)
    for rep in range(reps):
        _safe(lambda: record(model, "pi", "cold",
                             [pi_turn(model, P1, SLOT_A)], cwd=SLOT_A),
              model, "cold")

        def cont_short():
            sess = SLOT_A / f".sess-{uuid.uuid4().hex[:6]}"
            u1 = pi_turn(model, P1, SLOT_A, sess)
            u2 = pi_turn(model, P2_SHORT, SLOT_A, sess, cont=True)
            record(model, "pi", "continuous_short", [u1, u2], cwd=SLOT_A)
        _safe(cont_short, model, "continuous_short")

        def cont_restate():
            sess = SLOT_A / f".sess-{uuid.uuid4().hex[:6]}"
            u1 = pi_turn(model, P1, SLOT_A, sess)
            u2 = pi_turn(model, f"To restate the full request completely: {P1} "
                                f"Also: {P2_SHORT}", SLOT_A, sess, cont=True)
            record(model, "pi", "continuous_full_restatement", [u1, u2], cwd=SLOT_A)
        _safe(cont_restate, model, "continuous_full_restatement")

        def stable_prefix():
            u1 = pi_turn(model, P1, SLOT_A)
            u2 = pi_turn(model, P1, SLOT_A)
            record(model, "pi", "stable_prefix_new_session", [u1, u2], cwd=SLOT_A)
        _safe(stable_prefix, model, "stable_prefix_new_session")

        _safe(lambda: record(model, "pi", "changed_cwd",
                             [pi_turn(model, P1, SLOT_B)], cwd=SLOT_B),
              model, "changed_cwd")

        def delayed():
            sess = SLOT_A / f".sess-{uuid.uuid4().hex[:6]}"
            u1 = pi_turn(model, P1, SLOT_A, sess)
            time.sleep(60)
            u2 = pi_turn(model, P2_SHORT, SLOT_A, sess, cont=True)
            record(model, "pi", "delayed_follow_up_60s", [u1, u2], delay_s=60,
                   cwd=SLOT_A)
        _safe(delayed, model, "delayed_follow_up_60s")


def cc_turn(model_alias, model_id, prompt, home, work, cont=False, timeout=150):
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    (home / ".claude.json").write_text(json.dumps({"hasCompletedOnboarding": True}))
    (home / ".claude" / "settings.json").write_text(
        json.dumps({"permissions": {"defaultMode": "acceptEdits"}}))
    env = {"HOME": str(home), "PATH": f"{NODE_BIN}:/usr/bin:/bin",
           "ANTHROPIC_BASE_URL": "http://127.0.0.1:8903",
           "ANTHROPIC_AUTH_TOKEN": env_secret("GATEWAY_MASTER_KEY"),
           "ANTHROPIC_SMALL_FAST_MODEL": model_alias,
           "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "DISABLE_AUTOUPDATER": "1"}
    cmd = [str(CLAUDE), "-p", prompt, "--output-format", "json",
           "--model", model_alias, "--permission-mode", "acceptEdits",
           "--max-turns", "4"] + (["-c"] if cont else [])
    off = _capture_offset()
    subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True,
                   timeout=timeout, stdin=subprocess.DEVNULL)
    return _capture_slice(off, model_id)


def cc_conditions(model_id, alias, reps=2):
    cost = model_cost(model_id)
    for rep in range(reps):
        base = Path(f"/tmp/pi-prompt-benchmark/cc-cache-{alias}-{rep}")
        home, work = base / "home", base / "work"
        work.mkdir(parents=True, exist_ok=True)
        pairs1 = cc_turn(alias, model_id, P1, home, work)
        _cc_record(model_id, "cc_fresh", pairs1, cost, work)
        pairs2 = cc_turn(alias, model_id, P2_SHORT, home, work, cont=True)
        _cc_record(model_id, "cc_continued_short", pairs2, cost, work)


def _cc_record(model_id, condition, pairs, cost, cwd):
    up = upstream_usage_totals(pairs, cost)
    cache_cls = []
    for i, pr in enumerate(up["per_request"]):
        if not pr or not pr.get("cached"):
            cache_cls.append("none")
        elif i == 0:
            cache_cls.append("first_turn_hit")
        elif pr["cached"] / max(1, pr["prompt"]) > 0.5:
            cache_cls.append("substantial")
        else:
            cache_cls.append("partial")
    rec = {
        "run_id": f"cache_cc_{model_id.split('/')[-1]}_{condition}_{uuid.uuid4().hex[:6]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "experiment": "experiment_c", "experiment_family": "C",
        "harness": "claude-code", "model": model_id, "session_condition": condition,
        "turns": up["requests"], "workdir_hash": sha256(str(cwd)),
        "uncached_input_tokens": up["input_uncached"],
        "cached_input_tokens": up["cache_read"],
        "logical_input_tokens": up["logical_input"],
        "visible_output_tokens": up["output"],
        "cache_read_ratio": round(up["cache_read"] / up["logical_input"], 4)
                            if up["logical_input"] else None,
        "cache_classes_per_turn": cache_cls,
        "reported_cost_usd": up["reported_cost_usd"],
        "estimated_no_cache_cost_usd": up["no_cache_cost_usd"],
        "estimated_cache_savings_usd": round(
            up["no_cache_cost_usd"] - up["reported_cost_usd"], 6),
        "status": "completed",
    }
    append_jsonl(OUT, rec)
    print(f"{condition:28s} {model_id.split('/')[-1]:24s} reqs={up['requests']} "
          f"cached={up['cache_read']} ratio={rec['cache_read_ratio']}", flush=True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    core = ["zai-org/GLM-5.2", "deepseek-ai/DeepSeek-V4-Pro", "moonshotai/Kimi-K2.6"]
    rest = ["moonshotai/Kimi-K2.7-Code", "nvidia/nemotron-3-ultra-550b-a55b",
            "thinkingmachines/Inkling"]
    if mode in ("all", "pi"):
        for m in core:
            pi_conditions(m, reps=2)
        for m in rest:
            pi_conditions(m, reps=1)
    if mode in ("all", "cc"):
        # NOTE: must not run while pilot B has the same models in flight —
        # capture-slice attribution is per model within a byte window.
        for m, alias in (("moonshotai/Kimi-K2.6", "benchmark-kimi-k2-6"),
                         ("zai-org/GLM-5.2", "benchmark-glm-5-2")):
            cc_conditions(m, alias, reps=2)
    print("experiment C complete ->", OUT)


if __name__ == "__main__":
    main()
