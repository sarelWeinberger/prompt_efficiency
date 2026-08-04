"""Unit tests for tool-cost taxonomy, normalization, and redundancy rules
(frozen rubric benchmark/tool_cost_rubric.md §2-§3)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analysis"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from tool_cost_extract import analyze_run, categorize, norm

COST = {"input": 1.0, "output": 5.0, "cache_read": 0.1, "cache_write": 1.25}


def call(name, turn=0, chars=100, err=False, head="", **args):
    return {"name": name, "args": args, "turn": turn, "result_chars": chars,
            "result_head": head, "is_error": err, "dur_s": None}


TURNS = [{"ts": 0, "input": 100, "output": 50, "cache_read": 0, "cache_write": 0},
         {"ts": 1, "input": 300, "output": 50, "cache_read": 0, "cache_write": 0}]


class TestNorm(unittest.TestCase):
    def test_strips_workdir_and_cd(self):
        self.assertEqual(norm("cd /x && ls  -la"), "ls -la")
        self.assertEqual(norm("cat /tmp/pi-prompt-benchmark/slot-03/a.py"),
                         "cat a.py")


class TestCategorize(unittest.TestCase):
    def test_categories(self):
        self.assertEqual(categorize(call("read", path="a.py")), "file_read")
        self.assertEqual(categorize(call("Edit", file_path="a.py")), "code_edit")
        self.assertEqual(categorize(call("bash", command="go test ./...")),
                         "test_execution")
        self.assertEqual(categorize(call("bash", command="rg foo src/")),
                         "file_search")
        self.assertEqual(categorize(call("bash", command="ls -la")), "navigation")
        self.assertEqual(categorize(call("bash", command="git diff")), "git_inspect")
        self.assertEqual(categorize(call("bash", command="python3 --version")),
                         "env_inspect")

    def test_test_beats_search(self):
        # first-match-wins: a test command containing 'grep' is still a test
        self.assertEqual(categorize(call("bash", command="pytest -k 'grep'")),
                         "test_execution")


class TestRedundancy(unittest.TestCase):
    def test_duplicate_command_no_edit(self):
        calls = [call("bash", command="ls"), call("bash", command="ls")]
        m = analyze_run(calls, TURNS, COST)
        self.assertEqual(m["duplicate_commands"], 1)

    def test_edit_resets_duplicate_state(self):
        calls = [call("bash", command="ls"),
                 call("Edit", file_path="a.py"),
                 call("bash", command="ls")]
        m = analyze_run(calls, TURNS, COST)
        self.assertEqual(m["duplicate_commands"], 0)

    def test_repeated_read_same_file_unedited(self):
        calls = [call("read", path="a.py"), call("read", path="a.py")]
        self.assertEqual(analyze_run(calls, TURNS, COST)["repeated_reads"], 1)

    def test_reread_after_edit_not_redundant(self):
        calls = [call("read", path="a.py"),
                 call("Edit", file_path="a.py"),
                 call("read", path="a.py")]
        self.assertEqual(analyze_run(calls, TURNS, COST)["repeated_reads"], 0)

    def test_post_green_repeat_test(self):
        calls = [call("bash", command="pytest", head="2 passed"),
                 call("bash", command="pytest", head="2 passed")]
        m = analyze_run(calls, TURNS, COST)
        self.assertEqual(m["post_green_repeat_tests"], 1)

    def test_rerun_after_red_not_post_green(self):
        calls = [call("bash", command="pytest", head="1 failed", err=True),
                 call("bash", command="pytest", head="2 passed")]
        m = analyze_run(calls, TURNS, COST)
        self.assertEqual(m["post_green_repeat_tests"], 0)


class TestFlagsAndCosts(unittest.TestCase):
    def test_post_success_calls(self):
        calls = [call("Edit", file_path="a.py"),
                 call("bash", command="pytest", head="2 passed"),
                 call("read", path="a.py"),
                 call("bash", command="ls")]
        m = analyze_run(calls, TURNS, COST)
        self.assertEqual(m["post_success_calls"], 2)

    def test_failed_and_recovery(self):
        calls = [call("bash", command="pytest bad", err=True),
                 call("bash", command="ls")]
        m = analyze_run(calls, TURNS, COST)
        self.assertEqual(m["failed_calls"], 1)
        self.assertEqual(m["error_recovery_calls"], 1)

    def test_induced_bounds_ordering_and_growth(self):
        calls = [call("read", path="a.py", turn=0, chars=4000)]
        m = analyze_run(calls, TURNS, COST)
        self.assertGreaterEqual(m["induced_cost_upper_usd"],
                                m["induced_cost_lower_usd"])
        self.assertEqual(m["context_growth_tokens"], 200)  # 300-100

    def test_abandoned_exploration(self):
        calls = [call("read", path="src/used.py"),
                 call("read", path="docs/unrelated.md"),
                 call("Edit", file_path="src/used.py")]
        m = analyze_run(calls, TURNS, COST)
        self.assertEqual(m["abandoned_exploration_calls"], 1)


if __name__ == "__main__":
    unittest.main()
