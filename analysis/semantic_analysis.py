#!/usr/bin/env python3
"""Semantic analysis: paired variant-vs-baseline stats over Method B proxies
and (when present) Method A judge annotations. Frozen rubric v1, §8.

Emits:
- results/summaries/semantic_proxies_paired.csv   (Method B, per harness x model x variant)
- results/summaries/semantic_judge_paired.csv     (Method A, same shape)
- results/summaries/semantic_correlations.csv
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import ROOT, read_jsonl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_results import bootstrap_ci, med

OUT = ROOT / "results/summaries"
SEM = ROOT / "results/semantic"

PROXY_METRICS = [
    "thinking_chars", "tool_calls_before_first_edit",
    "thinking_chars_before_first_edit", "tool_calls_after_first_green",
    "test_runs_after_first_green", "postgreen_chars", "files_read_not_edited",
    "task_restatement_index", "redundancy_compression_ratio",
    "alt_markers_per_1k", "plan_markers_per_1k", "alt_markers_total",
]
JUDGE_METRICS = [
    ("composition", "alternative_approaches_considered"),
    ("composition", "alternatives_implemented"),
    ("composition", "planning"), ("composition", "hypotheses_stated"),
    ("composition", "hypotheses_grounded"), ("composition", "evidence_collection"),
    ("composition", "error_diagnosis"), ("composition", "self_corrections"),
    ("composition", "final_validation"), ("composition", "testing_verification"),
    ("waste", "unused_branches"), ("waste", "task_restatements"),
    ("waste", "redundant_verification"), ("waste", "speculative_architecture"),
    ("waste", "post_solution_reasoning"), ("waste", "planning_without_implementation"),
    ("quality", "factual_grounding"), ("quality", "unsupported_assumptions"),
    ("quality", "reversals_without_new_evidence"),
    ("quality", "task_relevance"), ("quality", "uncertainty_calibration"),
]

# Baseline experiment mapping: stress variants pair against screening baselines
BASELINE_EXP = {"stress_pi": "screening_pi", "kimi3_pi": "kimi3_pi",
                "holdout_pi": "holdout_pi"}


def fnum(x):
    try:
        v = float(x)
        return v
    except (TypeError, ValueError):
        return None


def paired_rows(rows, metrics, getv):
    """rows: list of dicts with harness/model/task_id/variant/experiment.
    Returns per (harness, model, variant) paired stats vs baseline."""
    base = defaultdict(list)   # (harness, model, task, exp) -> rows
    for r in rows:
        if r["variant"] == "baseline":
            base[(r["harness"], r["model"], r["task_id"], r["experiment"])].append(r)
    out = []
    groups = defaultdict(list)
    for r in rows:
        if r["variant"] != "baseline":
            groups[(r["harness"], r["model"], r["variant"], r["experiment"])].append(r)
    for (h, m, v, e), vr in sorted(groups.items()):
        bexp = BASELINE_EXP.get(e, e)
        rec = {"harness": h, "model": m, "variant": v, "experiment": e,
               "n_runs": len(vr)}
        for metric in metrics:
            name = metric if isinstance(metric, str) else f"{metric[0]}.{metric[1]}"
            ratios_by_task, deltas_by_task = defaultdict(list), defaultdict(list)
            for r in vr:
                b = base.get((h, m, r["task_id"], bexp), [])
                bvals = [getv(x, metric) for x in b]
                bvals = [x for x in bvals if x is not None]
                val = getv(r, metric)
                if val is None or not bvals:
                    continue
                bmed = med(bvals)
                deltas_by_task[r["task_id"]].append(val - bmed)
                if bmed and bmed > 0:
                    ratios_by_task[r["task_id"]].append(val / bmed)
            deltas = [x for xs in deltas_by_task.values() for x in xs]
            ratios = [x for xs in ratios_by_task.values() for x in xs]
            if deltas:
                lo, hi = bootstrap_ci(dict(deltas_by_task), med)
                rec[f"{name}__delta"] = round(med(deltas), 4)
                rec[f"{name}__delta_ci"] = f"[{lo:.3f},{hi:.3f}]" if lo is not None else None
                rec[f"{name}__ratio"] = round(med(ratios), 3) if ratios else None
                rec[f"{name}__n"] = len(deltas)
        out.append(rec)
    return out


def load_proxies():
    rows = []
    with open(OUT / "semantic_proxies.csv") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def proxy_get(r, metric):
    return fnum(r.get(metric))


def load_judge():
    ann_path = SEM / "annotations_primary.jsonl"
    if not ann_path.exists():
        return []
    ann = {}
    for j in read_jsonl(ann_path):
        if j.get("annotation"):
            ann[j["run_id"]] = j["annotation"]
    ledger = {r["run_id"]: r for r in read_jsonl(ROOT / "results/runs.jsonl")
              if "run_id" in r}
    rows = []
    for rid, a in ann.items():
        r = ledger.get(rid)
        if not r:
            continue
        rows.append({"run_id": rid, "harness": r["harness"], "model": r["model"],
                     "task_id": r["task_id"], "variant": r["variant"],
                     "experiment": r["experiment"], "_ann": a,
                     "reasoning_tokens": r.get("reasoning_tokens"),
                     "scope_compliant_success": r.get("scope_compliant_success")})
    return rows


def judge_get(r, metric):
    sec, key = metric
    try:
        return fnum(r["_ann"][sec][key])
    except (KeyError, TypeError):
        return None


def correlations(proxies, judge_rows):
    """Spearman correlations between semantic waste and quantitative metrics."""
    def spearman(pairs):
        xs = [p[0] for p in pairs]; ys = [p[1] for p in pairs]
        def rank(v):
            order = sorted(range(len(v)), key=lambda i: v[i])
            rk = [0.0] * len(v)
            i = 0
            while i < len(order):
                j = i
                while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                    j += 1
                avg = (i + j) / 2 + 1
                for k in range(i, j + 1):
                    rk[order[k]] = avg
                i = j + 1
            return rk
        rx, ry = rank(xs), rank(ys)
        n = len(pairs)
        mx = sum(rx) / n; my = sum(ry) / n
        num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
        dx = (sum((a - mx) ** 2 for a in rx)) ** 0.5
        dy = (sum((b - my) ** 2 for b in ry)) ** 0.5
        return num / (dx * dy) if dx and dy else None

    judge_by_id = {r["run_id"]: r for r in judge_rows}
    quant_keys = ["reasoning_tokens", "visible_output_tokens",
                  "tool_total_tool_calls", "turns", "estimated_no_cache_cost_usd"]
    sem_keys = [("waste", "unused_branches"), ("waste", "redundant_verification"),
                ("waste", "task_restatements"), ("waste", "post_solution_reasoning"),
                ("quality", "unsupported_assumptions")]
    out = []
    for sk in sem_keys:
        for qk in quant_keys:
            pairs = []
            for p in proxies:
                jr = judge_by_id.get(p["run_id"])
                if not jr:
                    continue
                sv = judge_get(jr, sk)
                qv = fnum(p.get(qk))
                if sv is not None and qv is not None:
                    pairs.append((sv, qv))
            if len(pairs) >= 30:
                out.append({"semantic": f"{sk[0]}.{sk[1]}", "quant": qk,
                            "spearman_rho": round(spearman(pairs), 3),
                            "n": len(pairs)})
    # success link
    for sk in sem_keys:
        pairs = []
        for jr in judge_rows:
            sv = judge_get(jr, sk)
            if sv is not None:
                pairs.append((sv, 1 if jr.get("scope_compliant_success") else 0))
        if len(pairs) >= 30:
            out.append({"semantic": f"{sk[0]}.{sk[1]}", "quant": "scope_compliant_success",
                        "spearman_rho": round(spearman(pairs), 3), "n": len(pairs)})
    return out


def write_csv(path, rows):
    if not rows:
        return
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {path.relative_to(ROOT)}")


def main():
    proxies = load_proxies()
    write_csv(OUT / "semantic_proxies_paired.csv",
              paired_rows(proxies, PROXY_METRICS, proxy_get))
    judge_rows = load_judge()
    if judge_rows:
        write_csv(OUT / "semantic_judge_paired.csv",
                  paired_rows(judge_rows, JUDGE_METRICS, judge_get))
        write_csv(OUT / "semantic_correlations.csv",
                  correlations(proxies, judge_rows))
    else:
        print("no judge annotations yet; Method B only")


if __name__ == "__main__":
    main()
