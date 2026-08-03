#!/usr/bin/env python3
"""Method A: structured judge annotation of reasoning traces (rubric v1, §3, §5).

The judge is condition-blind: it sees the canonical task spec (never the
variant prompt or its name), the recorded trace, and test outcomes. Output is
grammar-constrained to benchmark/semantic_schema.json via structured outputs.

Usage:
  python3 analysis/judge_annotate.py --select            # print corpus counts
  python3 analysis/judge_annotate.py --pilot 24          # sync pilot sample
  python3 analysis/judge_annotate.py --submit primary    # batch: full corpus
  python3 analysis/judge_annotate.py --submit alt_prompt --overlap 60
  python3 analysis/judge_annotate.py --submit haiku --overlap 60
  python3 analysis/judge_annotate.py --collect <batch_id> --judge primary
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import ROOT, load_config, load_task, read_jsonl, env_secret

sys.path.insert(0, str(Path(__file__).resolve().parent))
from semantic_trace import load_trace

CFG = load_config()
RAW = ROOT / CFG["raw_dir"]
SCHEMA = json.loads((ROOT / "benchmark/semantic_schema.json").read_text())
OUT_DIR = ROOT / "results/semantic"

JUDGE_MODELS = {"primary": "claude-sonnet-5", "alt_prompt": "claude-sonnet-5",
                "haiku": "claude-haiku-4-5"}

VARIANTS_A = {"baseline", "deep_thinking", "exhaustive_exploration",
              "multiple_approaches", "max_certainty", "adjacent_cleanup",
              "bounded_efficiency"}
HOLDOUT_VARIANTS = {"baseline", "multiple_approaches", "deep_thinking",
                    "bounded_efficiency"}
STRESS_VARIANTS = {"misleading_architecture", "ambiguous_scope"}
EXCLUDED_MODELS = {"claude-sonnet-5"}  # tier 5: no reasoning text recorded

SYSTEM_PRIMARY = """You are annotating the recorded reasoning of a coding agent for a research \
study of reasoning structure and epistemic quality. You will receive the task \
specification, the agent's recorded reasoning ("thinking"), its visible \
messages, its tool calls with result excerpts, and the test outcome.

Count reasoning UNITS: one unit is a distinct reasoning move (roughly one \
sentence to one short paragraph serving a single function). Definitions:
- problem_understanding: restating/interpreting what the task requires (count \
each distinct interpretation once; verbatim re-statements of already-given \
requirements are counted under waste.task_restatements instead).
- planning: statements of intended next actions or ordered steps.
- alternative_approaches_considered: distinct solution strategies elaborated \
(not a passing mention - it must be developed by at least a sentence).
- alternatives_implemented: of those, strategies actually reflected in edits.
- repo_exploration: reasoning about where things are / what to look at.
- hypotheses_stated: candidate explanations of behavior or bug causes.
- hypotheses_grounded: subset stated AFTER the relevant code was inspected in \
the trace (evidence must cite the inspection).
- evidence_collection: reading/searching/test observations interpreted.
- implementation_reasoning: reasoning about the concrete change being made.
- testing_verification: reasoning about running or interpreting tests.
- error_diagnosis: reasoning from an observed failure toward its cause.
- self_corrections: explicit revisions of the agent's own earlier claim/plan.
- final_validation: end-of-run confirmation that criteria are met.
- off_task: reasoning unrelated to the task.

Quality scores are 0-3 ordinals over the WHOLE run: 0 absent/poor, 1 weak, \
2 adequate, 3 consistently good. uncertainty_calibration: 3 = confidence \
tracks evidence; 0 = confident claims without support or hedging on \
established facts. premature_commitment: 1 if the agent locked in a solution \
before inspecting the code it modifies.

Waste mechanisms:
- unused_branches: approaches elaborated but absent from the final edits.
- task_restatements: near-verbatim repetitions of already-given requirements.
- redundant_verification: re-establishing an already-established fact with no \
new evidence in between.
- speculative_architecture: claims about code structure asserted before or \
without inspecting it.
- post_solution_reasoning: units occurring after the last edit AND after a \
fully-passing test run.
- planning_without_implementation: plan elements never acted on.

