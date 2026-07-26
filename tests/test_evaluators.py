import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from evaluate_run import evaluate
from reset_workspace import reset_slot

SLOT = Path("/tmp/pi-prompt-benchmark/slot-evaltest")

# Reference fixes for the pilot tasks: applying them must flip both visible
# and hidden tests to pass. This guards against unsatisfiable tasks.
FIXES = {
    "py-low-01": {"shop/discount.py": '''\
def apply_discount(price, pct):
    """Return the price after applying a pct-percent discount.

    pct must be between 0 and 100 inclusive.
    """
    if pct < 0 or pct > 100:
        raise ValueError("pct out of range")
    return price * (100 - pct) / 100
'''},
    "js-med-03": {"src/cache.js": '''\
class SimpleCache {
  constructor(ttlSeconds, clock = Date.now) {
    this.ttlSeconds = ttlSeconds;
    this.clock = clock;
    this.store = new Map();
  }

  set(key, value) {
    this.store.set(key, { value, at: this.clock() });
  }

  get(key) {
    const entry = this.store.get(key);
    if (!entry) return undefined;
    if (this.clock() - entry.at > this.ttlSeconds * 1000) {
      this.store.delete(key);
      return undefined;
    }
    return entry.value;
  }
}

module.exports = { SimpleCache };
'''},
    "go-low-01": {"stats/stats.go": '''\
package stats

// Average returns the arithmetic mean of xs, or 0 for an empty slice.
func Average(xs []int) float64 {
	if len(xs) == 0 {
		return 0
	}
	sum := 0
	for _, x := range xs {
		sum += x
	}
	return float64(sum) / float64(len(xs))
}
'''},
}


class TestEvaluators(unittest.TestCase):
    def test_pristine_fixture_fails_both_test_layers(self):
        for tid in FIXES:
            reset_slot(SLOT, tid)
            r = evaluate(SLOT, tid)
            self.assertFalse(r["task_success"], tid)

    def test_reference_fix_passes_both_layers_in_scope(self):
        for tid, patch in FIXES.items():
            reset_slot(SLOT, tid)
            for rel, content in patch.items():
                (SLOT / rel).write_text(content)
            r = evaluate(SLOT, tid)
            self.assertTrue(r["visible_test_pass"], f"{tid}: {r['visible_test_tail']}")
            self.assertTrue(r["hidden_test_pass"], f"{tid}: {r['hidden_test_tail']}")
            self.assertTrue(r["scope_compliant_success"], f"{tid}: {r['out_of_scope_changes']}")
            self.assertEqual(r["out_of_scope_changes"], [])

    def test_out_of_scope_change_detected(self):
        reset_slot(SLOT, "py-low-01")
        for rel, content in FIXES["py-low-01"].items():
            (SLOT / rel).write_text(content)
        (SLOT / "README_EXTRA.md").write_text("unrequested cleanup")
        r = evaluate(SLOT, "py-low-01")
        self.assertTrue(r["task_success"])
        self.assertFalse(r["scope_compliant_success"])
        self.assertIn("README_EXTRA.md", r["out_of_scope_changes"])

    def test_hidden_tests_removed_after_eval(self):
        reset_slot(SLOT, "py-low-01")
        evaluate(SLOT, "py-low-01")
        self.assertFalse((SLOT / "tests_hidden").exists())


if __name__ == "__main__":
    unittest.main()
