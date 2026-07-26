#!/usr/bin/env python3
"""Generate prompt variants for every task from benchmark/prompt_families.yaml.

Writes benchmark/generated_prompts/<task>/<variant>.json with full provenance
(design §11) and validates that primary variants preserve task semantics.
"""
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BENCH, GENERATOR_VERSION, all_task_ids, estimate_tokens, load_task, sha256

OUT = BENCH / "generated_prompts"


def _families():
    return yaml.safe_load((BENCH / "prompt_families.yaml").read_text())


def _slots(task):
    obj = task["objective"]
    words = obj.split()
    half = len(words) // 2
    return {
        "objective": obj,
        "scope": task["scope"],
        "criteria": task["criteria"],
        "test_cmd": task["test_cmd"],
        "stop": task["stop"],
        "objective_vague": task.get("objective_vague", "the reported behavior"),
        "misleading_hint": task.get("misleading_hint", "most recently changed file"),
        "objective_first_half": " ".join(words[:half]),
        "objective_second_half": " ".join(words[half:]),
    }


def generate_task(task_id, fam=None):
    fam = fam or _families()
    task = load_task(task_id)
    slots = _slots(task)
    out = {}
    for family, variants in (("primary", fam["primary"]), ("stress", fam["stress"])):
        for name, spec in variants.items():
            if "turns" in spec:
                text_turns = [t.format(**slots) for t in spec["turns"]]
                final_text = "\n<TURN-BREAK>\n".join(text_turns)
            else:
                final_text = spec["template"].format(**slots).strip()
                text_turns = [final_text]
            out[name] = {
                "task_id": task_id,
                "variant": name,
                "family": family,
                "features": spec["features"],
                "turns": text_turns,
                "text": final_text,
                "char_count": len(final_text),
                "byte_count": len(final_text.encode()),
                "est_prompt_tokens": estimate_tokens(final_text),
                "sha256": sha256(final_text),
                "generator_version": fam["generator_version"],
                "task_criteria": task["criteria"],
                "task_scope": task["scope"],
                "task_test_cmd": task["test_cmd"],
            }
    return out


def validate_task(task_id, prompts):
    """Primary variants must preserve objective, criteria and test command."""
    task = load_task(task_id)
    errors = []
    for name, p in prompts.items():
        if p["family"] != "primary":
            continue
        if task["objective"] not in p["text"]:
            errors.append(f"{task_id}/{name}: objective text altered or missing")
        if name in ("goal_only",):
            continue  # intentionally omits criteria
        if task["test_cmd"] not in p["text"]:
            errors.append(f"{task_id}/{name}: test_cmd missing")
        if task["criteria"] not in p["text"]:
            errors.append(f"{task_id}/{name}: acceptance criteria altered or missing")
    return errors


def main():
    fam = _families()
    all_errors = []
    n = 0
    for tid in all_task_ids():
        prompts = generate_task(tid, fam)
        all_errors += validate_task(tid, prompts)
        d = OUT / tid
        d.mkdir(parents=True, exist_ok=True)
        for name, p in prompts.items():
            (d / f"{name}.json").write_text(json.dumps(p, indent=1))
            n += 1
    if all_errors:
        print("VALIDATION FAILURES:")
        for e in all_errors:
            print(" -", e)
        sys.exit(1)
    print(f"generated {n} prompts for {len(all_task_ids())} tasks; validation clean")


if __name__ == "__main__":
    main()
