#!/usr/bin/env python3
"""Tool-cost paired analysis (frozen rubric §5-§6).

Emits:
- results/summaries/tool_cost_paired_effects.csv  (per harness x model x variant)
- results/summaries/tool_cost_by_mechanism.csv    (semantic mediator join)
- results/summaries/tool_cost_by_tool_type.csv    (category composition)
"""
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import ROOT, read_jsonl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_results import bootstrap_ci, med
from semantic_analysis import paired_rows, fnum

OUT = ROOT / "results/summaries"

METRICS = ["tool_calls", "failed_calls", "error_recovery_calls",
           "duplicate_commands", "repeated_reads", "post_green_repeat_tests",
           "post_success_calls", "abandoned_exploration_calls",
           "tool_result_chars", "est_tool_result_tokens",
           "induced_cost_lower_usd", "induced_cost_upper_usd",
           "context_growth_tokens", "tool_wall_s", "wall_s",
           "estimated_no_cache_cost_usd", "reported_cost_usd",
           "cat_test_execution", "cat_file_read", "cat_file_search",
           "cat_navigation", "cat_code_edit"]


def perm_test(deltas_by_task, n=10000, seed=17):
    """Paired sign-flip permutation test on per-task median deltas."""
    meds = [med(v) for v in deltas_by_task.values() if v]
    meds = [m for m in meds if m is not None]
    if len(meds) < 3:
        return None
    obs = med(meds)
    rnd = random.Random(seed)
    hits = 0
    for _ in range(n):
        flipped = [m * rnd.choice((1, -1)) for m in meds]
        if abs(med(flipped)) >= abs(obs):
            hits += 1
    return hits / n


def load_runs():
    rows = []
    with open(OUT / "tool_cost_run_level.csv") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def add_permutation(paired, runs, metrics):
    """Annotate paired rows with permutation p-values for key metrics."""
    base = defaultdict(list)
    for r in runs:
        if r["variant"] == "baseline":
            base[(r["harness"], r["model"], r["task_id"], r["experiment"])].append(r)
    idx = defaultdict(list)
    for r in runs:
        if r["variant"] != "baseline":
            idx[(r["harness"], r["model"], r["variant"], r["experiment"])].append(r)
    from semantic_analysis import BASELINE_EXP
    for rec in paired:
        key = (rec["harness"], rec["model"], rec["variant"], rec["experiment"])
        vr = idx.get(key, [])
        bexp = BASELINE_EXP.get(rec["experiment"], rec["experiment"])
        for m in metrics:
            dbt = defaultdict(list)
            for r in vr:
                b = base.get((rec["harness"], rec["model"], r["task_id"], bexp), [])
                bvals = [fnum(x.get(m)) for x in b]
                bvals = [x for x in bvals if x is not None]
                v = fnum(r.get(m))
                if v is not None and bvals:
                    dbt[r["task_id"]].append(v - med(bvals))
            p = perm_test(dbt)
            if p is not None:
                rec[f"{m}__perm_p"] = p
    return paired


def zero_tail_stats(runs, metrics):
    """Zero fraction and max for count metrics (heavy-tail disclosure)."""
    out = []
    for m in metrics:
        vals = [fnum(r.get(m)) for r in runs]
        vals = [v for v in vals if v is not None]
        if not vals:
            continue
        nz = [v for v in vals if v > 0]
        out.append({"metric": m, "n": len(vals),
                    "zero_fraction": round(1 - len(nz) / len(vals), 3),
                    "median": med(vals), "p95": sorted(vals)[int(0.95 * len(vals))],
                    "max": max(vals)})
    return out


def by_mechanism(runs):
    """Descriptive mediator decomposition: judge-annotated unused_branches /
    redundant_verification vs exploratory / post-green tool calls."""
    ann = {}
    for j in read_jsonl(ROOT / "results/semantic/annotations_primary.jsonl"):
        if j.get("annotation"):
            ann[j["run_id"]] = j["annotation"]
    rows = []
    strata = defaultdict(list)
    for r in runs:
        a = ann.get(r["run_id"])
        if not a:
            continue
        ub = a["waste"]["unused_branches"]
        rv = a["waste"]["redundant_verification"]
        strata[("unused_branches", min(int(ub), 4))].append(r)
        strata[("redundant_verification", min(int(rv), 3))].append(r)
    for (mech, level), rs in sorted(strata.items()):
        def m(k):
            vals = [fnum(x.get(k)) for x in rs]
            vals = [v for v in vals if v is not None]
            return med(vals) if vals else None
        rows.append({
            "mechanism": mech, "level": level, "n_runs": len(rs),
            "median_tool_calls": m("tool_calls"),
            "median_exploration_calls": (m("cat_file_read") or 0) + (m("cat_file_search") or 0),
            "median_abandoned_exploration": m("abandoned_exploration_calls"),
            "median_post_green_repeat_tests": m("post_green_repeat_tests"),
            "median_post_success_calls": m("post_success_calls"),
            "median_est_result_tokens": m("est_tool_result_tokens"),
            "median_induced_lower_usd": m("induced_cost_lower_usd"),
            "median_nocache_cost": m("estimated_no_cache_cost_usd"),
            "median_wall_s": m("wall_s"),
            "success_rate": round(sum(1 for x in rs
                                      if x.get("scope_compliant_success") == "True")
                                  / len(rs), 3),
        })
    return rows


def by_tool_type(runs):
    """Category composition per harness x variant (screening + anthropic)."""
    cats = ["cat_test_execution", "cat_file_read", "cat_file_search",
            "cat_navigation", "cat_code_edit", "cat_git_inspect",
            "cat_env_inspect", "cat_build_compile", "cat_other_bash"]
    rows = []
    strata = defaultdict(list)
    for r in runs:
        strata[(r["harness"], r["model"] == "claude-sonnet-5", r["variant"])].append(r)
    for (h, is_claude, v), rs in sorted(strata.items()):
        rec = {"harness": h, "model_group": "claude-sonnet-5" if is_claude else "open-6",
               "variant": v, "n_runs": len(rs)}
        tot = 0
        for c in cats:
            vals = [fnum(r.get(c)) or 0 for r in rs]
            rec[c] = round(sum(vals) / len(vals), 2)
            tot += rec[c]
        rec["mean_total_calls"] = round(tot, 2)
        for c in cats:
            rec[f"{c}_share"] = round(rec[c] / tot, 3) if tot else None
        rows.append(rec)
    return rows


def write(path, rows):
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, restval="")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {path.relative_to(ROOT)}")


def main():
    runs = load_runs()
    paired = paired_rows(runs, METRICS, lambda r, m: fnum(r.get(m)))
    key_metrics = ["tool_calls", "post_green_repeat_tests", "duplicate_commands",
                   "abandoned_exploration_calls", "post_success_calls",
                   "est_tool_result_tokens", "estimated_no_cache_cost_usd"]
    paired = add_permutation(paired, runs, key_metrics)
    write(OUT / "tool_cost_paired_effects.csv", paired)
    write(OUT / "tool_cost_by_mechanism.csv", by_mechanism(runs))
    write(OUT / "tool_cost_by_tool_type.csv", by_tool_type(runs))
    for r in zero_tail_stats(runs, ["duplicate_commands", "repeated_reads",
                                    "post_green_repeat_tests", "post_success_calls",
                                    "abandoned_exploration_calls", "failed_calls"]):
        print(r)


if __name__ == "__main__":
    main()
