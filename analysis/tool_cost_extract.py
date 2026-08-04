#!/usr/bin/env python3
"""Tool-cost extraction (frozen rubric benchmark/tool_cost_rubric.md).

Deterministic only. Parses raw traces independently of semantic_trace.py so
prior semantic results cannot be affected. Emits
results/summaries/tool_cost_run_level.csv.
"""
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import ROOT, load_config, model_cost, read_jsonl

CFG = load_config()
RAW = ROOT / CFG["raw_dir"]

TEST_PAT = re.compile(r"(go test|--test|unittest|pytest|npm test|node --test)")


def test_green(text, is_error):
    """Framework-aware pass detection (TAP / unittest / pytest / go test)."""
    if is_error or not text:
        return False
    if re.search(r"# fail 0", text):                      # TAP summary
        return True
    if re.search(r"(?m)^OK\b", text) and "FAILED" not in text:   # unittest
        return True
    m = re.search(r"(\d+) passed", text)
    if m and not re.search(r"[1-9]\d* (failed|error)", text):    # pytest
        return True
    if re.search(r"(?m)^ok\s", text) and not re.search(r"(?m)^(--- )?FAIL", text):
        return True                                        # go test
    return False
WORKDIR_PAT = re.compile(r"/tmp/pi-prompt-benchmark/slot[^/\s]*/?")
CD_PREFIX = re.compile(r"^cd\s+\S+\s*&&\s*")

CATEGORY_RULES = [  # first match wins (rubric §2)
    ("test_execution", TEST_PAT),
    ("lint_static", re.compile(r"\b(eslint|flake8|pylint|go vet|golangci)\b")),
    ("build_compile", re.compile(r"\b(go build|go mod|make\b|npm (ci|install)|pip install|tsc\b)")),
    ("git_inspect", re.compile(r"\bgit (status|log|diff|show|branch)\b")),
    ("file_search", re.compile(r"\b(rg|grep|ag)\b|find\s+\S+.*-name")),
    ("navigation", re.compile(r"^(ls|pwd|tree)\b|find\s+\S+.*-type d")),
    ("file_read", re.compile(r"^(cat|head|tail|sed -n|wc)\b")),
    ("env_inspect", re.compile(r"(--version|\bwhich\b|\buname\b|^echo )")),
    ("external_network", re.compile(r"\b(curl|wget)\b")),
]
EDIT_TOOLS = {"edit", "write", "Edit", "Write", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"read", "Read"}
BASH_TOOLS = {"bash", "Bash"}


def norm(s):
    s = WORKDIR_PAT.sub("", s or "")
    s = CD_PREFIX.sub("", s.strip())
    return re.sub(r"\s+", " ", s)


def flatten(obj):
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        parts = [c.get("text", "") if isinstance(c, dict) else str(c)
                 for c in obj.get("content") or []]
        if not parts and obj.get("text"):
            parts = [str(obj["text"])]
        return "\n".join(parts)
    if isinstance(obj, list):
        return "\n".join(flatten(x) for x in obj)
    return str(obj)


def categorize(call):
    name = call["name"]
    if name in EDIT_TOOLS:
        return "code_edit"
    if name in READ_TOOLS:
        return "file_read"
    if name in BASH_TOOLS:
        cmd = str((call["args"] or {}).get("command", ""))
        for cat, pat in CATEGORY_RULES:
            if pat.search(cmd):
                return cat
        return "other_bash"
    return "other_tool"


def parse_pi(path):
    """Return (calls, turns_usage). calls: ordered dicts with name/args/
    result_chars/is_error/turn. turns_usage: per-turn usage + ts."""
    results = {}
    calls, turns = [], []
    for line in open(path):
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = ev.get("type")
        if t == "tool_execution_end":
            txt = flatten(ev.get("result"))
            results[ev.get("toolCallId")] = (len(txt),
                                             txt[:300] + "\n" + txt[-300:],
                                             bool(ev.get("isError")))
        elif t == "turn_end":
            msg = ev.get("message") or {}
            if msg.get("role") != "assistant":
                continue
            u = msg.get("usage") or {}
            ti = len(turns)
            turns.append({"ts": msg.get("timestamp"),
                          "input": u.get("input", 0), "output": u.get("output", 0),
                          "cache_read": u.get("cacheRead", 0),
                          "cache_write": u.get("cacheWrite", 0)})
            for b in msg.get("content") or []:
                if isinstance(b, dict) and b.get("type") in ("toolCall", "toolUse"):
                    rid = b.get("id") or b.get("toolCallId")
                    rc, head, err = results.get(rid, (0, "", False))
                    calls.append({"name": b.get("name") or "?",
                                  "args": b.get("arguments") or {}, "turn": ti,
                                  "result_chars": rc, "result_head": head,
                                  "is_error": err, "dur_s": None})
    return calls, turns


