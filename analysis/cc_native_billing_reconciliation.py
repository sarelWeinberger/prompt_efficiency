#!/usr/bin/env python3
"""Reconcile native Claude Code billed cost against visible usage categories.

Tests whether any separately billed provider-side cost (e.g. a safety
classifier surcharge) is detectable in the 54 anthropic_cc runs: recomputes
each run's cost from uncached input, cache reads, cache writes, and output
at the standard claude-sonnet-5 price table, and solves the implied
cache-write rate from the residual. A per-request classifier surcharge would
scale with request count / turns / classified input volume; a residual that
tracks cache-write token volume at the documented 5-minute (1.25x = $3.75/M)
and 1-hour (2x = $6.00/M) write premiums indicates pricing structure, not a
hidden charge.

Emits results/summaries/cc_native_billing_reconciliation.csv.
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import ROOT, read_jsonl

IN, OUT, CR = 3.00, 15.00, 0.30          # standard $/M (snapshot 2026-08)
IN_INTRO, OUT_INTRO = 2.00, 10.00        # introductory $/M (through 2026-08-31)
CW_5M, CW_1H = 3.75, 6.00                # documented write premiums (1.25x / 2x)


def main():
    rows = []
    for r in read_jsonl(ROOT / "results/runs.jsonl"):
        if r.get("experiment") != "anthropic_cc" or r.get("run_validity") != "valid":
            continue
        unc = r["uncached_input_tokens"]
        cr = r["cached_input_tokens"]
        out = r["visible_output_tokens"]
        cw = r["logical_input_tokens"] - unc - cr
        rep = r["reported_cost_usd"]
        base = (unc * IN + cr * CR + out * OUT) / 1e6
        math_5m = base + cw * CW_5M / 1e6
        implied_cw = (rep - base) / max(cw, 1) * 1e6 if cw else None
        intro_math = (unc * IN_INTRO + cr * CR * (IN_INTRO / IN)
                      + cw * CW_5M * (IN_INTRO / IN) + out * OUT_INTRO) / 1e6
        rows.append({
            "run_id": r["run_id"], "turns": r.get("turns"),
            "uncached_in": unc, "cache_read": cr, "cache_write": cw,
            "output": out, "reported_usd": rep,
            "token_math_5m_usd": round(math_5m, 6),
            "rel_diff_5m": round((rep - math_5m) / max(rep, 1e-9), 4),
            "implied_cache_write_rate_per_M": round(implied_cw, 2)
                                              if implied_cw else None,
            "rel_diff_vs_intro_pricing": round((rep - intro_math)
                                               / max(rep, 1e-9), 4),
        })
    outp = ROOT / "results/summaries/cc_native_billing_reconciliation.csv"
    with open(outp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    d5 = sorted(abs(x["rel_diff_5m"]) for x in rows)
    within1 = sum(1 for x in d5 if x <= 0.01)
    icw = sorted(x["implied_cache_write_rate_per_M"] for x in rows
                 if x["implied_cache_write_rate_per_M"])
    dintro = sorted(x["rel_diff_vs_intro_pricing"] for x in rows)
    print(f"n={len(rows)} native CC runs")
    print(f"|reported - token_math(5m writes)|/reported: median={d5[len(d5)//2]:.4f}, "
          f"within 1%: {within1}/{len(rows)}, max={d5[-1]:.4f}")
    print(f"implied cache-write $/M: median={st.median(icw):.2f}, "
          f"q90={icw[int(.9*len(icw))]:.2f}, max={icw[-1]:.2f} "
          f"(documented rates: {CW_5M} 5-minute, {CW_1H} 1-hour)")
    print(f"uniform artifact vs intro pricing: median rel diff="
          f"{dintro[len(dintro)//2]:.4f} (= standard/intro price ratio)")


if __name__ == "__main__":
    main()
