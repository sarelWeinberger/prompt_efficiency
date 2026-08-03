#!/usr/bin/env python3
"""Method B: deterministic behavioral reconstruction (frozen rubric v1, §4).

Walks every valid run in the ledger, parses its recorded trace, and computes
mechanical semantic proxies. No model judgment anywhere in this file.

Emits results/summaries/semantic_proxies.csv (one row per run).
"""
import csv
import re
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import ROOT, load_config, load_task, read_jsonl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from semantic_trace import (EDIT_TOOLS, READ_TOOLS, is_test_call, load_trace,
                            test_passed)

CFG = load_config()
RAW = ROOT / CFG["raw_dir"]

# Frozen lexicons (rubric §4)
PLAN_PAT = re.compile(r"(?i)\b(plan|step \d|first,|then,|finally)\b")
ALT_PAT = re.compile(r"(?i)\b(option|approach|alternative(?:ly)?|instead|"
                     r"we could|one way|another way)\b")


def shingles(text, n=8):
    words = re.findall(r"\w+", text.lower())
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


_task_cache = {}


def task_spec_text(task_id):
    if task_id not in _task_cache:
        t = load_task(task_id)
        parts = [str(t.get("objective", ""))]
        for c in t.get("acceptance_criteria") or []:
            parts.append(str(c))
        _task_cache[task_id] = " ".join(parts)
    return _task_cache[task_id]


def proxies_for(run_dir, task_id):
    turns, harness = load_trace(run_dir)
    if turns is None:
        return None
    think_all, text_all = [], []
    flat = []  # (kind, payload, turn_idx)
    for i, t in enumerate(turns):
        if t["thinking"]:
            think_all.append(t["thinking"])
        if t["text"]:
            text_all.append(t["text"])
        for tc in t["tools"]:
            flat.append((tc, i))

    thinking = "\n".join(think_all)
    visible = "\n".join(text_all)
    both = thinking + "\n" + visible

    # --- edit / read / test structure
    first_edit_idx = None
    first_green_idx = None
    reads, edits = [], []
    test_runs = 0
    for k, (tc, ti) in enumerate(flat):
        name = tc["name"]
        args = tc["args"] if isinstance(tc["args"], dict) else {}
        if name in READ_TOOLS:
            reads.append(args.get("path") or args.get("file_path") or "")
        if name in EDIT_TOOLS:
            edits.append(args.get("path") or args.get("file_path") or "")
            if first_edit_idx is None:
                first_edit_idx = k
        if is_test_call(tc):
            test_runs += 1
            if first_green_idx is None and test_passed(tc):
                first_green_idx = k

    tools_before_edit = first_edit_idx if first_edit_idx is not None else len(flat)
    tools_after_green = (len(flat) - 1 - first_green_idx
                         if first_green_idx is not None else None)
    tests_after_green = (sum(1 for tc, _ in flat[first_green_idx + 1:]
                             if is_test_call(tc))
                         if first_green_idx is not None else None)

    # thinking chars split around first edit / first green (by turn boundary)
    def turn_of(idx):
        return flat[idx][1] if idx is not None and idx < len(flat) else None

    edit_turn = turn_of(first_edit_idx)
    green_turn = turn_of(first_green_idx)
    tc_before_edit = sum(len(t["thinking"]) for i, t in enumerate(turns)
                         if edit_turn is None or i < edit_turn)
    tc_after_green = (sum(len(t["thinking"]) + len(t["text"])
                          for i, t in enumerate(turns) if i > green_turn)
                      if green_turn is not None else None)

    # --- lexical proxies (frozen)
    spec = task_spec_text(task_id)
    spec_sh = shingles(spec)
    run_sh = shingles(both)
    restate = (len(spec_sh & run_sh) / len(spec_sh)) if spec_sh else 0.0

    comp_ratio = None
    if len(thinking) >= 500:
        comp_ratio = 1 - len(zlib.compress(thinking.encode())) / len(thinking.encode())

    per_k = max(1, len(thinking)) / 1000.0
    return {
        "turns_parsed": len(turns),
        "thinking_chars": len(thinking),
        "visible_chars": len(visible),
        "tool_calls_parsed": len(flat),
        "tool_calls_before_first_edit": tools_before_edit,
        "thinking_chars_before_first_edit": tc_before_edit,
        "first_green_test_found": first_green_idx is not None,
        "tool_calls_after_first_green": tools_after_green,
        "test_runs_total": test_runs,
        "test_runs_after_first_green": tests_after_green,
        "postgreen_chars": tc_after_green,
        "distinct_files_read": len(set(reads)),
        "files_read_not_edited": len(set(reads) - set(edits)),
        "task_restatement_index": round(restate, 4),
        "redundancy_compression_ratio": round(comp_ratio, 4)
                                        if comp_ratio is not None else None,
        "plan_markers_per_1k": round(len(PLAN_PAT.findall(thinking)) / per_k, 3),
        "alt_markers_per_1k": round(len(ALT_PAT.findall(thinking)) / per_k, 3),
        "alt_markers_total": len(ALT_PAT.findall(thinking)),
        "plan_markers_total": len(PLAN_PAT.findall(thinking)),
    }


def main():
    out_path = ROOT / "results/summaries/semantic_proxies.csv"
    rows = []
    skipped = 0
    for r in read_jsonl(ROOT / "results/runs.jsonl"):
        if r.get("run_validity") != "valid":
            continue
        if r.get("status") not in ("completed", "timeout"):
            continue
        d = RAW / r["run_id"]
        if not d.exists():
            skipped += 1
            continue
        p = proxies_for(d, r["task_id"])
        if p is None:
            skipped += 1
            continue
        rows.append({
            "run_id": r["run_id"], "experiment": r.get("experiment"),
            "harness": r["harness"], "model": r["model"],
            "task_id": r["task_id"], "variant": r["variant"], "rep": r["rep"],
            "reasoning_tokens": r.get("reasoning_tokens"),
            "visible_output_tokens": r.get("visible_output_tokens"),
            "turns": r.get("turns"),
            "tool_total_tool_calls": r.get("tool_total_tool_calls"),
            "tool_duplicate_reads": r.get("tool_duplicate_reads"),
            "tool_repeated_searches": r.get("tool_repeated_searches"),
            "tool_repeated_tests_no_change": r.get("tool_repeated_tests_no_change"),
            "edits_reverted": r.get("edits_reverted"),
            "scope_compliant_success": r.get("scope_compliant_success"),
            "reported_cost_usd": r.get("reported_cost_usd"),
            "estimated_no_cache_cost_usd": r.get("estimated_no_cache_cost_usd"),
            **p,
        })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows ({skipped} runs skipped: no retained trace) "
          f"-> {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
