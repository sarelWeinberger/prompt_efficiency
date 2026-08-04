#!/usr/bin/env python3
"""Generate paper figures directly from analysis CSVs (never from prose).

fig_cost_carriers.pdf : unused-branch / redundant-verification levels vs
                        no-cache cost, tool calls, wall-clock
fig_harness_composition.pdf : baseline tool-call composition per harness
"""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent


def mech_rows():
    with open(ROOT / "results/summaries/tool_cost_by_mechanism.csv") as f:
        return list(csv.DictReader(f))


def fig_cost_carriers():
    rows = mech_rows()
    ub = sorted((r for r in rows if r["mechanism"] == "unused_branches"),
                key=lambda r: int(r["level"]))
    rv = sorted((r for r in rows if r["mechanism"] == "redundant_verification"),
                key=lambda r: int(r["level"]))
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))
    for ax, rows_, title in ((axes[0], ub, "Unused solution branches (level)"),
                             (axes[1], rv, "Redundant verification (level)")):
        lv = [int(r["level"]) for r in rows_]
        cost = [float(r["median_nocache_cost"]) for r in rows_]
        calls = [float(r["median_tool_calls"]) for r in rows_]
        wall = [float(r["median_wall_s"]) for r in rows_]
        ax.plot(lv, cost, "o-", color="#B3261E", label="median no-cache $/run")
        ax.set_xlabel(title + "\n(n per level: " +
                      ", ".join(r["n_runs"] for r in rows_) + ")")
        ax.set_ylabel("median no-cache USD/run", color="#B3261E")
        ax.tick_params(axis="y", labelcolor="#B3261E")
        ax2 = ax.twinx()
        ax2.plot(lv, calls, "s--", color="#1A5FB4", label="median tool calls")
        ax2.plot(lv, [w / 10 for w in wall], "^:", color="#5B21B6",
                 label="median wall s / 10")
        ax2.set_ylabel("tool calls  /  wall s ÷ 10")
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper left")
        ax.set_xticks(lv)
    fig.suptitle("Waste mechanisms have different cost carriers "
                 "(judge level vs deterministic telemetry; success flat across levels)",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_cost_carriers.pdf")
    print("wrote fig_cost_carriers.pdf")


def fig_harness_composition():
    with open(ROOT / "results/summaries/tool_cost_by_tool_type.csv") as f:
        rows = [r for r in csv.DictReader(f) if r["variant"] == "baseline"]
    cats = [("cat_test_execution_share", "tests"), ("cat_file_read_share", "reads"),
            ("cat_file_search_share", "search"), ("cat_navigation_share", "nav"),
            ("cat_code_edit_share", "edits"), ("cat_other_bash_share", "other")]
    labels, stacks = [], []
    for r in rows:
        labels.append(f"{r['harness']}\n{r['model_group']}"
                      f"\n({r['mean_total_calls']} calls/run)")
        stacks.append([float(r.get(c) or 0) for c, _ in cats])
    colors = ["#1A5FB4", "#B3261E", "#E8912D", "#5B21B6", "#1B7F4D", "#9AA0A6"]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    bottom = [0.0] * len(labels)
    for i, (_, name) in enumerate(cats):
        vals = [s[i] for s in stacks]
        ax.bar(labels, vals, bottom=bottom, label=name, color=colors[i])
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_ylabel("share of tool calls (baseline runs)")
    ax.legend(fontsize=7, ncol=6, loc="upper center", bbox_to_anchor=(0.5, 1.18))
    fig.tight_layout()
    fig.savefig(OUT / "fig_harness_composition.pdf")
    print("wrote fig_harness_composition.pdf")


if __name__ == "__main__":
    fig_cost_carriers()
    fig_harness_composition()
