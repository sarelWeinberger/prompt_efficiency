import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import all_task_ids, load_task
from generate_prompts import generate_task, validate_task


class TestPromptGenerator(unittest.TestCase):
    def test_all_tasks_generate_and_validate(self):
        for tid in all_task_ids():
            prompts = generate_task(tid)
            self.assertGreaterEqual(len(prompts), 16)
            self.assertEqual(validate_task(tid, prompts), [])

    def test_primary_variants_preserve_criteria(self):
        prompts = generate_task("py-low-01")
        task = load_task("py-low-01")
        for name, p in prompts.items():
            if p["family"] != "primary" or name == "goal_only":
                continue
            self.assertIn(task["criteria"], p["text"], name)
            self.assertIn(task["test_cmd"], p["text"], name)

    def test_baseline_is_shortest_primary_with_criteria(self):
        prompts = generate_task("js-med-03")
        base = prompts["baseline"]["char_count"]
        self.assertLess(base, prompts["verbose_repetition"]["char_count"])
        self.assertLess(base, prompts["deep_thinking"]["char_count"])

    def test_hashes_are_stable(self):
        a = generate_task("go-low-01")["baseline"]["sha256"]
        b = generate_task("go-low-01")["baseline"]["sha256"]
        self.assertEqual(a, b)

    def test_stress_variants_flagged(self):
        prompts = generate_task("py-low-01")
        self.assertEqual(prompts["ambiguous_scope"]["family"], "stress")
        self.assertNotIn(load_task("py-low-01")["criteria"],
                         prompts["ambiguous_scope"]["text"])


if __name__ == "__main__":
    unittest.main()
