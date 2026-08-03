#!/usr/bin/env python3
"""Validation for the semantic judge (rubric v1 §6): agreement between judge
configurations, evidence-rule compliance, and verbosity-leakage diagnostics.

Usage:
  python3 analysis/semantic_validation.py --evidence results/semantic/pilot_annotations.jsonl
  python3 analysis/semantic_validation.py --agreement primary alt_prompt
  python3 analysis/semantic_validation.py --agreement primary haiku
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import ROOT, read_jsonl

SEM = ROOT / "results/semantic"

COUNT_FIELDS = [("composition", k) for k in (
    "problem_understanding", "planning", "alternative_approaches_considered",
    "alternatives_implemented", "repo_exploration", "hypotheses_stated",
    "evidence_collection", "error_diagnosis", "self_corrections",
    "final_validation")] + [("waste", k) for k in (
    "unused_branches", "task_restatements", "redundant_verification",
    "speculative_architecture", "post_solution_reasoning",
    "planning_without_implementation")] + [
    ("quality", "unsupported_assumptions"),
    ("quality", "reversals_without_new_evidence")]
ORDINAL_FIELDS = [("quality", k) for k in (
    "task_relevance", "factual_grounding", "logical_consistency",
    "specificity", "actionability", "uncertainty_calibration")]


def get(a, f):
    try:
        return a[f[0]][f[1]]
    except (KeyError, TypeError):
        return None


def load(path):
    out = {}
    for j in read_jsonl(path):
        if j.get("annotation"):
            out[j["run_id"]] = j["annotation"]
    return out


def evidence_check(path):
    """Fraction of nonzero counts backed by at least one evidence item."""
    n_pos = n_backed = n_runs = 0
    for j in read_jsonl(path):
        a = j.get("annotation")
        if not a:
            continue
        n_runs += 1
        fields_with_ev = {e.get("field") for e in a.get("evidence") or []}
        for f in COUNT_FIELDS:
            v = get(a, f)
            if v and v > 0:
                n_pos += 1
                if f[1] in fields_with_ev or f"{f[0]}.{f[1]}" in fields_with_ev:
                    n_backed += 1
    print(f"runs={n_runs} nonzero_counts={n_pos} "
          f"evidence_backed={n_backed} ({n_backed/max(1,n_pos):.1%})")


def kappa(pairs):
    """Cohen's kappa on binarized presence (>0)."""
    a = [(1 if x > 0 else 0, 1 if y > 0 else 0) for x, y in pairs]
    n = len(a)
    if not n:
        return None
    po = sum(1 for x, y in a if x == y) / n
    p1 = sum(x for x, _ in a) / n
    p2 = sum(y for _, y in a) / n
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    return (po - pe) / (1 - pe) if pe < 1 else None


def agreement(j1, j2):
    a1, a2 = load(SEM / f"annotations_{j1}.jsonl"), load(SEM / f"annotations_{j2}.jsonl")
    if j2 == "pilot":
        a2 = load(SEM / "pilot_annotations.jsonl")
    common = sorted(set(a1) & set(a2))
    print(f"{j1} vs {j2}: {len(common)} common runs")
    rows = []
    for f in COUNT_FIELDS:
        pairs = [(get(a1[r], f), get(a2[r], f)) for r in common]
        pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
        if not pairs:
            continue
        within1 = sum(1 for x, y in pairs if abs(x - y) <= 1) / len(pairs)
        k = kappa(pairs)
        rows.append((f"{f[0]}.{f[1]}", len(pairs), round(within1, 3),
                     round(k, 3) if k is not None else None))
    for f in ORDINAL_FIELDS:
        pairs = [(get(a1[r], f), get(a2[r], f)) for r in common]
        pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
        if not pairs:
            continue
        within1 = sum(1 for x, y in pairs if abs(x - y) <= 1) / len(pairs)
        rows.append((f"{f[0]}.{f[1]} (ordinal)", len(pairs), round(within1, 3), None))
    print(f"{'field':45s} {'n':>4s} {'within±1':>9s} {'kappa(>0)':>10s}")
    for name, n, w, k in rows:
        print(f"{name:45s} {n:4d} {w:9.3f} {k if k is not None else '':>10}")
    ws = [w for _, _, w, _ in rows]
    ks = [k for _, _, _, k in rows if k is not None]
    print(f"\nmacro within±1: {sum(ws)/len(ws):.3f} | macro kappa: "
          f"{sum(ks)/len(ks):.3f} (n fields={len(ks)})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence")
    ap.add_argument("--agreement", nargs=2)
    args = ap.parse_args()
    if args.evidence:
        evidence_check(Path(args.evidence))
    if args.agreement:
        agreement(*args.agreement)


if __name__ == "__main__":
    main()
