#!/usr/bin/env python3
"""Unified ordered trace for semantic analysis (frozen rubric v1, §4).

Builds one representation from either harness's raw artifacts:
  [{turn, thinking, text, tools: [{name, args, result_head, is_error}]}, ...]
Only what was actually recorded is used; no reconstruction of hidden CoT.
"""
import json
import re

TEST_PAT = re.compile(r"(go test|--test|unittest|pytest|npm test|node --test)")
PASS_PAT = re.compile(r"(?i)(\b\d+ passed\b|\bPASS\b|^ok\b|\bOK\b|tests? passed)")
FAIL_PAT = re.compile(r"(?i)(\bfail(ed|ure)?\b|\berror\b|traceback|FAIL)")
EDIT_TOOLS = {"edit", "write", "Edit", "Write", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"read", "Read"}
BASH_TOOLS = {"bash", "Bash"}


def _result_text(obj, limit=1500):
    """Flatten a tool result payload to text."""
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj[:limit]
    if isinstance(obj, dict):
        parts = []
        for c in obj.get("content") or []:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text") or "")
            elif isinstance(c, str):
                parts.append(c)
        if not parts and obj.get("text"):
            parts.append(str(obj["text"]))
        return "\n".join(parts)[:limit]
    if isinstance(obj, list):
        return "\n".join(_result_text(x, limit) for x in obj)[:limit]
    return str(obj)[:limit]


def from_pi(path):
    turns = []
    results = {}   # toolCallId -> (text, is_error)
    order = []
    for line in open(path):
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = ev.get("type")
        if t == "tool_execution_end":
            results[ev.get("toolCallId")] = (_result_text(ev.get("result")),
                                             bool(ev.get("isError")))
        elif t == "turn_end":
            msg = ev.get("message") or {}
            if msg.get("role") != "assistant":
                continue
            turn = {"thinking": "", "text": "", "tools": [], "ts": msg.get("timestamp")}
            for b in msg.get("content") or []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "thinking":
                    turn["thinking"] += (b.get("thinking") or "")
                elif b.get("type") == "text":
                    turn["text"] += (b.get("text") or "")
                elif b.get("type") in ("toolCall", "toolUse", "tool_call", "tool_use"):
                    turn["tools"].append({
                        "name": b.get("name") or b.get("toolName") or "?",
                        "args": b.get("arguments") or b.get("input") or {},
                        "id": b.get("id") or b.get("toolCallId"),
                    })
            turns.append(turn)
            order.append(turn)
    for turn in order:
        for tc in turn["tools"]:
            res = results.get(tc.pop("id"), ("", False))
            tc["result_head"], tc["is_error"] = res
    return turns


def from_cc(path):
    turns = []
    results = {}
    pending = []
    for line in open(path):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = rec.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        if msg.get("role") == "assistant":
            turn = {"thinking": "", "text": "", "tools": [], "ts": rec.get("timestamp")}
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "thinking":
                    turn["thinking"] += (b.get("thinking") or "")
                elif b.get("type") == "text":
                    turn["text"] += (b.get("text") or "")
                elif b.get("type") == "tool_use":
                    tc = {"name": b.get("name", "?"), "args": b.get("input") or {},
                          "id": b.get("id")}
                    turn["tools"].append(tc)
                    pending.append(tc)
            turns.append(turn)
        elif msg.get("role") == "user":
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    results[b.get("tool_use_id")] = (
                        _result_text(b.get("content")),
                        bool(b.get("is_error")))
    for tc in pending:
        res = results.get(tc.pop("id"), ("", False))
        tc["result_head"], tc["is_error"] = res
    return turns


def load_trace(run_dir):
    """Return (turns, harness) or (None, None)."""
    run_dir = str(run_dir)
    import os
    if os.path.exists(run_dir + "/pi_events.jsonl"):
        return from_pi(run_dir + "/pi_events.jsonl"), "pi"
    if os.path.exists(run_dir + "/claude_code_events.jsonl"):
        return from_cc(run_dir + "/claude_code_events.jsonl"), "claude-code"
    return None, None


def is_test_call(tc):
    if tc["name"] in BASH_TOOLS:
        return bool(TEST_PAT.search(str(tc["args"].get("command", ""))))
    return False


def test_passed(tc):
    txt = tc.get("result_head") or ""
    return (not tc.get("is_error")) and bool(PASS_PAT.search(txt)) \
        and not FAIL_PAT.search(txt)