STRICT EVIDENCE RULE: every count > 0 and every score of 0 or 3 requires at \
least one evidence item {field, turn, source, quote <= 25 words}. Counts you \
cannot support with a quote must be 0. Do not infer hidden reasoning that is \
not in the record: if the thinking text is empty, code only what is visible.
This is not sentiment analysis; tone is irrelevant."""

SYSTEM_ALT = """Task: research annotation of a coding agent's recorded deliberation - its \
functional structure and epistemic quality (never tone or sentiment). Input: \
task spec, recorded thinking, visible messages, tool calls with result \
snippets, test outcome. Produce unit counts, ordinal quality scores, and \
waste-mechanism counts per the schema.

A unit = one reasoning move (about a sentence to a short paragraph with one \
function). Category definitions are as follows. problem_understanding: \
interpreting task requirements (verbatim repetitions belong to \
task_restatements). planning: declared next actions. \
alternative_approaches_considered: distinct strategies developed by at least \
a sentence; alternatives_implemented: those visible in the edits. \
repo_exploration: where-to-look reasoning. hypotheses_stated: candidate \
explanations; hypotheses_grounded: those stated only after the relevant code \
was inspected. evidence_collection: interpreting reads/searches/tests. \
implementation_reasoning: about the concrete change. testing_verification: \
about running/reading tests. error_diagnosis: failure-to-cause reasoning. \
self_corrections: explicit self-revisions. final_validation: closing \
criteria checks. off_task: unrelated.

Scores are 0-3 for the whole run (0 absent/poor ... 3 consistently good); \
premature_commitment is 1 only if a fix was locked in before inspecting the \
modified code. Waste: unused_branches (developed, never in final edits); \
task_restatements; redundant_verification (re-proving settled facts); \
speculative_architecture (structure claims without inspection); \
post_solution_reasoning (after last edit and a green test); \
planning_without_implementation.

