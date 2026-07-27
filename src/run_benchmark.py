#!/usr/bin/env python3
"""Benchmark orchestrator (design §26, §16, §18).

Examples:
  python3 src/run_benchmark.py --experiment pilot_a --dry-run
  python3 src/run_benchmark.py --experiment pilot_a --workers 6
  python3 src/run_benchmark.py --experiment pilot_b --workers 1
  python3 src/run_benchmark.py --harnesses pi --models zai-org/GLM-5.2 \
      --tasks py-low-01 --variants baseline --reps 1 --max-runs 1
"""
import argparse
import json
import random
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (BENCH, GENERATOR_VERSION, ROOT, append_jsonl, dir_hash,
                    load_config, load_models, load_task, model_cost, read_jsonl,
                    sha256)
from claude_runner import run_claude
from evaluate_run import evaluate
from parse_pi_usage import cache_classification
from pi_runner import run_pi
from reset_workspace import reset_slot

CFG = load_config()
LOCK = threading.Lock()
SPENT = {"reported": 0.0, "nocache": 0.0, "runs": 0}
SPENT_BY_MODEL = {}
PI_VERSION = "0.82.1"
CC_VERSION = "2.1.220"
LITELLM_VERSION = "1.93.0"


def load_prompt(task_id, variant):
    p = BENCH / "generated_prompts" / task_id / f"{variant}.json"
    return json.loads(p.read_text())


def completed_keys(out_path, experiment=None):
    """Cells with a finished record. With experiment set, only records from
    that experiment count (protocol-pure resume); otherwise any experiment
    satisfies the cell (legacy cross-experiment dedup)."""
    keys = set()
    for r in read_jsonl(out_path):
        if r.get("status") in ("not_run", "infra_error"):
            continue
        if experiment and r.get("experiment") != experiment:
            continue
        keys.add((r["harness"], r["model"], r["task_id"], r["variant"], r["rep"]))
    return keys


def alias_for(model_id):
    for m in load_models():
        if m["id"] == model_id:
            return m["alias"]
    raise KeyError(model_id)


def build_matrix(args):
    exps = CFG.get("experiments") or {}
    if args.experiment in exps:
        spec = exps[args.experiment]
        harnesses = [spec["harness"]]
        models = spec["models"]
        if models == "all_compatible":
            compat = json.loads(
                (ROOT / "results/compatibility/cc_compat.json").read_text())
            models = [r["model"] for r in compat if r.get("tool_loop_valid")]
        tasks, reps = spec["tasks"], spec["repetitions"]
        sel = None
        if spec.get("selection_file"):
            sel = json.loads((ROOT / spec["selection_file"]).read_text())
        blocks = []
        for h in harnesses:
            for m in models:
                variants = spec["variants"]
                if sel is not None:
                    variants = sorted(set(sel[m] + spec.get("always_variants", [])))
                for t_ in tasks:
                    cells = [(v, r) for v in variants for r in range(1, reps + 1)]
                    rnd = random.Random(f"{args.seed}|{h}|{m}|{t_}")
                    rnd.shuffle(cells)
                    blocks.append({"harness": h, "model": m, "task": t_, "cells": cells})
        rnd = random.Random(args.seed)
        rnd.shuffle(blocks)
        return blocks
    if args.experiment in ("pilot_a", "pilot_b"):
        spec = CFG[args.experiment]
        harnesses = [spec["harness"]]
        models = spec["models"]
        if models == "all_compatible":
            compat = json.loads(
                (ROOT / "results/compatibility/cc_compat.json").read_text())
            models = [r["model"] for r in compat if r.get("tool_loop_valid")]
        tasks, variants, reps = spec["tasks"], spec["variants"], spec["repetitions"]
    else:
        harnesses = args.harnesses.split(",")
        models = args.models.split(",")
        tasks = args.tasks.split(",")
        variants = args.variants.split(",")
        reps = args.reps
    blocks = []
    for h in harnesses:
        for m in models:
            for t in tasks:
                cells = [(v, r) for v in variants for r in range(1, reps + 1)]
                rnd = random.Random(f"{args.seed}|{h}|{m}|{t}")
                rnd.shuffle(cells)
                blocks.append({"harness": h, "model": m, "task": t, "cells": cells})
    rnd = random.Random(args.seed)
    rnd.shuffle(blocks)
    return blocks


