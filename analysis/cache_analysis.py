#!/usr/bin/env python3
"""Cache behavior analysis (design §16-17): emits results/summaries/cache_behavior.csv.

Sources:
- Experiment A/B pilot runs: per-turn cache classes recorded per run.
- Experiment C session runs (results/runs_cache.jsonl) when present.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import ROOT, read_jsonl

OUT = ROOT / "results/summaries"


def main():
    rows = []
    for src, fname in (("pilot", "results/runs.jsonl"),
                       ("experiment_c", "results/runs_cache.jsonl")):
        for r in read_jsonl(ROOT / fname):
            if r.get("status") not in ("completed", "timeout"):
                continue
            rows.append({
                "source": src,
                "harness": r.get("harness"),
                "model": r.get("model"),
                "session_condition": r.get("session_condition",
                                           r.get("session_mode", "cold")),
                "task_id": r.get("task_id"),
                "variant": r.get("variant"),
                "turns": r.get("turns"),
                "logical_input_tokens": r.get("logical_input_tokens"),
                "cached_input_tokens": r.get("cached_input_tokens"),
                "cache_read_ratio": r.get("cache_read_ratio"),
                "cache_classes_per_turn": "|".join(r.get("cache_classes_per_turn") or []),
                "first_turn_hit": ("first_turn_hit" in
                                   (r.get("cache_classes_per_turn") or [])),
                "reported_cost_usd": r.get("reported_cost_usd"),
                "estimated_no_cache_cost_usd": r.get("estimated_no_cache_cost_usd"),
                "estimated_cache_savings_usd": r.get("estimated_cache_savings_usd"),
                "delay_s": r.get("delay_s"),
                "prefix_hash": r.get("prefix_hash_after_translation") or r.get("workdir_hash"),
                "workdir_hash": r.get("workdir_hash"),
            })
    OUT.mkdir(parents=True, exist_ok=True)
    if rows:
        with open(OUT / "cache_behavior.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    # aggregate: hit-rate by harness/model
    agg = {}
    for r in rows:
        k = (r["harness"], r["model"])
        a = agg.setdefault(k, {"n": 0, "hits": 0, "ratio_sum": 0.0, "ratio_n": 0,
                               "savings": 0.0, "first_turn_hits": 0})
        a["n"] += 1
        if (r["cache_read_ratio"] or 0) > 0.1:
            a["hits"] += 1
        if r["cache_read_ratio"] is not None:
            a["ratio_sum"] += r["cache_read_ratio"]
            a["ratio_n"] += 1
        a["savings"] += r["estimated_cache_savings_usd"] or 0
        a["first_turn_hits"] += 1 if r["first_turn_hit"] else 0
    print(f"{'harness':12s} {'model':38s} {'runs':>5s} {'anyhit%':>8s} "
          f"{'meanratio':>9s} {'1st-turn':>8s} {'savings$':>9s}")
    for (h, m), a in sorted(agg.items()):
        print(f"{h:12s} {m:38s} {a['n']:5d} {100*a['hits']/a['n']:7.0f}% "
              f"{a['ratio_sum']/max(1,a['ratio_n']):9.3f} {a['first_turn_hits']:8d} "
              f"{a['savings']:9.3f}")
    print(f"wrote {OUT/'cache_behavior.csv'} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
