#!/usr/bin/env python3
"""Score advisor predictions against gold labels.

Usage: score.py --data data/holdout.jsonl --pred results/holdout/gemma.jsonl
                [--json results/holdout/gemma.metrics.json]

Metric definitions (frozen in PROTOCOL.md):

Detection
- A predicted risk is GROUNDED if its evidence string is an exact substring
  of the prompt. Ungrounded risks count toward fabricated_span_rate and are
  IGNORED for detection credit (precision-first).
- A predicted risk of family f is CORRECT if grounded and its evidence
  overlaps (char ranges, first occurrence) any gold span of family f.
  Grounded but non-overlapping predictions of a gold family count as
  family-level FP (right label, wrong evidence).
- Family P/R/F1 over risk-level decisions; macro = unweighted mean over the
  six families; micro = pooled.
- Example-level: pred=warn matches gold=warn only if >=1 correct risk
  ("displayed warning precision"). uncertain = abstention (excluded from
  precision; counted as a miss for recall).
- FPR on neutrals = fraction of gold no_change examples with pred warn.
- Calibration: selective precision at confidence thresholds.

Rewrite safety (deterministic part)
- For examples where a rewrite exists: every gold `protected` string must
  appear verbatim in the rewrite (whitespace-normalized). Missing any =
  critical deletion. Language preservation: if prompt >=20% Hebrew chars,
  rewrite must be >=10% Hebrew chars.
- rewrite_offered_rate, protected_preservation (item level),
  critical_deletion_rate (example level), language_violation_rate.

Schema compliance: parseable JSON with required keys and legal enum values.
"""
import argparse
import json
import re
import unicodedata
from collections import defaultdict

FAMILIES = ["multiple_approaches", "max_certainty", "deep_thinking",
            "exhaustive_exploration", "adjacent_cleanup",
            "missing_stop_conditions"]
RECS = {"warn", "no_change", "uncertain"}


def norm_ws(s):
    return re.sub(r"\s+", " ", s).strip()


def hebrew_ratio(s):
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return 0.0
    heb = sum(1 for c in letters if "֐" <= c <= "׿")
    return heb / len(letters)


def spans_overlap(prompt, a, b):
    """Do first occurrences of substrings a and b overlap in prompt?"""
    ia, ib = prompt.find(a), prompt.find(b)
    if ia < 0 or ib < 0:
        return False
    return max(ia, ib) < min(ia + len(a), ib + len(b))


def schema_ok(p):
    if not isinstance(p, dict):
        return False
    if p.get("recommendation") not in RECS:
        return False
    if not isinstance(p.get("risks"), list):
        return False
    for r in p["risks"]:
        if not isinstance(r, dict) or r.get("type") not in FAMILIES:
            return False
        if not isinstance(r.get("evidence"), str):
            return False
    if not (p.get("revised_prompt") is None or isinstance(p["revised_prompt"], str)):
        return False
    if not isinstance(p.get("confidence"), (int, float)):
        return False
    return True