def over_budget(args, model=None):
    if (SPENT["reported"] >= args.max_cost
            or SPENT["nocache"] >= args.max_nocache_cost
            or SPENT["runs"] >= args.max_runs):
        return True
    if model and args.per_model_cost_cap:
        return SPENT_BY_MODEL.get(model, 0.0) >= args.per_model_cost_cap
    return False


def make_record(base, **kw):
    rec = dict(base)
    rec.update(kw)
    return rec


def run_cell(block, variant, rep, slot, args, order_idx):
    harness, model, task_id = block["harness"], block["model"], block["task"]
    task = load_task(task_id)
    prompt = load_prompt(task_id, variant)
    timeout = CFG["timeouts_s"][task["complexity"]] * args.timeout_mult
    run_id = f"{harness}_{model.split('/')[-1]}_{task_id}_{variant}_r{rep}_{uuid.uuid4().hex[:6]}"
    run_dir = ROOT / CFG["raw_dir"] / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    fixture_hash = reset_slot(slot, task_id)
    cost = model_cost(model)
    base = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "order_index": order_idx,
        "experiment": args.experiment,
        "harness": harness,
        "harness_version": PI_VERSION if harness == "pi" else CC_VERSION,
        "harness_mode": "print_json",
        "permission_mode": None if harness == "pi" else args.permission_mode,
        "gateway_used": harness == "claude-code",
        "gateway_name": None if harness == "pi" else "litellm",
        "gateway_version": None if harness == "pi" else LITELLM_VERSION,
        "gateway_config_hash": None if harness == "pi" else sha256(
            (BENCH / "gateway/litellm.yaml").read_text()),
        "model": model,
        "model_alias": None if harness == "pi" else alias_for(model),
        "upstream_model": model,
        "protocol_inbound": None if harness == "pi" else "anthropic_messages",
        "protocol_outbound": "openai_chat_completions",
        "task_id": task_id,
        "complexity": task["complexity"],
        "variant": variant,
        "prompt_features": prompt["features"],
        "prompt_hash": prompt["sha256"],
        "prompt_chars": prompt["char_count"],
        "prompt_bytes": prompt["byte_count"],
        "est_prompt_tokens": prompt["est_prompt_tokens"],
        "generator_version": prompt["generator_version"],
        "rep": rep,
        "experiment_family": "stress" if prompt["family"] == "stress" else "A",
        "session_mode": "continuous" if "<TURN-BREAK>" in prompt["text"] else "cold",
        "turn_number": 1,
        "slot_id": slot.name,
        "workdir_hash": sha256(str(slot)),
        "fixture_hash": fixture_hash,
        "thinking_requested": CFG["thinking"]["requested_level"] if harness == "pi"
                              else "harness_default",
        "timeout_s": timeout,
    }

    if harness == "pi":
        res = run_pi(model, prompt["text"], slot, timeout,
                     run_dir / "pi_events.jsonl",
                     thinking=CFG["thinking"]["requested_level"])
    else:
        res = run_claude(model, alias_for(model), prompt["text"], slot, timeout,
                         run_dir, permission_mode=args.permission_mode,
                         max_turns=CFG["claude_code"]["max_turns"])

    if res.get("status") == "infra_error":
        return make_record(base, status="infra_error", run_validity="infrastructure_failure",
                           failure_reason=res.get("error"))

    ev = evaluate(slot, task_id,
                  edited_paths=res["trace"].get("edited_paths"),
                  timeout=120)

    if harness == "pi":
        tot = res["usage"]["totals"]
        per_turn = res["usage"]["per_turn"]
        reported = tot["reported_cost_usd"]
        nocache = (tot["logical_input"] * cost["input"]
                   + tot["output"] * cost["output"]) / 1e6
        reasoning = tot["reasoning"]
        reasoning_status = tot["reasoning_token_status"]
        upstream_reasoning = reasoning
        harness_visible_reasoning = reasoning
        preservation = "preserved" if reasoning is not None else "unknown"
        logical_input = tot["logical_input"]
        cached = tot["cache_read"]
        uncached = tot["input_uncached"]
        output_tokens = tot["output"]
        turns = tot["turns"]
        model_validated = model in (tot.get("models_seen") or [model])
        cache_cls = [cache_classification(t, i == 0)[0]
                     for i, t in enumerate(per_turn)]
        harness_reported_input = logical_input
    else:
        up = res["upstream"]
        reported = up["reported_cost_usd"]
        nocache = up["no_cache_cost_usd"]
        reasoning = up["reasoning"]
        reasoning_status = "explicit" if up["reasoning_reported"] else "missing"
        upstream_reasoning = reasoning
        cc_usage = ((res.get("cc_result") or {}).get("usage") or {})
        harness_visible_reasoning = None  # dropped in translation (H16)
        preservation = "dropped" if up["reasoning_reported"] else "unavailable_upstream"
        logical_input = up["logical_input"]
        cached = up["cache_read"]
        uncached = up["input_uncached"]
        output_tokens = up["output"]
        turns = (res.get("cc_result") or {}).get("num_turns")
        model_validated = res["model_validated"]
        cache_cls = ["first_turn_hit" if (i == 0 and pr and pr["cached"]) else
                     ("none" if not pr or not pr["cached"] else
                      ("substantial" if pr["cached"] / max(1, pr["prompt"]) > 0.5
                       else "partial"))
                     for i, pr in enumerate(up["per_request"])]
        harness_reported_input = cc_usage.get("input_tokens")

    status = res["status"]
    validity = "valid"
    if status == "timeout":
        validity = "valid"  # timeouts are real outcomes, kept with timeout flag
    if not model_validated:
        validity = "gateway_failure" if harness == "claude-code" else "usage_parsing_failure"
    if harness == "claude-code" and res.get("gateway_requests", 0) == 0:
        validity = "gateway_failure"
    if status == "no_events" or (harness == "pi" and reasoning_status == "parse_error"):
        validity = "usage_parsing_failure"
    # Provider-side hard failures (e.g. 402 credit exhaustion): zero upstream
    # work on a "completed" run is an infrastructure failure, never a task result.
    if status == "completed" and logical_input == 0:
        validity = "infrastructure_failure"
        status = "infra_error"

    rec = make_record(
        base,
        status=status,
        run_validity=validity,
        wall_s=res["wall_s"],
        exit_code=res.get("exit_code"),
        timeout_hit=status == "timeout",
        truncated=False,
        cc_subtype=res.get("cc_subtype"),
        turns_censored=bool(res.get("max_turns_hit")),
        turns=turns,
        uncached_input_tokens=uncached,
        cached_input_tokens=cached,
        logical_input_tokens=logical_input,
        harness_reported_input_tokens=harness_reported_input,
        upstream_cached_input_tokens=cached,
        visible_output_tokens=output_tokens,
        reasoning_tokens=reasoning,
        upstream_reasoning_tokens=upstream_reasoning,
        harness_visible_reasoning_tokens=harness_visible_reasoning,
        reasoning_token_status=reasoning_status,
        reasoning_metadata_preservation=preservation,
        reported_cost_usd=round(reported, 6),
        estimated_no_cache_cost_usd=round(nocache, 6),
        estimated_cache_savings_usd=round(nocache - reported, 6),
        cache_read_ratio=round(cached / logical_input, 4) if logical_input else None,
        cache_classes_per_turn=cache_cls,
        gateway_retries=None,
        harness_retries=None,
        context_compaction_events=None,
        context_summary_events=None,
        prefix_hash_before_translation=None,
        prefix_hash_after_translation=None,
        compatibility_status="compatible",
        **{f"tool_{k}": v for k, v in res["trace"].items()
           if k not in ("edited_paths", "stream_t0", "first_tool_ts", "first_edit_ts")},
        **ev,
    )
    return rec


