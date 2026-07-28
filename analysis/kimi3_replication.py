#!/usr/bin/env python3
"""Kimi-K3 small-replication analysis (post-registration).

Emits:
- results/summaries/kimi3_small_replication.csv  (K3 per-variant paired stats)
- results/summaries/kimi_generation_small_comparison.csv (K3 vs K2.6 vs
  K2.7-Code on the SAME tasks, each vs its own baseline, plus the frozen
  material-difference evaluation)

Comparators come from screening_pi / screening_cc restricted to the frozen
replication tasks. Historical results are read-only.
"""
import csv
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import ROOT, load_config, read_jsonl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_results import analyze, bootstrap_ci, med

CFG = load_config()
TH = CFG["kimi3_material_difference"]
OUT = ROOT / "results/summaries"
PI_TASKS = ["py-low-01", "go-low-01", "py-med-01", "js-med-03", "js-high-01", "go-high-01"]
CC_TASKS = ["py-low-01", "js-med-03", "js-high-01"]
VARIANTS = ["multiple_approaches", "deep_thinking", "bounded_efficiency"]
K3 = "moonshotai/Kimi-K3"
K26 = "moonshotai/Kimi-K2.6"
K27 = "moonshotai/Kimi-K2.7-Code"


def stats_for(runs, experiments, model, tasks, harness):
    """Per-variant paired stats vs the model's own baseline on given tasks."""
    rows = [r for r in runs
            if r.get("run_validity") == "valid"
            and r.get("status") in ("completed", "timeout")
            and r.get("experiment") in experiments
            and r.get("model") == model
            and r.get("harness") == harness
            and r.get("task_id") in tasks]
    base = defaultdict(list)
    for r in rows:
        if r["variant"] == "baseline":
            base[r["task_id"]].append(r)
    out = {}
    for v in VARIANTS:
        vr = [r for r in rows if r["variant"] == v]
        if not vr:
            continue
        ratios_by_task, tool_r, turn_r = defaultdict(list), [], []
        scope, costs, ncosts = [], [], []
        for r in vr:
            b = base.get(r["task_id"], [])
            bmed = med([x.get("reasoning_tokens") for x in b])
            if bmed and r.get("reasoning_tokens") is not None:
                ratios_by_task[r["task_id"]].append(r["reasoning_tokens"] / bmed)
            btool = med([x.get("tool_total_tool_calls") for x in b])
            bturn = med([x.get("turns") for x in b])
            if btool and r.get("tool_total_tool_calls") is not None:
                tool_r.append(r["tool_total_tool_calls"] / btool)
            if bturn and r.get("turns") is not None:
                turn_r.append(r["turns"] / bturn)
            scope.append(1 if r.get("scope_compliant_success") else 0)
            costs.append(r.get("reported_cost_usd") or 0)
            ncosts.append(r.get("estimated_no_cache_cost_usd") or 0)
        ratios = [x for xs in ratios_by_task.values() for x in xs]
        lo, hi = bootstrap_ci(dict(ratios_by_task), med)
        n_dir = sum(1 for xs in ratios_by_task.values() if med(xs) and med(xs) > 1)
        n_ok = sum(scope)
        base_scope = [1 if x.get("scope_compliant_success") else 0
                      for xs in base.values() for x in xs]
        out[v] = {
            "n_runs": len(vr), "n_tasks": len({r['task_id'] for r in vr}),
            "median_reasoning_ratio": round(med(ratios), 3) if ratios else None,
            "ci_low": round(lo, 3) if lo else None,
            "ci_high": round(hi, 3) if hi else None,
            "n_tasks_same_direction": n_dir,
            "scope_success": round(sum(scope) / len(scope), 3) if scope else None,
            "baseline_scope_success": round(sum(base_scope) / len(base_scope), 3)
                                      if base_scope else None,
            "median_tool_ratio": round(med(tool_r), 3) if tool_r else None,
            "median_turn_ratio": round(med(turn_r), 3) if turn_r else None,
            "cost_per_compliant_success": round(sum(costs) / n_ok, 5) if n_ok else None,
            "nocache_cost_per_compliant_success": round(sum(ncosts) / n_ok, 5)
                                                  if n_ok else None,
        }
    return out


def classify_effect(s):
    """Waste classification consistent with the main §24 rule."""
    if s is None or s["median_reasoning_ratio"] is None or s["n_runs"] < 3:
        return "inconclusive"
    r, lo = s["median_reasoning_ratio"], s["ci_low"] or 0
    dsucc = (s["scope_success"] or 0) - (s["baseline_scope_success"] or 0)
    if r > 1.5 and lo > 1.1 and dsucc <= 0.10:
        return "wasteful"
    if r <= 1.2 and abs(dsucc) <= 0.05:
        return "neutral"
    if r > 1.2:
        return "elevated_unconfirmed"
    return "neutral_or_lower"


