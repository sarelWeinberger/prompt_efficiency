#!/usr/bin/env python3
"""Reset a fixed benchmark slot to a task's pristine fixture (design §8).

The slot path stays constant (cache comparability); contents are wiped and
re-copied, then committed to a fresh git repo so evaluate_run can diff.
"""
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BENCH, dir_hash

GIT_ENV = {"GIT_AUTHOR_NAME": "bench", "GIT_AUTHOR_EMAIL": "b@b",
           "GIT_COMMITTER_NAME": "bench", "GIT_COMMITTER_EMAIL": "b@b",
           "HOME": "/tmp/pi-prompt-benchmark"}


def reset_slot(slot: Path, task_id: str) -> str:
    """Wipe slot contents, copy fixture, git-commit baseline. Returns fixture hash."""
    slot = Path(slot)
    fixture = BENCH / "fixtures" / task_id
    if not fixture.is_dir():
        raise FileNotFoundError(f"no fixture for {task_id}")
    slot.mkdir(parents=True, exist_ok=True)
    for child in slot.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    shutil.copytree(fixture, slot, dirs_exist_ok=True)
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "-c", "user.name=bench", "-c", "user.email=b@b",
                 "commit", "-qm", "fixture"]):
        subprocess.run(cmd, cwd=slot, capture_output=True, env={**GIT_ENV})
    return dir_hash(slot)


if __name__ == "__main__":
    print(reset_slot(Path(sys.argv[1]), sys.argv[2]))