def score(data_path, pred_path):
    gold = {json.loads(l)["id"]: json.loads(l) for l in open(data_path)}
    preds = {}
    for l in open(pred_path):
        r = json.loads(l)
        preds[r["id"]] = r
    ids = [i for i in gold if i in preds]

    m = defaultdict(float)
    fam = {f: defaultdict(int) for f in FAMILIES}
    confusion = defaultdict(int)
    fp_examples, fn_examples, fab_examples = [], [], []
    rw = defaultdict(float)
    rw_del_examples = []
    cal = []  # (confidence, warn_correct) for displayed warnings
    cat_rec = defaultdict(lambda: defaultdict(int))
    n_risks = 0
    n_fab = 0

    for i in ids:
        g, p = gold[i], preds[i]
        prompt = g["prompt"]
        parsed = p.get("parsed")
        ok = schema_ok(parsed)
        m["n"] += 1
        m["schema_ok"] += ok
        cat = g["category"]
        if not ok:
            parsed = {"recommendation": "uncertain", "risks": [],
                      "revised_prompt": None, "confidence": 0.0}
        rec = parsed["recommendation"]
        gold_rec = g["gold"]["recommendation"]
        confusion[(gold_rec, rec)] += 1
        cat_rec[cat][(gold_rec, rec)] += 1

        gold_fams = {r["type"]: r["gold_spans"] for r in g["gold"]["risks"]}
        alt_ok = set(g["gold"].get("alt_ok", []))
        all_gold_spans = [s for ss in gold_fams.values() for s in ss]

        # risk-level scoring
        pred_correct_fams = set()
        for r in parsed["risks"]:
            n_risks += 1
            ev = r.get("evidence", "")
            grounded = bool(ev) and (ev in prompt)
            if not grounded:
                n_fab += 1
                fab_examples.append((i, r.get("type"), ev[:80]))
                continue
            f = r["type"]
            if f in gold_fams and any(spans_overlap(prompt, ev, s)
                                      for s in gold_fams[f]):
                fam[f]["tp"] += 1
                pred_correct_fams.add(f)
            elif f in alt_ok and any(spans_overlap(prompt, ev, s)
                                     for s in all_gold_spans):
                pass  # acceptable secondary family: neither TP nor FP
            else:
                fam[f]["fp"] += 1
        for f in gold_fams:
            if f not in pred_correct_fams:
                fam[f]["fn"] += 1

        # example level
        if rec == "warn":
            m["warn_shown"] += 1
            correct = gold_rec == "warn" and bool(pred_correct_fams)
            m["warn_correct"] += correct
            cal.append((float(parsed.get("confidence", 0)), correct))
            if gold_rec != "warn":
                fp_examples.append((i, [r["type"] for r in parsed["risks"]]))
        if gold_rec == "warn":
            m["gold_warn"] += 1
            if rec == "warn" and pred_correct_fams:
                m["warn_recalled"] += 1
            else:
                fn_examples.append((i, rec))
        else:
            m["gold_clean"] += 1
            if rec == "warn":
                m["clean_fp"] += 1
        if rec == "uncertain":
            m["abstain"] += 1

        # rewrite safety
        rwp = parsed.get("revised_prompt")
        if isinstance(rwp, str) and rwp.strip():
            m["rewrites"] += 1
            nr = norm_ws(rwp)
            missing = [x for x in g["gold"]["protected"]
                       if norm_ws(x) not in nr]
            rw["prot_total"] += len(g["gold"]["protected"])
            rw["prot_kept"] += len(g["gold"]["protected"]) - len(missing)
            if missing:
                rw["critical_del"] += 1
                rw_del_examples.append((i, missing[:5]))
            if hebrew_ratio(prompt) >= 0.2 and hebrew_ratio(rwp) < 0.1:
                rw["lang_viol"] += 1
            # rewrite of a clean prompt is itself unsafe behavior
            if gold_rec == "no_change":
                rw["rewrite_of_clean"] += 1

    # aggregate
    out = {"n": int(m["n"]), "schema_compliance": m["schema_ok"] / m["n"]}
    out["abstention_rate"] = m["abstain"] / m["n"]
    out["displayed_warning_precision"] = (
        m["warn_correct"] / m["warn_shown"] if m["warn_shown"] else None)
    out["warn_recall"] = (
        m["warn_recalled"] / m["gold_warn"] if m["gold_warn"] else None)
    out["neutral_fpr"] = (
        m["clean_fp"] / m["gold_clean"] if m["gold_clean"] else None)
    out["fabricated_span_rate"] = n_fab / n_risks if n_risks else 0.0
    out["n_predicted_risks"] = n_risks

    per_fam = {}
    for f in FAMILIES:
        tp, fp, fn = fam[f]["tp"], fam[f]["fp"], fam[f]["fn"]
        pr = tp / (tp + fp) if tp + fp else None
        rc = tp / (tp + fn) if tp + fn else None
        f1 = (2 * pr * rc / (pr + rc)) if pr and rc else 0.0
        per_fam[f] = {"tp": tp, "fp": fp, "fn": fn,
                      "precision": pr, "recall": rc, "f1": f1}
    out["per_family"] = per_fam
    tps = sum(fam[f]["tp"] for f in FAMILIES)
    fps = sum(fam[f]["fp"] for f in FAMILIES)
    fns = sum(fam[f]["fn"] for f in FAMILIES)
    out["micro_precision"] = tps / (tps + fps) if tps + fps else None
    out["micro_recall"] = tps / (tps + fns) if tps + fns else None
    prs = [v["precision"] for v in per_fam.values() if v["precision"] is not None]
    rcs = [v["recall"] for v in per_fam.values() if v["recall"] is not None]
    out["macro_precision"] = sum(prs) / len(prs) if prs else None
    out["macro_recall"] = sum(rcs) / len(rcs) if rcs else None

    # calibration / selective precision
    sel = {}
    for th in (0.0, 0.5, 0.7, 0.9):
        kept = [(c, ok) for c, ok in cal if c >= th]
        sel[str(th)] = {
            "n_warnings": len(kept),
            "precision": (sum(ok for _, ok in kept) / len(kept)) if kept else None,
        }
    out["selective_precision"] = sel

    out["confusion"] = {f"{g}->{p}": v for (g, p), v in sorted(confusion.items())}
    out["per_category_confusion"] = {
        c: {f"{g}->{p}": v for (g, p), v in sorted(d.items())}
        for c, d in sorted(cat_rec.items())}

    out["rewrite"] = {
        "offered": int(m["rewrites"]),
        "offered_rate": m["rewrites"] / m["n"],
        "protected_item_preservation": (
            rw["prot_kept"] / rw["prot_total"] if rw["prot_total"] else None),
        "critical_deletion_rate": (
            rw["critical_del"] / m["rewrites"] if m["rewrites"] else None),
        "language_violation_rate": (
            rw["lang_viol"] / m["rewrites"] if m["rewrites"] else None),
        "rewrites_of_clean_prompts": int(rw["rewrite_of_clean"]),
    }
    out["examples"] = {
        "false_positives": fp_examples[:15],
        "false_negatives": fn_examples[:15],
        "fabricated_spans": fab_examples[:15],
        "critical_deletions": rw_del_examples[:15],
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    out = score(args.data, args.pred)
    s = json.dumps(out, indent=2, ensure_ascii=False)
    if args.json:
        open(args.json, "w").write(s)
    print(s)


if __name__ == "__main__":
    main()
