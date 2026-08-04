#!/usr/bin/env python3
"""Expansion analysis: E11/E12 (paraphrase generalization) + repetition
stability, per EXPANSION-PREREGISTRATION.md (frozen 5db5bb2).

Emits results/summaries/expansion_paraphrase.csv and
results/summaries/expansion_stability.csv.
"""
import csv
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import ROOT, read_jsonl

OUT = ROOT / "results/summaries"
CONDS = ["multiple_approaches", "deep_thinking", "max_certainty",
         "bounded_efficiency"]
FORMS = ["direct", "polite", "concise", "verbose"]


def med(v):
    v = [x for x in v if x is not None]
    return st.median(v) if v else None


def load(exp):
    rows = []
    for r in read_jsonl(ROOT / "results/runs.jsonl"):
        if r.get("experiment") == exp and r.get("run_validity") == "valid":
            rows.append(r)
    return rows


def paraphrase():
    rows = load("exp_paraphrase")
    base = defaultdict(list)   # (model, task) -> baseline reasoning
    for r in rows:
        if r["variant"] == "baseline":
            base[(r["model"], r["task_id"])].append(r)
    out = []
    # per condition x form x model: paired reasoning ratio vs baseline
    eff = defaultdict(list)    # (cond, form, model) -> ratios
    for r in rows:
        v = r["variant"]
        if not v.startswith("xp_"):
            continue
        b = base.get((r["model"], r["task_id"]))
        bmed = med([x.get("reasoning_tokens") for x in b]) if b else None
        if not bmed or r.get("reasoning_tokens") is None:
            continue
        ratio = r["reasoning_tokens"] / bmed
        if v.endswith("_direct_first"):
            cond, form = v[3:-13], "direct_first"
        elif v in ("xp_control_short", "xp_control_long"):
            cond, form = "control", v[11:]
        else:
            for c in CONDS:
                if v.startswith(f"xp_{c}_"):
                    cond, form = c, v[len(c) + 4:]
                    break
            else:
                continue
        eff[(cond, form, r["model"])].append(ratio)
    models = sorted({m for _, _, m in eff})
    for cond in CONDS + ["control"]:
        forms = FORMS + ["direct_first"] if cond != "control" else ["short", "long"]
        for form in forms:
            per_model = {m: med(eff.get((cond, form, m), [])) for m in models}
            vals = [v for v in per_model.values() if v]
            if not vals:
                continue
            out.append({"condition": cond, "form": form,
                        "n_models": len(vals),
                        "median_reasoning_ratio": round(med(vals), 3),
                        "min": round(min(vals), 3), "max": round(max(vals), 3),
                        **{f"m_{m.split('/')[-1]}": round(v, 2) if v else None
                           for m, v in per_model.items()}})
    # E11 verdict per condition x model: same-sign (>1 for waste conds,
    # any-sign consistency) across the 4 paraphrase forms
    e11 = []
    for cond in CONDS:
        for m in models:
            forms_up = [1 if med(eff.get((cond, f, m), [])) and
                        med(eff.get((cond, f, m))) > 1 else 0 for f in FORMS]
            e11.append({"condition": cond, "model": m.split('/')[-1],
                        "forms_with_ratio_gt1": sum(forms_up), "of": 4})
    # E12: heterogeneity — spread across forms within condition vs conditions
    e12 = []
    for cond in CONDS:
        form_meds = [med([x for m in models
                          for x in eff.get((cond, f, m), [])]) for f in FORMS]
        form_meds = [x for x in form_meds if x]
        pos_pair = (med([x for m in models for x in eff.get((cond, "direct", m), [])]),
                    med([x for m in models for x in eff.get((cond, "direct_first", m), [])]))
        e12.append({"condition": cond,
                    "across_form_range": f"{min(form_meds):.2f}-{max(form_meds):.2f}",
                    "position_last_vs_first": f"{pos_pair[0]:.2f} vs {pos_pair[1]:.2f}"})
    return out, e11, e12


def stability():
    rows = load("exp_stability")
    cells = defaultdict(list)
    for r in rows:
        cells[(r["model"], r["task_id"], r["variant"])].append(r)
    base_med = {}
    for (m, t, v), rs in cells.items():
        if v == "baseline":
            base_med[(m, t)] = med([r.get("reasoning_tokens") for r in rs])
    out = []
    per_variant = defaultdict(lambda: {"cv_cost": [], "cv_reason": [],
                                       "succ_agree": [], "reversal": []})
    for (m, t, v), rs in cells.items():
        costs = [r.get("estimated_no_cache_cost_usd") for r in rs if r.get("estimated_no_cache_cost_usd")]
        reas = [r.get("reasoning_tokens") for r in rs if r.get("reasoning_tokens") is not None]
        succ = [1 if r.get("scope_compliant_success") else 0 for r in rs]
        d = per_variant[v]
        if len(costs) >= 3 and med(costs):
            d["cv_cost"].append(st.pstdev(costs) / st.mean(costs))
        if len(reas) >= 3 and st.mean(reas) > 0:
            d["cv_reason"].append(st.pstdev(reas) / st.mean(reas))
        if succ:
            d["succ_agree"].append(1 if len(set(succ)) == 1 else 0)
        if v != "baseline":
            bm = base_med.get((m, t))
            if bm and reas:
                deltas = [x - bm for x in reas]
                mdel = med(deltas)
                if mdel:
                    d["reversal"].append(
                        sum(1 for x in deltas if (x > 0) != (mdel > 0)) / len(deltas))
    for v, d in sorted(per_variant.items()):
        out.append({"variant": v,
                    "n_cells": len(d["cv_cost"]),
                    "median_within_cell_cost_CV": round(med(d["cv_cost"]), 3)
                                                  if d["cv_cost"] else None,
                    "median_within_cell_reasoning_CV": round(med(d["cv_reason"]), 3)
                                                       if d["cv_reason"] else None,
                    "success_unanimous_share": round(st.mean(d["succ_agree"]), 3)
                                               if d["succ_agree"] else None,
                    "median_sign_reversal_prob": round(med(d["reversal"]), 3)
                                                 if d["reversal"] else None})
    return out


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
    print(f"wrote {len(rows)} -> {path.name}")


def main():
    para, e11, e12 = paraphrase()
    write(OUT / "expansion_paraphrase.csv", para)
    stab = stability()
    write(OUT / "expansion_stability.csv", stab)
    print("\n== E11 (forms with ratio>1, of 4 paraphrases) ==")
    agg = defaultdict(list)
    for r in e11:
        agg[r["condition"]].append(r["forms_with_ratio_gt1"])
    for c, xs in agg.items():
        print(f"  {c:22s} per-model: {xs} (>=3/4 = generalizes)")
    print("\n== E12 (heterogeneity) ==")
    for r in e12:
        print(f"  {r['condition']:22s} across-form range {r['across_form_range']} | "
              f"position last-vs-first {r['position_last_vs_first']}")
    print("\n== paraphrase summary (pooled across 3 models) ==")
    for r in para:
        if r["form"] in ("direct", "verbose", "concise", "polite", "direct_first",
                         "short", "long"):
            print(f"  {r['condition']:20s} {r['form']:13s} ratio={r['median_reasoning_ratio']} "
                  f"[{r['min']},{r['max']}]")
    print("\n== stability ==")
    for r in stab:
        print(f"  {r['variant']:24s} costCV={r['median_within_cell_cost_CV']} "
              f"reasCV={r['median_within_cell_reasoning_CV']} "
              f"succ_unanimous={r['success_unanimous_share']} "
              f"sign_reversal={r['median_sign_reversal_prob']}")


if __name__ == "__main__":
    main()