Hard rule: any nonzero count and any 0 or 3 score needs one evidence item \
{field, turn, source, quote <= 25 words}; otherwise report 0. Never impute \
reasoning that was not recorded."""


def corpus(runs):
    sel = []
    for r in runs:
        if r.get("run_validity") != "valid" or r.get("status") not in ("completed", "timeout"):
            continue
        if r.get("model") in EXCLUDED_MODELS:
            continue
        e, v = r.get("experiment"), r.get("variant")
        take = ((e == "screening_pi" and v in VARIANTS_A)
                or (e in ("screening_cc", "pilot_b") and v in VARIANTS_A)
                or (e == "stress_pi" and v in STRESS_VARIANTS)
                or (e == "kimi3_pi")
                or (e == "holdout_pi" and v in HOLDOUT_VARIANTS))
        if take:
            sel.append(r)
    return sel


def render_input(r, max_think=6000, max_text=2000, max_res=400, max_total=60000):
    task = load_task(r["task_id"])
    turns, _ = load_trace(RAW / r["run_id"])
    if turns is None:
        return None
    spec = {"objective": task.get("objective"),
            "acceptance_criteria": task.get("acceptance_criteria"),
            "allowed_paths": task.get("allowed_paths")}
    lines = ["## Task specification", json.dumps(spec, indent=1), "", "## Recorded trace"]
    for i, t in enumerate(turns):
        lines.append(f"### Turn {i}")
        if t["thinking"]:
            th = t["thinking"]
            lines.append("[thinking] " + (th[:max_think] +
                         (f" ...[{len(th)-max_think} chars truncated]" if len(th) > max_think else "")))
        if t["text"]:
            tx = t["text"]
            lines.append("[assistant text] " + (tx[:max_text] +
                         (f" ...[truncated]" if len(tx) > max_text else "")))
        for tc in t["tools"]:
            args = json.dumps(tc["args"])[:300]
            res = (tc.get("result_head") or "")[:max_res]
            lines.append(f"[tool {tc['name']}] args={args}")
            lines.append(f"[tool result{' ERROR' if tc.get('is_error') else ''}] {res}")
    lines += ["", "## Outcome",
              f"visible_tests_passed={r.get('visible_test_pass')} "
              f"hidden_tests_passed={r.get('hidden_test_pass')} "
              f"scope_compliant_success={r.get('scope_compliant_success')}"]
    doc = "\n".join(lines)
    return doc[:max_total]


def build_request(r, judge, custom_id):
    doc = render_input(r)
    if doc is None:
        return None
    system = SYSTEM_ALT if judge == "alt_prompt" else SYSTEM_PRIMARY
    return {
        "custom_id": custom_id,
        "params": {
            "model": JUDGE_MODELS[judge],
            "max_tokens": 16000,
            "system": [{"type": "text", "text": system,
                        "cache_control": {"type": "ephemeral"}}],
            "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
            "messages": [{"role": "user", "content": doc}],
        },
    }


def client():
    import anthropic
    return anthropic.Anthropic(api_key=env_secret("ANTHROPIC_API_KEY"))


def overlap_sample(sel, n, seed=11):
    rnd = random.Random(seed)
    return rnd.sample(sel, min(n, len(sel)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--select", action="store_true")
    ap.add_argument("--pilot", type=int)
    ap.add_argument("--submit", choices=list(JUDGE_MODELS))
    ap.add_argument("--overlap", type=int, help="use N-run overlap sample instead of full corpus")
    ap.add_argument("--collect", help="batch id")
    ap.add_argument("--judge", default="primary")
    ap.add_argument("--exclude-holdout", action="store_true",
                    help="dev-split only (pre-freeze development)")
    args = ap.parse_args()

    runs = read_jsonl(ROOT / "results/runs.jsonl")
    sel = corpus(runs)
    if args.exclude_holdout:
        sel = [r for r in sel if r["experiment"] != "holdout_pi"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.select:
        from collections import Counter
        c = Counter((r["experiment"], r["harness"]) for r in sel)
        for k, v in sorted(c.items()):
            print(k, v)
        print("total", len(sel))
        return

    if args.pilot:
        rnd = random.Random(3)
        strata = {}
        for r in sel:
            strata.setdefault((r["harness"], r["variant"]), []).append(r)
        picks = []
        keys = sorted(strata)
        while len(picks) < args.pilot and keys:
            for k in list(keys):
                if len(picks) >= args.pilot:
                    break
                pool = strata[k]
                if pool:
                    picks.append(pool.pop(rnd.randrange(len(pool))))
                else:
                    keys.remove(k)
        cl = client()
        out = open(OUT_DIR / "pilot_annotations.jsonl", "w")
        for i, r in enumerate(picks):
            req = build_request(r, "primary", r["run_id"])
            resp = cl.messages.create(**req["params"])
            txt = next((b.text for b in resp.content if b.type == "text"), None)
            ann, err = None, None
            if txt is None:
                err = f"no_text_block stop_reason={resp.stop_reason}"
            else:
                try:
                    ann = json.loads(txt)
                except json.JSONDecodeError:
                    err = "invalid_json"
            out.write(json.dumps({"run_id": r["run_id"], "variant": r["variant"],
                                  "model": r["model"], "harness": r["harness"],
                                  "annotation": ann, "error": err}) + "\n")
            out.flush()
            print(f"[{i+1}/{len(picks)}] {r['run_id']}" + (f" ERR={err}" if err else ""))
        out.close()
        return

    if args.submit:
        pool = overlap_sample(sel, args.overlap) if args.overlap else sel
        reqs = []
        for r in pool:
            req = build_request(r, args.submit, r["run_id"])
            if req:
                reqs.append(req)
        cl = client()
        ids = []
        for i in range(0, len(reqs), 9000):
            batch = cl.messages.batches.create(requests=reqs[i:i + 9000])
            ids.append(batch.id)
            print("submitted", batch.id, len(reqs[i:i + 9000]), "requests")
        (OUT_DIR / f"batch_{args.submit}.json").write_text(json.dumps(ids))
        return

    if args.collect:
        cl = client()
        out = open(OUT_DIR / f"annotations_{args.judge}.jsonl", "a")
        n = ok = 0
        for res in cl.messages.batches.results(args.collect):
            n += 1
            if res.result.type != "succeeded":
                out.write(json.dumps({"run_id": res.custom_id,
                                      "error": res.result.type}) + "\n")
                continue
            msg = res.result.message
            txt = next((b.text for b in msg.content if b.type == "text"), None)
            try:
                ann = json.loads(txt)
                ok += 1
            except (TypeError, json.JSONDecodeError):
                ann = None
            out.write(json.dumps({"run_id": res.custom_id, "annotation": ann}) + "\n")
        out.close()
        print(f"collected {n} results, {ok} valid annotations -> annotations_{args.judge}.jsonl")


if __name__ == "__main__":
    main()
