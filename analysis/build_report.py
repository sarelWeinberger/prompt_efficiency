#!/usr/bin/env python3
"""Generate the data-driven markdown tables for RESULTS.md / HARNESS-COMPARISON.md.

Reads results/summaries/*.csv + results/runs.jsonl and prints markdown blocks
(picked up by the hand-written narrative reports).
"""
import csv
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import ROOT, read_jsonl

SUM = ROOT / "results/summaries"


def med(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else None


def fmt(x, nd=2):
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def sensitivity_tables():
    rows = list(csv.DictReader(open(SUM / "prompt_sensitivity.csv")))
    for r in rows:
        for k in ("median_reasoning_ratio", "ratio_ci_low", "ratio_ci_high",
                  "success_rate", "baseline_success_rate", "median_reasoning",
                  "median_excess_reasoning", "median_tool_calls",
                  "median_repeated_ops", "nocache_cost_per_success"):
            r[k] = float(r[k]) if r.get(k) not in (None, "", "None") else None
    print("\n## Prompt-variant effects vs paired baseline (median reasoning ratio)\n")
    for harness in ("pi", "claude-code"):
        hr = [r for r in rows if r["harness"] == harness]
        if not hr:
            continue
        models = sorted({r["model"] for r in hr})
        variants = sorted({r["variant"] for r in hr})
        print(f"\n### {harness}\n")
        print("| variant | " + " | ".join(m.split("/")[-1] for m in models) + " |")
        print("|---|" + "---|" * len(models))
        for v in variants:
            cells = []
            for m in models:
                r = next((x for x in hr if x["model"] == m and x["variant"] == v), None)
                if r is None or r["median_reasoning_ratio"] is None:
                    cells.append("—")
                else:
                    cls = {"wasteful": "**W**", "harmful_overthinking": "**H!**",
                           "useful_deliberation": "U", "neutral": "·",
                           "inconclusive": "?"}[r["classification"]]
                    dsucc = ((r["success_rate"] or 0)
                             - (r["baseline_success_rate"] or 0))
                    cells.append(f"{r['median_reasoning_ratio']:.2f}x "
                                 f"({dsucc:+.0%}) {cls}")
            print(f"| {v} | " + " | ".join(cells) + " |")
    print("\nCell: median reasoning-token ratio vs paired baseline "
          "(Δ success rate) classification — **W** wasteful, **H!** harmful "
          "overthinking, U useful, · neutral, ? inconclusive.\n")


def harness_comparison():
    runs = [r for r in read_jsonl(ROOT / "results/runs.jsonl")
            if r.get("run_validity") == "valid" and r.get("status") == "completed"
            and r.get("experiment") in ("pilot_a", "pilot_b")]
    shared_tasks = sorted({r["task_id"] for r in runs if r["harness"] == "claude-code"}
                          & {r["task_id"] for r in runs if r["harness"] == "pi"})
    shared_variants = sorted({r["variant"] for r in runs if r["harness"] == "claude-code"}
                             & {r["variant"] for r in runs if r["harness"] == "pi"})
    print(f"\n## Matched harness comparison "
          f"(tasks: {', '.join(shared_tasks)}; variants: {', '.join(shared_variants)})\n")
    print("| model | harness | n | success | reasoning (med) | tool calls | "
          "turns | logical input | reported $/success | no-cache $/success | wall s |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    grp = defaultdict(list)
    for r in runs:
        if r["task_id"] in shared_tasks and r["variant"] in shared_variants:
            grp[(r["model"], r["harness"])].append(r)
    for (model, harness), rs in sorted(grp.items()):
        n_succ = sum(1 for r in rs if r.get("task_success"))
        succ = n_succ / len(rs)
        cost = sum(r.get("reported_cost_usd") or 0 for r in rs)
        ncost = sum(r.get("estimated_no_cache_cost_usd") or 0 for r in rs)
        print(f"| {model.split('/')[-1]} | {harness} | {len(rs)} | {succ:.0%} | "
              f"{fmt(med([r.get('reasoning_tokens') for r in rs]), 0)} | "
              f"{fmt(med([r.get('tool_total_tool_calls') for r in rs]), 1)} | "
              f"{fmt(med([r.get('turns') for r in rs]), 0)} | "
              f"{fmt(med([r.get('logical_input_tokens') for r in rs]), 0)} | "
              f"{fmt(cost / n_succ if n_succ else None, 4)} | "
              f"{fmt(ncost / n_succ if n_succ else None, 4)} | "
              f"{fmt(med([r.get('wall_s') for r in rs]), 0)} |")


def scope_and_oos():
    runs = [r for r in read_jsonl(ROOT / "results/runs.jsonl")
            if r.get("run_validity") == "valid" and r.get("status") == "completed"]
    print("\n## Out-of-scope changes by variant (both harnesses pooled)\n")
    grp = defaultdict(list)
    for r in runs:
        grp[r["variant"]].append(1 if r.get("out_of_scope_changes") else 0)
    print("| variant | n | runs with out-of-scope changes |")
    print("|---|---|---|")
    for v, xs in sorted(grp.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
        print(f"| {v} | {len(xs)} | {sum(xs)/len(xs):.0%} |")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "sensitivity"):
        sensitivity_tables()
    if which in ("all", "harness"):
        harness_comparison()
    if which in ("all", "scope"):
        scope_and_oos()
