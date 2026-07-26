#!/usr/bin/env python3
"""Prompt-effect analysis (design §8, §18, §23-24).

Paired within model×harness×task blocks against the block's baseline median.
Task-clustered bootstrap CIs. Emits results/summaries/prompt_sensitivity.csv
and per-model summaries. Only run_validity == valid rows enter comparisons.
"""
import csv
import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import ROOT, load_config, read_jsonl

CFG = load_config()
OUT = ROOT / "results/summaries"


def med(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else None


def bootstrap_ci(pairs_by_task, stat_fn, n=2000, seed=7):
    """Task-clustered bootstrap: resample tasks, then compute stat."""
    tasks = list(pairs_by_task)
    if not tasks:
        return None, None
    rnd = random.Random(seed)
    stats = []
    for _ in range(n):
        sample = [pairs_by_task[rnd.choice(tasks)] for _ in tasks]
        flat = [v for vs in sample for v in vs]
        s = stat_fn(flat)
        if s is not None:
            stats.append(s)
    if not stats:
        return None, None
    stats.sort()
    return stats[int(0.025 * len(stats))], stats[int(0.975 * len(stats))]


def classify(row, cfg):
    c = cfg["classification"]
    ratio, lo = row["median_reasoning_ratio"], row["ratio_ci_low"]
    if row["n_runs"] < 3 or ratio is None:
        return "inconclusive"
    dsucc = (row["success_rate"] or 0) - (row["baseline_success_rate"] or 0)
    harmful = (dsucc < -c["success_improvement_practical_threshold"]
               or (row["oos_rate"] or 0) > (row["baseline_oos_rate"] or 0) + 0.15)
    wasteful = (ratio > c["wasteful_min_median_reasoning_ratio"]
                and (lo or 0) > c["wasteful_min_ci_lower_ratio"]
                and dsucc <= c["success_improvement_practical_threshold"]
                and row["n_tasks_direction"] >= c["min_tasks_with_effect"])
    if harmful and ratio > 1.1:
        return "harmful_overthinking"
    if wasteful:
        return "wasteful"
    if ratio > 1.2 and dsucc > c["success_improvement_practical_threshold"]:
        return "useful_deliberation"
    if ratio is not None and ratio <= 1.2 and abs(dsucc) <= 0.05:
        return "neutral"
    return "inconclusive"


def analyze(runs, experiment_filter=None):
    rows = [r for r in runs
            if r.get("run_validity") == "valid"
            and r.get("status") in ("completed", "timeout")
            and (experiment_filter is None or r.get("experiment") in experiment_filter)]
    # block = (harness, model, task); baseline medians per block
    base_reasoning = {}
    base_success = defaultdict(list)
    for key, group in _group(rows, ("harness", "model", "task_id")).items():
        b = [r for r in group if r["variant"] == "baseline"]
        base_reasoning[key] = med([r.get("reasoning_tokens") for r in b])
        base_success[key] = [1 if r.get("task_success") else 0 for r in b]

    out = []
    for (harness, model, variant), group in _group(
            rows, ("harness", "model", "variant")).items():
        if variant == "baseline":
            continue
        pairs_by_task = defaultdict(list)
        excess_by_task = defaultdict(list)
        succ, oos, tools, repeats, costs, nocache, walls = [], [], [], [], [], [], []
        base_succ_all = []
        for r in group:
            key = (harness, model, r["task_id"])
            b = base_reasoning.get(key)
            base_succ_all += base_success.get(key, [])
            rt = r.get("reasoning_tokens")
            if b is not None and rt is not None:
                if b > 0:
                    pairs_by_task[r["task_id"]].append(rt / b)
                excess_by_task[r["task_id"]].append(rt - b)
            succ.append(1 if r.get("task_success") else 0)
            oos.append(1 if r.get("out_of_scope_changes") else 0)
            tools.append(r.get("tool_total_tool_calls"))
            repeats.append((r.get("tool_duplicate_reads") or 0)
                           + (r.get("tool_repeated_searches") or 0)
                           + (r.get("tool_repeated_tests_no_change") or 0))
            costs.append(r.get("reported_cost_usd"))
            nocache.append(r.get("estimated_no_cache_cost_usd"))
            walls.append(r.get("wall_s"))
        ratios = [v for vs in pairs_by_task.values() for v in vs]
        excesses = [v for vs in excess_by_task.values() for v in vs]
        lo, hi = bootstrap_ci(dict(pairs_by_task), med)
        n_dir = sum(1 for vs in pairs_by_task.values() if med(vs) and med(vs) > 1)
        n_succ = sum(succ)
        row = {
            "harness": harness, "model": model, "variant": variant,
            "features": ";".join(group[0].get("prompt_features", [])),
            "n_runs": len(group), "n_tasks": len({r['task_id'] for r in group}),
            "success_rate": round(sum(succ) / len(succ), 3) if succ else None,
            "baseline_success_rate": round(sum(base_succ_all) / len(base_succ_all), 3)
                                     if base_succ_all else None,
            "oos_rate": round(sum(oos) / len(oos), 3) if oos else None,
            "baseline_oos_rate": 0.0,
            "median_reasoning": med([r.get("reasoning_tokens") for r in group]),
            "median_excess_reasoning": med(excesses),
            "median_reasoning_ratio": round(med(ratios), 3) if ratios else None,
            "ratio_ci_low": round(lo, 3) if lo else None,
            "ratio_ci_high": round(hi, 3) if hi else None,
            "n_tasks_direction": n_dir,
            "median_tool_calls": med(tools),
            "median_repeated_ops": med(repeats),
            "cost_per_success": round(sum(c for c in costs if c) / n_succ, 5)
                                if n_succ else None,
            "nocache_cost_per_success": round(sum(c for c in nocache if c) / n_succ, 5)
                                        if n_succ else None,
            "median_wall_s": med(walls),
        }
        row["classification"] = classify(row, CFG)
        out.append(row)
    return out, rows


def _group(rows, keys):
    g = defaultdict(list)
    for r in rows:
        g[tuple(r.get(k) for k in keys)].append(r)
    return g


def main():
    runs = read_jsonl(ROOT / "results/runs.jsonl")
    table, valid_rows = analyze(runs, experiment_filter={"pilot_a", "pilot_b"})
    OUT.mkdir(parents=True, exist_ok=True)
    if table:
        with open(OUT / "prompt_sensitivity.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(table[0].keys()))
            w.writeheader()
            w.writerows(sorted(table, key=lambda r: (r["harness"], r["model"],
                                                     r["variant"])))
    counts = defaultdict(int)
    for r in runs:
        counts[(r.get("experiment"), r.get("status"), r.get("run_validity"))] += 1
    summary = {
        "n_total_records": len(runs),
        "n_valid_for_analysis": len(valid_rows),
        "by_experiment_status": {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in counts.items()},
        "total_reported_cost": round(sum(r.get("reported_cost_usd") or 0 for r in runs), 3),
        "total_nocache_cost": round(sum(r.get("estimated_no_cache_cost_usd") or 0
                                        for r in runs), 3),
    }
    (OUT / "run_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    print(f"wrote {OUT/'prompt_sensitivity.csv'} ({len(table)} rows)")


if __name__ == "__main__":
    main()
