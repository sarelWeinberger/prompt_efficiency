#!/usr/bin/env python3
"""Parse a pi --mode json event stream into per-turn usage and totals.

pi emits normalized usage per assistant message (turn_end.message.usage):
{input, output, cacheRead, cacheWrite, reasoning?, totalTokens, cost{...}}.
Raw provider usage is not exposed by pi; the normalized object is retained
verbatim as raw_usage. reasoning_token_status is per design §12.
"""
import json
import sys
from pathlib import Path


def parse_events(lines):
    events = []
    for line in lines:
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def parse_usage(events):
    turns = []
    model_seen = set()
    for ev in events:
        if ev.get("type") != "turn_end":
            continue
        msg = ev.get("message") or {}
        u = msg.get("usage") or {}
        model_seen.add(msg.get("model"))
        turns.append({
            "input_uncached": u.get("input", 0),
            "cache_read": u.get("cacheRead", 0),
            "cache_write": u.get("cacheWrite", 0),
            "output": u.get("output", 0),
            "reasoning": u.get("reasoning"),
            "total_tokens": u.get("totalTokens", 0),
            "cost_usd": (u.get("cost") or {}).get("total", 0.0),
            "stop_reason": msg.get("stopReason"),
            "raw_usage": u,
        })
    tot = {
        "turns": len(turns),
        "input_uncached": sum(t["input_uncached"] for t in turns),
        "cache_read": sum(t["cache_read"] for t in turns),
        "cache_write": sum(t["cache_write"] for t in turns),
        "output": sum(t["output"] for t in turns),
        "reported_cost_usd": round(sum(t["cost_usd"] for t in turns), 6),
        "models_seen": sorted(m for m in model_seen if m),
    }
    # Cache-written tokens are logical prompt tokens (billed 1.25x on Anthropic;
    # always 0 on Together, which has no explicit write accounting).
    tot["logical_input"] = (tot["input_uncached"] + tot["cache_read"]
                            + tot["cache_write"])
    # Zero-usage turns (aborted/empty responses) report no usage at all; sum
    # reasoning over the turns that actually report it. Never invent values.
    reporting = [t["reasoning"] for t in turns if t["reasoning"] is not None]
    nonzero_turns = [t for t in turns if t["total_tokens"] > 0]
    tot["turns_without_usage"] = len(turns) - len(nonzero_turns)
    if not turns:
        tot["reasoning"] = None
        tot["reasoning_token_status"] = "parse_error"
    elif not reporting:
        tot["reasoning"] = None
        tot["reasoning_token_status"] = "missing"
    else:
        tot["reasoning"] = sum(reporting)
        tot["reasoning_token_status"] = "explicit"
        if any(t["reasoning"] is None for t in nonzero_turns):
            tot["reasoning_token_status"] = "explicit_partial"
    return {"per_turn": turns, "totals": tot}


def estimate_no_cache_cost(totals, cost):
    """Cost if every logical input token were billed at the uncached input price."""
    inp = totals["logical_input"] * cost["input"] / 1e6
    out = totals["output"] * cost["output"] / 1e6
    return round(inp + out, 6)


def cache_classification(turn, first_turn):
    logical = turn["input_uncached"] + turn["cache_read"]
    if logical == 0:
        return "unknown", None
    ratio = turn["cache_read"] / logical
    if turn["cache_read"] == 0:
        cls = "none"
    elif first_turn:
        cls = "first_turn_hit"
    elif ratio > 0.5:
        cls = "substantial"
    else:
        cls = "partial"
    return cls, round(ratio, 4)


if __name__ == "__main__":
    events = parse_events(Path(sys.argv[1]).read_text().splitlines())
    print(json.dumps(parse_usage(events)["totals"], indent=1))
