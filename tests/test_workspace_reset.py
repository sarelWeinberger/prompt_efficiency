import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from reset_workspace import reset_slot

SLOT = Path("/tmp/pi-prompt-benchmark/slot-test")


class TestWorkspaceReset(unittest.TestCase):
    def test_reset_is_deterministic_and_cleans_dirt(self):
        h1 = reset_slot(SLOT, "py-low-01")
        (SLOT / "junk.txt").write_text("dirt")
        (SLOT / "shop" / "discount.py").write_text("corrupted")
        h2 = reset_slot(SLOT, "py-low-01")
        self.assertEqual(h1, h2)
        self.assertFalse((SLOT / "junk.txt").exists())
        self.assertIn("apply_discount", (SLOT / "shop" / "discount.py").read_text())

    def test_reset_switches_tasks(self):
        reset_slot(SLOT, "py-low-01")
        reset_slot(SLOT, "go-low-01")
        self.assertTrue((SLOT / "stats" / "stats.go").exists())
        self.assertFalse((SLOT / "shop").exists())

    def test_git_baseline_committed(self):
        reset_slot(SLOT, "py-low-01")
        p = subprocess.run(["git", "status", "--porcelain"], cwd=SLOT,
                           capture_output=True, text=True)
        self.assertEqual(p.stdout.strip(), "")

    def test_slot_path_is_stable(self):
        reset_slot(SLOT, "py-low-01")
        before = str(SLOT.resolve())
        reset_slot(SLOT, "py-low-01")
        self.assertEqual(before, str(SLOT.resolve()))


if __name__ == "__main__":
    unittest.main()
