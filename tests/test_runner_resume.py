import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from run_benchmark import completed_keys
from common import append_jsonl


class TestRunnerResume(unittest.TestCase):
    def test_completed_keys_skip_finished_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "runs.jsonl"
            append_jsonl(p, {"harness": "pi", "model": "m", "task_id": "t",
                             "variant": "baseline", "rep": 1, "status": "completed"})
            append_jsonl(p, {"harness": "pi", "model": "m", "task_id": "t",
                             "variant": "deep_thinking", "rep": 1,
                             "status": "infra_error"})
            append_jsonl(p, {"harness": "pi", "model": "m", "task_id": "t",
                             "variant": "adjacent_cleanup", "rep": 1,
                             "status": "timeout"})
            keys = completed_keys(p)
        self.assertIn(("pi", "m", "t", "baseline", 1), keys)
        self.assertIn(("pi", "m", "t", "adjacent_cleanup", 1), keys)  # timeout = real outcome
        self.assertNotIn(("pi", "m", "t", "deep_thinking", 1), keys)  # infra retries

    def test_timeout_kill_actually_kills(self):
        """The runner pattern (start_new_session + killpg) terminates children."""
        import os
        import signal
        p = subprocess.Popen(["bash", "-c", "sleep 30 & sleep 30"],
                             start_new_session=True)
        time.sleep(0.2)
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        t0 = time.time()
        p.wait(timeout=5)
        self.assertLess(time.time() - t0, 5)


if __name__ == "__main__":
    unittest.main()