def parse_cc(path):
    calls, turns = [], []
    pending = {}
    for line in open(path):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = rec.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        ts = rec.get("timestamp")
        if msg.get("role") == "assistant":
            u = msg.get("usage") or {}
            ti = len(turns)
            turns.append({"ts": ts, "input": u.get("input_tokens", 0),
                          "output": u.get("output_tokens", 0),
                          "cache_read": u.get("cache_read_input_tokens", 0) or 0,
                          "cache_write": u.get("cache_creation_input_tokens", 0) or 0})
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    c = {"name": b.get("name", "?"), "args": b.get("input") or {},
                         "turn": ti, "result_chars": 0, "result_head": "",
                         "is_error": False, "dur_s": None, "_ts": ts}
                    calls.append(c)
                    pending[b.get("id")] = c
        elif msg.get("role") == "user":
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    c = pending.get(b.get("tool_use_id"))
                    if c is None:
                        continue
                    txt = flatten(b.get("content"))
                    c["result_chars"] = len(txt)
                    c["result_head"] = txt[:300] + "\n" + txt[-300:]
                    c["is_error"] = bool(b.get("is_error"))
                    try:
                        t0 = datetime.fromisoformat(c.pop("_ts").replace("Z", "+00:00"))
                        t1 = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        c["dur_s"] = round((t1 - t0).total_seconds(), 3)
                    except (KeyError, ValueError, AttributeError, TypeError):
                        c.pop("_ts", None)
    for c in calls:
        c.pop("_ts", None)
    return calls, turns


