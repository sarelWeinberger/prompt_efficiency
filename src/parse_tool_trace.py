#!/usr/bin/env python3
"""Extract tool-behavior waste metrics (design §15) from harness event streams.

Supports two formats:
- pi --mode json events (assistant messages carry toolCall content blocks)
- Claude Code project transcripts (~/.claude/projects/**.jsonl; assistant
  messages carry content blocks of type tool_use)
"""
import json
import re
from pathlib import Path

TEST_PAT = re.compile(r"(go test|--test|unittest|pytest|npm test)")
SEARCH_PAT = re.compile(r"\b(rg|grep|find|ag)\b")
EDIT_TOOLS = {"edit", "write", "Edit", "Write", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"read", "Read"}
BASH_TOOLS = {"bash", "Bash"}


def _pi_tool_calls(events):
    calls = []
    t0 = None
    for ev in events:
        if ev.get("type") == "message_start" and t0 is None:
            t0 = (ev.get("message") or {}).get("timestamp")
        if ev.get("type") != "message_end":
            continue
        msg = ev.get("message") or {}
        if msg.get("role") != "assistant":
            continue
        for block in msg.get("content") or []:
            if block.get("type") in ("toolCall", "toolUse", "tool_call", "tool_use"):
                calls.append({
                    "tool": block.get("name") or block.get("toolName") or "?",
                    "args": block.get("arguments") or block.get("input") or {},
                    "ts": msg.get("timestamp"),
                })
    return calls, t0


def _cc_tool_calls(transcript_lines):
    calls = []
    t0 = None
    for line in transcript_lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = rec.get("message") or {}
        ts = rec.get("timestamp")
        if t0 is None and ts:
            t0 = ts
        if msg.get("role") != "assistant":
            continue
        for block in msg.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                calls.append({"tool": block.get("name", "?"),
                              "args": block.get("input") or {}, "ts": ts})
    return calls, t0


def analyze_tool_calls(calls, allowed_paths=None):
    reads, searches, tests, edits = [], [], [], []
    read_counts = {}
    by_tool = {}
    first_tool_ts = calls[0]["ts"] if calls else None
    first_edit_ts = None
    test_cmds_since_edit = []
    repeated_tests = 0

    for c in calls:
        tool = c["tool"]
        by_tool[tool] = by_tool.get(tool, 0) + 1
        args = c["args"] if isinstance(c["args"], dict) else {}
        if tool in READ_TOOLS:
            path = args.get("path") or args.get("file_path") or ""
            reads.append(path)
            key = (path, args.get("offset"))
            read_counts[key] = read_counts.get(key, 0) + 1
        elif tool in BASH_TOOLS:
            cmd = args.get("command", "")
            if SEARCH_PAT.search(cmd):
                searches.append(cmd.strip())
            if TEST_PAT.search(cmd):
                tests.append(cmd.strip())
                if cmd.strip() in test_cmds_since_edit:
                    repeated_tests += 1
                test_cmds_since_edit.append(cmd.strip())
        if tool in EDIT_TOOLS:
            path = args.get("path") or args.get("file_path") or ""
            edits.append(path)
            test_cmds_since_edit = []
            if first_edit_ts is None:
                first_edit_ts = c["ts"]

    dup_reads = sum(n - 1 for n in read_counts.values() if n > 1)
    search_counts = {}
    for s in searches:
        search_counts[s] = search_counts.get(s, 0) + 1
    repeated_searches = sum(n - 1 for n in search_counts.values() if n > 1)

    files_read_before_edit = 0
    for c in calls:
        if c["tool"] in EDIT_TOOLS:
            break
        if c["tool"] in READ_TOOLS:
            files_read_before_edit += 1

    return {
        "total_tool_calls": len(calls),
        "calls_by_tool": by_tool,
        "read_calls": sum(by_tool.get(t, 0) for t in READ_TOOLS),
        "bash_calls": sum(by_tool.get(t, 0) for t in BASH_TOOLS),
        "edit_calls": sum(by_tool.get(t, 0) for t in EDIT_TOOLS if t.lower() == "edit"),
        "write_calls": sum(by_tool.get(t, 0) for t in EDIT_TOOLS if t.lower() == "write"),
        "files_inspected": len(set(reads)),
        "duplicate_reads": dup_reads,
        "search_commands": len(searches),
        "repeated_searches": repeated_searches,
        "test_commands": len(tests),
        "repeated_tests_no_change": repeated_tests,
        "files_read_before_first_edit": files_read_before_edit,
        "first_tool_ts": first_tool_ts,
        "first_edit_ts": first_edit_ts,
        "edited_paths": sorted(set(edits)),
    }


def from_pi_events(events, allowed_paths=None):
    calls, t0 = _pi_tool_calls(events)
    out = analyze_tool_calls(calls, allowed_paths)
    out["stream_t0"] = t0
    return out


def from_cc_transcript(lines, allowed_paths=None):
    calls, t0 = _cc_tool_calls(lines)
    out = analyze_tool_calls(calls, allowed_paths)
    out["stream_t0"] = t0
    return out


if __name__ == "__main__":
    import sys
    lines = Path(sys.argv[1]).read_text().splitlines()
    events = [json.loads(l) for l in lines if l.strip().startswith("{")]
    print(json.dumps(from_pi_events(events), indent=1))
