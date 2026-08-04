"""Regression: paper prompt examples must match the frozen experimental
prompts. Regenerates the appendix artifacts and fails on any divergence
(the generator itself fails on hash/preservation violations)."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestPromptExamples(unittest.TestCase):
    def test_appendix_matches_frozen_prompts(self):
        before = {p.name: p.read_text() for p in
                  [ROOT / "paper/prompt_appendix.tex",
                   ROOT / "paper/prompt_table.tex",
                   ROOT / "paper/prompt_examples.json"]}
        r = subprocess.run([sys.executable, str(ROOT / "paper/make_prompt_appendix.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, "generator verification failed: " + r.stdout + r.stderr)
        for name, old in before.items():
            new = (ROOT / "paper" / name).read_text()
            self.assertEqual(old, new,
                             f"{name} is stale: regenerate with make_prompt_appendix.py")

    def test_all_18_variants_documented(self):
        a = json.loads((ROOT / "paper/prompt_examples.json").read_text())
        self.assertEqual(len(a["variants"]), 18)
        for v in ("multiple_approaches", "max_certainty", "bounded_efficiency",
                  "misleading_architecture", "split_across_turns"):
            self.assertIn(v, a["variants"])

    def test_primary_variants_preserve_task_content(self):
        a = json.loads((ROOT / "paper/prompt_examples.json").read_text())
        for v in ("multiple_approaches", "deep_thinking", "max_certainty",
                  "bounded_efficiency", "verbose_repetition"):
            self.assertTrue(a["variants"][v]["task_content_preserved"], v)


class TestSemanticExamples(unittest.TestCase):
    def test_examples_are_trace_verified(self):
        import json
        ex = json.loads((ROOT / "paper/semantic_examples.json").read_text())
        self.assertGreaterEqual(len(ex), 5)
        for e in ex:
            self.assertTrue(e["verified_in_trace"], e["mechanism"])

    def test_regeneration_matches(self):
        before = (ROOT / "paper/semantic_examples.tex").read_text()
        r = subprocess.run([sys.executable, str(ROOT / "paper/make_semantic_examples.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(before, (ROOT / "paper/semantic_examples.tex").read_text(),
                         "semantic_examples.tex is stale")


if __name__ == "__main__":
    unittest.main()
