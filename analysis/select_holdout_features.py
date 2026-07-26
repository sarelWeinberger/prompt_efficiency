#!/usr/bin/env python3
"""Freeze the holdout variant selection (design §22).

Per model: the three most waste-inducing prompt variants, ranked by median
reasoning ratio vs paired baseline on DEVELOPMENT-task screening data only,
requiring n_runs >= min_n. baseline and bounded_efficiency are excluded from
selection (they are always run in the holdout as controls).

Writes results/holdout_selection.json. Refuses to overwrite an existing file
unless --force: the selection is FROZEN once holdout runs begin.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import ROOT, read_jsonl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_results import analyze

OUT = ROOT / "results/holdout_selection.json"
EXCLUDE = {"baseline", "bounded_efficiency", "goal_only", "scoped_authorization"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiments", default="screening_pi,screening_cc,pilot_a,pilot_b")
    ap.add_argument("--min-n", type=int, default=6)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if OUT.exists() and not args.force:
        print(f"{OUT} already exists — selection is frozen. Use --force to redo "
              "(only before any holdout run).")
        sys.exit(1)

    runs = read_jsonl(ROOT / "results/runs.jsonl")
    table, _ = analyze(runs, experiment_filter=set(args.experiments.split(",")))
    by_model = defaultdict(list)
    for row in table:
        if row["variant"] in EXCLUDE:
            continue
        if row["median_reasoning_ratio"] is None or row["n_runs"] < args.min_n:
            continue
        by_model[row["model"]].append(row)

    selection = {}
    evidence = {}
    for model, rows in by_model.items():
        # pool across harnesses: prefer the strongest per-variant evidence
        best = {}
        for r in rows:
            v = r["variant"]
            if v not in best or (r["median_reasoning_ratio"] or 0) > (
                    best[v]["median_reasoning_ratio"] or 0):
                best[v] = r
        ranked = sorted(best.values(),
                        key=lambda r: -(r["median_reasoning_ratio"] or 0))
        top = ranked[:3]
        selection[model] = [r["variant"] for r in top]
        evidence[model] = [{"variant": r["variant"],
                            "harness": r["harness"],
                            "ratio": r["median_reasoning_ratio"],
                            "ci": [r["ratio_ci_low"], r["ratio_ci_high"]],
                            "n": r["n_runs"],
                            "classification": r["classification"]} for r in top]

    OUT.write_text(json.dumps(selection, indent=1))
    (ROOT / "results/holdout_selection_evidence.json").write_text(
        json.dumps(evidence, indent=1))
    print(json.dumps(selection, indent=1))
    print(f"FROZEN -> {OUT}")


if __name__ == "__main__":
    main()
