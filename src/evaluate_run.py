#!/usr/bin/env python3
"""Deterministic per-run evaluation: visible tests, hidden tests, diff and scope.

Hidden tests never live in the workspace during the agent run; they are copied
in afterwards, executed, and removed (design §9, §26).
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BENCH, load_task, run_env


def _run(cmd, cwd, timeout=120):
    try:
        p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, env=run_env({"HOME": str(Path.home())}))
        return p.returncode, (p.stdout + p.stderr)[-4000:]
    except subprocess.TimeoutExpired:
        return -9, "evaluator timeout"


def git_diff_stats(slot):
    slot = Path(slot)
    rc, out = 0, ""
    p = subprocess.run(["git", "diff", "--numstat", "HEAD"], cwd=slot,
                       capture_output=True, text=True)
    added = removed = 0
    changed = []
    for line in p.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            a, r, path = parts
            added += 0 if a == "-" else int(a)
            removed += 0 if r == "-" else int(r)
            changed.append(path)
    p2 = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"],
                        cwd=slot, capture_output=True, text=True)
    created = [f for f in p2.stdout.splitlines() if f]
    return {"files_changed": changed, "files_created": created,
            "lines_added": added, "lines_removed": removed}


def scope_check(diff, allowed_paths):
    """A changed/created path is in scope if it matches an allowed path prefix
    or is an ephemeral test artifact."""
    out_of_scope = []
    for path in diff["files_changed"] + diff["files_created"]:
        ok = any(path == ap or path.startswith(ap.rstrip("/") + "/") or
                 Path(path).match(ap) for ap in allowed_paths)
        artifact = ("__pycache__" in path or path.endswith((".pyc", ".pyo"))
                    or path.startswith(("tests_hidden/", ".claude/", ".bench-session/", "go.sum")))
        if not ok and not artifact:
            out_of_scope.append(path)
    return out_of_scope


def run_hidden(slot, task_id, timeout=120):
    ev = json.loads((BENCH / "evaluators" / task_id / "eval.yaml").read_text())
    slot = Path(slot)
    copied = []
    for item in ev.get("hidden_copy", []):
        src = BENCH / "evaluators" / task_id / item["src"]
        dst = slot / item["dst"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copy(src, dst)
            copied.append(dst)
    rc, out = _run(ev["hidden_cmd"], slot, timeout)
    for dst in copied:
        dst.unlink(missing_ok=True)
    for extra in ev.get("hidden_cleanup", []):
        (slot / extra).unlink(missing_ok=True)
    hidden_dir = slot / "tests_hidden"
    if hidden_dir.exists():
        shutil.rmtree(hidden_dir, ignore_errors=True)
    return rc == 0, out


def evaluate(slot, task_id, edited_paths=None, timeout=120):
    task = load_task(task_id)
    vis_rc, vis_out = _run(task["test_cmd"], slot, timeout)
    hid_ok, hid_out = run_hidden(slot, task_id, timeout)
    diff = git_diff_stats(slot)
    oos = scope_check(diff, task["allowed_paths"])
    reverted = []
    for p in (edited_paths or []):
        norm = str(Path(p)) if p else ""
        rel = norm.lstrip("/")
        if rel and rel not in diff["files_changed"] and rel not in diff["files_created"]:
            reverted.append(rel)
    visible_ok = vis_rc == 0
    return {
        "visible_test_pass": visible_ok,
        "hidden_test_pass": hid_ok,
        "task_success": visible_ok and hid_ok,
        "scope_compliant_success": visible_ok and hid_ok and not oos,
        "out_of_scope_changes": oos,
        "files_changed_count": len(diff["files_changed"]),
        "files_created_count": len(diff["files_created"]),
        "lines_added": diff["lines_added"],
        "lines_removed": diff["lines_removed"],
        "edits_reverted": reverted,
        "visible_test_tail": vis_out[-800:],
        "hidden_test_tail": hid_out[-800:],
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(Path(sys.argv[1]), sys.argv[2]), indent=1))
