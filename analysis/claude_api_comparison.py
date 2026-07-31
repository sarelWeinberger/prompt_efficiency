#!/usr/bin/env python3
"""Claude-API study analysis (post-registration, frozen 2026-07-31).

Compares prompt-family effects on claude-sonnet-5 (first-party Anthropic API;
pi --provider anthropic + Claude Code native) against the six open-weight
Together models from the main screening phase, on the same tasks.

PRIMARY METRIC (frozen before results): paired TOTAL-OUTPUT-token ratio vs the
model's own baseline. Rationale: the Anthropic API bills thinking inside
output_tokens and never reports it separately
(reasoning_token_status = included_in_output_but_not_separable), while
Together's completion_tokens likewise includes reasoning tokens - so total
output is the one deliberation+response measure defined identically on both
providers. Reasoning-token ratios are reported for open models as reference
only.

Emits results/summaries/claude_api_comparison.csv.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import ROOT, read_jsonl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_results import bootstrap_ci, med

OUT = ROOT / "results/summaries"
PI_TASKS = ["py-low-01", "go-low-01", "py-med-01", "js-med-03", "js-high-01", "go-high-01"]
CC_TASKS = ["py-low-01", "js-med-03", "js-high-01"]
VARIANTS = ["verbose_repetition", "deep_thinking", "exhaustive_exploration",
            "multiple_approaches", "max_certainty", "adjacent_cleanup",
            "no_questions_autonomy", "bounded_efficiency"]
CLAUDE = "claude-sonnet-5"
OPEN_MODELS = ["deepseek-ai/DeepSeek-V4-Pro", "moonshotai/Kimi-K2.6",
               "moonshotai/Kimi-K2.7-Code", "nvidia/nemotron-3-ultra-550b-a55b",
               "inclusionai/Inkling", "zai-org/GLM-5.2"]


def stats_for(runs, experiments, model, tasks, harness):
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
        out_by_task, reas_r, tool_r, turn_r = defaultdict(list), [], [], []
        scope, costs, ncosts = [], [], []
        for r in vr:
            b = base.get(r["task_id"], [])
            bout = med([x.get("visible_output_tokens") for x in b])
            if bout and r.get("visible_output_tokens") is not None:
                out_by_task[r["task_id"]].append(r["visible_output_tokens"] / bout)
            breas = med([x.get("reasoning_tokens") for x in b])
            if breas and r.get("reasoning_tokens") is not None:
                reas_r.append(r["reasoning_tokens"] / breas)
            btool = med([x.get("tool_total_tool_calls") for x in b])
            bturn = med([x.get("turns") for x in b])
            if btool and r.get("tool_total_tool_calls") is not None:
                tool_r.append(r["tool_total_tool_calls"] / btool)
            if bturn and r.get("turns") is not None:
                turn_r.append(r["turns"] / bturn)
            scope.append(1 if r.get("scope_compliant_success") else 0)
            costs.append(r.get("reported_cost_usd") or 0)
            ncosts.append(r.get("estimated_no_cache_cost_usd") or 0)
        ratios = [x for xs in out_by_task.values() for x in xs]
        lo, hi = bootstrap_ci(dict(out_by_task), med)
        n_ok = sum(scope)
        base_scope = [1 if x.get("scope_compliant_success") else 0
                      for xs in base.values() for x in xs]
        base_ncost = [x.get("estimated_no_cache_cost_usd") or 0
                      for xs in base.values() for x in xs]
        out[v] = {
            "n_runs": len(vr),
            "n_tasks": len({r["task_id"] for r in vr}),
            "median_output_ratio": round(med(ratios), 3) if ratios else None,
            "ci_low": round(lo, 3) if lo else None,
            "ci_high": round(hi, 3) if hi else None,
            "n_tasks_ratio_gt1": sum(1 for xs in out_by_task.values()
                                     if med(xs) and med(xs) > 1),
            "median_reasoning_ratio_ref": round(med(reas_r), 3) if reas_r else None,
            "scope_success": round(sum(scope) / len(scope), 3) if scope else None,
            "baseline_scope_success": round(sum(base_scope) / len(base_scope), 3)
                                      if base_scope else None,
            "median_tool_ratio": round(med(tool_r), 3) if tool_r else None,
            "median_turn_ratio": round(med(turn_r), 3) if turn_r else None,
            "cost_per_compliant_success": round(sum(costs) / n_ok, 5) if n_ok else None,
            "nocache_cost_per_compliant_success": round(sum(ncosts) / n_ok, 5)
                                                  if n_ok else None,
            "baseline_median_nocache_cost": round(med(base_ncost), 5)
                                            if base_ncost else None,
        }
    return out


def classify_output_effect(s):
    """Section-24 waste rule applied to the output-token ratio (this study's
    primary metric); same thresholds, different substrate - labeled distinctly."""
    if s is None or s["median_output_ratio"] is None or s["n_runs"] < 3:
        return "inconclusive"
    r, lo = s["median_output_ratio"], s["ci_low"] or 0
    dsucc = (s["scope_success"] or 0) - (s["baseline_scope_success"] or 0)
    if r > 1.5 and lo > 1.1 and dsucc <= 0.10:
        return "output_wasteful"
    if r <= 1.2 and abs(dsucc) <= 0.05:
        return "neutral"
    if r > 1.2:
        return "elevated_unconfirmed"
    return "neutral_or_lower"


def main():
    runs = read_jsonl(ROOT / "results/runs.jsonl")
    rows = []
    for harness, exps_claude, exps_open, tasks in (
            ("pi", {"anthropic_pi"}, {"screening_pi"}, PI_TASKS),
            ("claude-code", {"anthropic_cc"}, {"screening_cc", "pilot_b"}, CC_TASKS)):
        stats = {CLAUDE: stats_for(runs, exps_claude, CLAUDE, tasks, harness)}
        for m in OPEN_MODELS:
            stats[m] = stats_for(runs, exps_open, m, tasks, harness)
        for v in VARIANTS:
            for m in [CLAUDE] + OPEN_MODELS:
                s = stats[m].get(v)
                if s:
                    rows.append({"harness": harness, "variant": v, "model": m,
                                 "provider": "anthropic" if m == CLAUDE else "together",
                                 **s, "classification": classify_output_effect(s)})
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "claude_api_comparison.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        if r["model"] == CLAUDE:
            print(f"{r['harness']:11s} {r['variant']:22s} out_ratio="
                  f"{r['median_output_ratio']} ci=[{r['ci_low']},{r['ci_high']}] "
                  f"scope={r['scope_success']} cls={r['classification']}")
    print(f"\nwrote {len(rows)} rows to results/summaries/claude_api_comparison.csv")


if __name__ == "__main__":
    main()