def material_check(k3, k26, k27):
    """Frozen thresholds; returns (verdict, reasons)."""
    reasons = []
    if not k3 or k3["median_reasoning_ratio"] is None:
        return "inconclusive", ["no K3 data"]
    for name, comp in (("K2.6", k26), ("K2.7-Code", k27)):
        if not comp or comp["median_reasoning_ratio"] is None:
            reasons.append(f"comparator {name} missing")
    comps = [c for c in (k26, k27) if c and c["median_reasoning_ratio"]]
    if len(comps) == 2:
        diffs = [abs(k3["median_reasoning_ratio"] - c["median_reasoning_ratio"])
                 / c["median_reasoning_ratio"] for c in comps]
        if all(d > TH["reasoning_ratio_relative_diff"] for d in diffs):
            reasons.append(f"reasoning ratio differs >{TH['reasoning_ratio_relative_diff']:.0%} "
                           f"from both (diffs {diffs[0]:.0%}, {diffs[1]:.0%})")
        cls3 = classify_effect(k3)
        if all(classify_effect(c) != cls3 for c in comps) and cls3 in ("wasteful", "neutral"):
            reasons.append(f"classification flip: K3={cls3} vs "
                           f"{[classify_effect(c) for c in comps]}")
        for c, name in zip(comps, ("K2.6", "K2.7-Code")):
            pass
        scope_diffs = [abs((k3["scope_success"] or 0) - (c["scope_success"] or 0)) * 100
                       for c in comps]
        if all(d > TH["scope_success_pp"] for d in scope_diffs):
            reasons.append(f"scope-compliant success differs >{TH['scope_success_pp']}pp from both")
        for metric in ("median_tool_ratio", "median_turn_ratio"):
            vals = [c.get(metric) for c in comps]
            if k3.get(metric) and all(v for v in vals):
                dd = [abs(k3[metric] - v) / v for v in vals]
                if all(d > TH["tool_calls_or_turns_relative_diff"] for d in dd):
                    reasons.append(f"{metric} differs >30% from both")
    material = [r for r in reasons if "missing" not in r]
    if material:
        return "materially_different", material
    if any("missing" in r for r in reasons):
        return "inconclusive", reasons
    # similar, but flag power honestly
    if k3["n_runs"] < 12 or (k3["ci_high"] or 0) - (k3["ci_low"] or 0) > 2.0:
        return "practically_similar_low_power", ["within thresholds; wide CI"]
    return "practically_similar", ["within all frozen thresholds"]


def main():
    runs = read_jsonl(ROOT / "results/runs.jsonl")
    k3_rows, comp_rows = [], []
    for harness, exps_k3, exps_cmp, tasks in (
            ("pi", {"kimi3_pi"}, {"screening_pi"}, PI_TASKS),
            ("claude-code", {"kimi3_cc"}, {"screening_cc", "pilot_b"}, CC_TASKS)):
        s3 = stats_for(runs, exps_k3, K3, tasks, harness)
        s26 = stats_for(runs, exps_cmp, K26, tasks, harness)
        s27 = stats_for(runs, exps_cmp, K27, tasks, harness)
        for v in VARIANTS:
            if v in s3:
                k3_rows.append({"harness": harness, "variant": v, **s3[v],
                                "classification": classify_effect(s3.get(v))})
            for model, s in ((K3, s3), (K26, s26), (K27, s27)):
                if v in s:
                    verdict, reasons = (material_check(s3.get(v), s26.get(v), s27.get(v))
                                        if model == K3 else (None, None))
                    comp_rows.append({
                        "harness": harness, "variant": v, "model": model,
                        **s[v], "classification": classify_effect(s.get(v)),
                        "material_verdict": verdict,
                        "material_reasons": "; ".join(reasons) if reasons else None,
                    })
    OUT.mkdir(parents=True, exist_ok=True)
    for fname, rows in (("kimi3_small_replication.csv", k3_rows),
                        ("kimi_generation_small_comparison.csv", comp_rows)):
        if rows:
            with open(OUT / fname, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
    for r in comp_rows:
        tag = f" -> {r['material_verdict']}" if r["material_verdict"] else ""
        print(f"{r['harness']:11s} {r['variant']:22s} {r['model'].split('/')[-1]:14s} "
              f"ratio={r['median_reasoning_ratio']} ci=[{r['ci_low']},{r['ci_high']}] "
              f"scope={r['scope_success']} cls={r['classification']}{tag}")
        if r["material_reasons"] and r["material_verdict"] not in (
                "practically_similar", "practically_similar_low_power"):
            print(f"{'':11s}   reasons: {r['material_reasons']}")
    print(f"\nwrote {len(k3_rows)}+{len(comp_rows)} rows to results/summaries/")


if __name__ == "__main__":
    main()
