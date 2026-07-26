import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from parse_pi_usage import cache_classification, parse_events, parse_usage

SAMPLE = [
    json.dumps({"type": "turn_end", "message": {
        "role": "assistant", "model": "zai-org/GLM-5.2", "stopReason": "toolUse",
        "usage": {"input": 1355, "output": 42, "cacheRead": 0, "cacheWrite": 0,
                  "reasoning": 30, "totalTokens": 1397,
                  "cost": {"total": 0.002082}}}}),
    json.dumps({"type": "turn_end", "message": {
        "role": "assistant", "model": "zai-org/GLM-5.2", "stopReason": "stop",
        "usage": {"input": 35, "output": 77, "cacheRead": 1344, "cacheWrite": 0,
                  "reasoning": 0, "totalTokens": 1456,
                  "cost": {"total": 0.000737}}}}),
    "not json garbage",
]


class TestUsageParser(unittest.TestCase):
    def test_totals(self):
        u = parse_usage(parse_events(SAMPLE))
        t = u["totals"]
        self.assertEqual(t["turns"], 2)
        self.assertEqual(t["input_uncached"], 1390)
        self.assertEqual(t["cache_read"], 1344)
        self.assertEqual(t["logical_input"], 2734)
        self.assertEqual(t["reasoning"], 30)
        self.assertEqual(t["reasoning_token_status"], "explicit")
        self.assertAlmostEqual(t["reported_cost_usd"], 0.002819)

    def test_missing_reasoning_marked(self):
        ev = parse_events([json.dumps({"type": "turn_end", "message": {
            "role": "assistant", "usage": {"input": 10, "output": 5,
                                           "cacheRead": 0, "cacheWrite": 0,
                                           "cost": {"total": 0.0}}}})])
        t = parse_usage(ev)["totals"]
        self.assertIsNone(t["reasoning"])
        self.assertEqual(t["reasoning_token_status"], "missing")

    def test_empty_stream_is_parse_error(self):
        t = parse_usage([])["totals"]
        self.assertEqual(t["reasoning_token_status"], "parse_error")

    def test_cache_classification(self):
        full = {"input_uncached": 35, "cache_read": 1344}
        none = {"input_uncached": 1355, "cache_read": 0}
        part = {"input_uncached": 1257, "cache_read": 192}
        self.assertEqual(cache_classification(full, False)[0], "substantial")
        self.assertEqual(cache_classification(none, False)[0], "none")
        self.assertEqual(cache_classification(part, False)[0], "partial")
        self.assertEqual(cache_classification(full, True)[0], "first_turn_hit")
        self.assertEqual(cache_classification({"input_uncached": 0, "cache_read": 0},
                                              False)[0], "unknown")


if __name__ == "__main__":
    unittest.main()