def analyze_run(calls, turns, cost):
    """All rubric §2-§4 deterministic metrics for one run."""
    n = len(calls)
    cat_counts = {}
    seen_cmd_after_edit = {}   # norm cmd -> last exec index
    last_edit_of_path = {}     # path -> call idx
    last_edit_idx = None
    green_cmds = set()
    first_green_idx = None
    dup_cmd = rep_read = post_green_rep = 0
    edited_paths, read_paths = set(), set()
    failed = 0
    err_recovery = 0
    prev_failed = False
    for i, c in enumerate(calls):
        cat = categorize(c)
        c["cat"] = cat
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        if c["is_error"]:
            failed += 1
        if prev_failed:
            err_recovery += 1
        prev_failed = c["is_error"]
        args = c["args"] if isinstance(c["args"], dict) else {}
        path = norm(str(args.get("path") or args.get("file_path") or ""))
        if cat == "code_edit":
            last_edit_idx = i
            if path:
                edited_paths.add(path)
                last_edit_of_path[path] = i
            seen_cmd_after_edit = {}   # edits invalidate duplicate-command state
        elif c["name"] in READ_TOOLS and path:
            read_paths.add(path)
            prev = [j for j, cc in enumerate(calls[:i])
                    if cc["name"] in READ_TOOLS
                    and norm(str((cc["args"] or {}).get("path")
                                 or (cc["args"] or {}).get("file_path") or "")) == path]
            if prev and last_edit_of_path.get(path, -1) < prev[-1]:
                rep_read += 1
        elif c["name"] in BASH_TOOLS:
            cmd = norm(str(args.get("command", "")))
            if cmd in seen_cmd_after_edit:
                dup_cmd += 1
            seen_cmd_after_edit[cmd] = i
            if cat == "test_execution":
                green = test_green(c.get("result_head") or "", c["is_error"])
                if cmd in green_cmds:
                    post_green_rep += 1
                if green:
                    green_cmds.add(cmd)
                    if first_green_idx is None:
                        first_green_idx = i
    # completion proxy: after last edit AND after first green
    post_success_calls = 0
    if first_green_idx is not None and last_edit_idx is not None:
        cp = max(first_green_idx, last_edit_idx)
        post_success_calls = max(0, n - 1 - cp)
    # abandoned exploration proxy
    final_dirs = {p.rsplit("/", 1)[0] for p in edited_paths if "/" in p}
    abandoned = 0
    for c in calls:
        if c["cat"] in ("file_read", "file_search"):
            args = c["args"] if isinstance(c["args"], dict) else {}
            p = norm(str(args.get("path") or args.get("file_path") or ""))
            if p and p not in edited_paths \
                    and (p.rsplit("/", 1)[0] if "/" in p else "") not in final_dirs:
                abandoned += 1
    # induced model cost (rubric §4C)
    tot_result_chars = sum(c["result_chars"] for c in calls)
    est_tokens_by_call = [(c, c["result_chars"] / 4.0) for c in calls]
    nturns = len(turns)
    low = up = 0.0
    for c, tk in est_tokens_by_call:
        t_after = max(0, nturns - 1 - c["turn"])
        low += tk * (cost["input"] + max(0, t_after - 1) * cost["cache_read"]) / 1e6
        up += tk * max(1, t_after) * cost["input"] / 1e6
    # direct measurement: per-turn logical input growth
    growth = 0
    prev_logical = None
    for t in turns:
        logical = t["input"] + t["cache_read"] + t["cache_write"]
        if prev_logical is not None:
            growth += max(0, logical - prev_logical)
        prev_logical = logical
    durs = [c["dur_s"] for c in calls if c.get("dur_s") is not None]
    return {
        "tool_calls": n,
        "failed_calls": failed,
        "error_recovery_calls": err_recovery,
        "duplicate_commands": dup_cmd,
        "repeated_reads": rep_read,
        "post_green_repeat_tests": post_green_rep,
        "post_success_calls": post_success_calls,
        "abandoned_exploration_calls": abandoned,
        "distinct_files_read": len(read_paths),
        "tool_result_chars": tot_result_chars,
        "est_tool_result_tokens": round(tot_result_chars / 4),
        "induced_cost_lower_usd": round(low, 6),
        "induced_cost_upper_usd": round(up, 6),
        "context_growth_tokens": growth,
        "tool_wall_s": round(sum(durs), 2) if durs else None,
        "n_calls_with_duration": len(durs),
        **{f"cat_{k}": v for k, v in sorted(cat_counts.items())},
    }


def main():
    rows = []
    skipped = 0
    for r in read_jsonl(ROOT / "results/runs.jsonl"):
        if "run_id" not in r or r.get("run_validity") != "valid" \
                or r.get("status") not in ("completed", "timeout"):
            continue
        d = RAW / r["run_id"]
        pi_p, cc_p = d / "pi_events.jsonl", d / "claude_code_events.jsonl"
        if pi_p.exists():
            calls, turns = parse_pi(pi_p)
        elif cc_p.exists():
            calls, turns = parse_cc(cc_p)
        else:
            skipped += 1
            continue
        m = analyze_run(calls, turns, model_cost(r["model"]))
        rows.append({
            "run_id": r["run_id"], "experiment": r.get("experiment"),
            "harness": r["harness"], "model": r["model"],
            "task_id": r["task_id"], "variant": r["variant"], "rep": r["rep"],
            "wall_s": r.get("wall_s"), "turns": r.get("turns"),
            "reasoning_tokens": r.get("reasoning_tokens"),
            "visible_output_tokens": r.get("visible_output_tokens"),
            "logical_input_tokens": r.get("logical_input_tokens"),
            "reported_cost_usd": r.get("reported_cost_usd"),
            "estimated_no_cache_cost_usd": r.get("estimated_no_cache_cost_usd"),
            "scope_compliant_success": r.get("scope_compliant_success"),
            **m,
        })
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    out = ROOT / "results/summaries/tool_cost_run_level.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, restval=0)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows ({skipped} skipped) -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