def worker_loop(blocks_queue, slot, args, out_path, done_keys):
    while True:
        with LOCK:
            if not blocks_queue or over_budget(args):
                return
            block = blocks_queue.pop(0)
        for i, (variant, rep) in enumerate(block["cells"]):
            key = (block["harness"], block["model"], block["task"], variant, rep)
            with LOCK:
                if key in done_keys:
                    continue
                if over_budget(args, block["model"]):
                    break
                done_keys.add(key)
            try:
                rec = run_cell(block, variant, rep, slot, args, i)
            except Exception as e:
                rec = {"harness": block["harness"], "model": block["model"],
                       "task_id": block["task"], "variant": variant, "rep": rep,
                       "status": "infra_error", "run_validity": "infrastructure_failure",
                       "failure_reason": f"runner_exception:{e}"}
            with LOCK:
                SPENT["reported"] += rec.get("reported_cost_usd") or 0
                SPENT["nocache"] += rec.get("estimated_no_cache_cost_usd") or 0
                SPENT_BY_MODEL[block["model"]] = (SPENT_BY_MODEL.get(block["model"], 0.0)
                                                  + (rec.get("reported_cost_usd") or 0))
                SPENT["runs"] += 1
                append_jsonl(out_path, rec)
                print(f"[{SPENT['runs']}] {rec.get('run_id', key)} "
                      f"status={rec.get('status')} success={rec.get('task_success')} "
                      f"reasoning={rec.get('reasoning_tokens')} "
                      f"cost=${rec.get('reported_cost_usd')} "
                      f"(total ${SPENT['reported']:.2f})", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", default="custom")
    ap.add_argument("--harnesses", default="pi")
    ap.add_argument("--models", default="")
    ap.add_argument("--tasks", default="")
    ap.add_argument("--variants", default="baseline")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--workers", type=int, default=CFG.get("workers", 6))
    ap.add_argument("--seed", type=int, default=CFG["seed"])
    ap.add_argument("--max-runs", type=int, default=10000)
    ap.add_argument("--max-cost", type=float,
                    default=CFG["budgets"]["pilot_max_reported_cost_usd"])
    ap.add_argument("--max-nocache-cost", type=float,
                    default=CFG["budgets"]["pilot_max_no_cache_cost_usd"])
    ap.add_argument("--timeout-mult", type=float, default=1.0)
    ap.add_argument("--permission-mode", default="acceptEdits")
    ap.add_argument("--per-model-cost-cap", type=float, default=None,
                    help="reported-USD budget pool per model")
    ap.add_argument("--resume-scope", choices=["global", "experiment"],
                    default="global")
    ap.add_argument("--out", default="results/runs.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--require-valid-tool-loop", action="store_true", default=True)
    args = ap.parse_args()

    out_path = ROOT / args.out
    blocks = build_matrix(args)
    n_runs = sum(len(b["cells"]) for b in blocks)
    est = n_runs * 0.02
    print(f"matrix: {len(blocks)} blocks, {n_runs} runs "
          f"(rough no-cache estimate ${est:.2f}); "
          f"budget caps: ${args.max_cost} reported / ${args.max_nocache_cost} no-cache")
    if args.dry_run:
        for b in blocks[:8]:
            print(" ", b["harness"], b["model"], b["task"],
                  [c[0][:12] for c in b["cells"][:5]], "...")
        return

    done = completed_keys(out_path,
                          experiment=args.experiment if args.resume_scope == "experiment"
                          else None)
    print(f"resume: {len(done)} cells already completed")

    # Claude Code runs must be sequential (shared capture stream attribution).
    cc_blocks = [b for b in blocks if b["harness"] == "claude-code"]
    pi_blocks = [b for b in blocks if b["harness"] == "pi"]
    slots_root = Path(CFG["slots_root"])

    if pi_blocks:
        workers = min(args.workers, len(pi_blocks))
        queue = list(pi_blocks)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for w in range(workers):
                slot = slots_root / f"slot-{w+1:02d}"
                ex.submit(worker_loop, queue, slot, args, out_path, done)
    if cc_blocks and not over_budget(args):
        # Same-model CC runs must be sequential (capture attribution is by
        # model within a byte-offset window); different models can run in
        # parallel because _capture_slice filters on the upstream model id.
        by_model = {}
        for b in cc_blocks:
            by_model.setdefault(b["model"], []).append(b)
        with ThreadPoolExecutor(max_workers=len(by_model)) as ex:
            for i, (model, mblocks) in enumerate(sorted(by_model.items())):
                slot = slots_root / f"slot-cc-{i+1:02d}"
                ex.submit(worker_loop, list(mblocks), slot, args, out_path, done)

    print(f"DONE runs={SPENT['runs']} reported=${SPENT['reported']:.2f} "
          f"nocache=${SPENT['nocache']:.2f}")


if __name__ == "__main__":
    main()
