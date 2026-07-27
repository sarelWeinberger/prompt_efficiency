#!/usr/bin/env python3
"""Holdout confirmation analysis (design §22).

For each model and each frozen selected feature: does the waste effect
replicate on the 8 never-before-seen holdout tasks? A feature is CONFIRMED
when the holdout median reasoning ratio > 1.5 with CI lower bound > 1.1 and
no material success gain; REPLICATED_WEAKER when ratio > 1.2 with CI > 1.0;
NOT_REPLICATED otherwise. bounded_efficiency is evaluated against its own
pilot claim (ratio <= 1.2, no success loss).

Writes results/summaries/holdout_confirmation.csv and prints the verdicts.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import ROOT, read_jsonl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_results import analyze

OUT = ROOT / "results/summaries"


def verdict(row, control=False):
    r, lo = row["median_reasoning_ratio"], row["ratio_ci_low"]
    if r is None or row["n_runs"] < 10:
        return "underpowered"
    dsucc = (row["success_rate"] or 0) - (row["baseline_success_rate"] or 0)
    if control:  # bounded_efficiency: claim is neutrality
        return ("confirmed_neutral" if r <= 1.2 and dsucc >= -0.10
                else "not_replicated")
    if r > 1.5 and (lo or 0) > 1.1 and dsucc <= 0.10:
        return "confirmed_wasteful"
    if r > 1.2 and (lo or 0) > 1.0 and dsucc <= 0.10:
        return "replicated_weaker"
    if dsucc < -0.10 and r > 1.1:
        return "harmful_overthinking"
    return "not_replicated"


def main():
    selection = json.loads((ROOT / "results/holdout_selection.json").read_text())
    runs = read_jsonl(ROOT / "results/runs.jsonl")
    rows_out = []
    for exp, harness in (("holdout_pi", "pi"), ("holdout_cc", "claude-code")):
        table, _ = analyze(runs, experiment_filter={exp})
        for row in table:
            if row["harness"] != harness:
                continue
            selected = row["variant"] in selection.get(row["model"], [])
            control = row["variant"] == "bounded_efficiency"
            if not (selected or control):
                continue
            row2 = dict(row)
            row2["experiment"] = exp
            row2["selected_feature"] = selected
            row2["holdout_verdict"] = verdict(row, control=control)
            rows_out.append(row2)
    OUT.mkdir(parents=True, exist_ok=True)
    if rows_out:
        with open(OUT / "holdout_confirmation.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
            w.writeheader()
            w.writerows(rows_out)
    for r in sorted(rows_out, key=lambda x: (x["experiment"], x["model"], x["variant"])):
        print(f"{r['experiment']:11s} {r['model'].split('/')[-1]:26s} "
              f"{r['variant']:24s} ratio={r['median_reasoning_ratio']} "
              f"ci=[{r['ratio_ci_low']},{r['ratio_ci_high']}] n={r['n_runs']} "
              f"-> {r['holdout_verdict']}")
    print(f"\nwrote {OUT/'holdout_confirmation.csv'} ({len(rows_out)} rows)")


if __name__ == "__main__":
    main()
