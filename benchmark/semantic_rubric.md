# Semantic reasoning analysis — frozen rubric (v1)

Status: FROZEN before any holdout-run annotation. Development of this rubric
used only dev-split screening runs. Any change after the freeze commit
requires a new version and re-annotation.

## 1. Artifact inventory (audited 2026-08-02, 5,506 run dirs + 2.5 GB wire capture)

| Tier | Artifact class | Where recorded | Coverage |
|---|---|---|---|
| 1 | **Full textual reasoning traces** | pi: `thinking` blocks in `turn_end` messages of `pi_events.jsonl`. Claude Code: `thinking` blocks in transcript `claude_code_events.jsonl` (LiteLLM translated Together's `reasoning` field into Anthropic thinking blocks). Cross-check: raw `reasoning` field in non-streaming bodies of `together_capture.jsonl`. | All 7 open-weight models (6 frozen + Kimi-K3), both harnesses. Sampled medians 0.4–6.4k chars/run; runs with zero thinking text are real (model chose not to think), not recording gaps. |
| 2 | **Provider reasoning summaries** | none | Never recorded. claude-sonnet-5 runs used the default `display: omitted`; summaries were not requested. |
| 3 | **Visible assistant rationale** | `text` blocks in pi events / CC transcripts; CC `result` field | All runs, all models. |
| 4 | **Reasoning inferred from tool behavior** | `toolCall` blocks + tool results (pi), `tool_use`/`tool_result` (CC), with full arguments (incl. Edit old/new strings) | All runs. Final diffs were NOT retained (workspaces reset); the edit-call sequence is the reconstructable record of changes. |
| 5 | **Token counts only** | ledger usage fields | claude-sonnet-5 (thinking billed inside output, never separable; CC-native thinking blocks present but empty). Sonnet is therefore EXCLUDED from trace annotation and covered by tiers 3–4 + Method B only. |

Hidden chain-of-thought that was never returned by a provider is not claimed,
reconstructed, or imputed anywhere in this analysis.

## 2. Unit of annotation

One run. The judge receives, per run:
- the canonical task specification (objective, acceptance criteria, allowed
  paths — from the task YAML, NOT the variant prompt; keeps the judge
  condition-blind),
- the ordered turn sequence: thinking text, assistant text, tool calls
  (name + key arguments, truncated), tool-result heads,
- visible/hidden test outcomes.
The judge is never shown the variant name, the variant prompt text, or which
condition is baseline.

A "unit" is one reasoning move (roughly a sentence to a short paragraph
serving one function).

## 3. Annotation schema (Method A)

All counts are non-negative integers over the whole run; every count > 0
requires at least one evidence item `{turn, source: thinking|text|tool,
quote ≤ 25 words}`. Unsupported positives are invalid.

Composition counts: `problem_understanding`, `planning`,
`alternative_approaches_considered`, `alternatives_implemented`,
`repo_exploration`, `hypotheses_stated`, `hypotheses_grounded` (stated after
inspecting the relevant code), `evidence_collection`,
`implementation_reasoning`, `testing_verification`, `error_diagnosis`,
`self_corrections`, `final_validation`, `off_task`.

Quality scores (0–3 ordinal; 0 = absent/poor, 3 = consistently good):
`task_relevance`, `factual_grounding`, `logical_consistency`, `specificity`,
`actionability`, `uncertainty_calibration`. Quality counts:
`unsupported_assumptions`, `reversals_without_new_evidence`,
`premature_commitment` (0/1).

Waste-mechanism counts: `unused_branches` (approaches elaborated but absent
from the final edit set), `task_restatements` (re-statements of already-given
requirements), `redundant_verification` (re-checking an already-established
fact with no new evidence), `speculative_architecture` (theories about code
structure asserted before/without inspection), `post_solution_reasoning`
(units after the last necessary edit and first fully-passing test),
`planning_without_implementation` (plan elements never acted on).

Explicitly out of scope: sentiment, tone, politeness. Only functional
structure and epistemic quality are coded.

## 4. Deterministic proxies (Method B) — definitions

Computed mechanically from traces; no model judgment. Per run:
- `first_edit_tool_index`, `tool_calls_before_first_edit`,
  `thinking_chars_before_first_edit`
- `first_green_test_turn` (first test command whose result indicates full
  pass), `tool_calls_after_first_green`, `thinking_chars_after_first_green`,
  `test_runs_after_first_green`
- `distinct_files_read`, `files_read_not_edited`, `duplicate_file_reads`
  (ledger), `repeated_searches` (ledger), `repeated_tests_no_change` (ledger),
  `edits_reverted` (ledger)
- `task_restatement_index`: fraction of 8-word shingles of the task objective
  + acceptance criteria that appear verbatim in the run's thinking+text
- `redundancy_compression_ratio`: 1 − zlib(thinking)/len(thinking); higher =
  more internally repetitive reasoning (reported only when thinking ≥ 500
  chars)
- `plan_marker_count` / `alternative_marker_count`: frozen regex lexicons
  (\b(plan|step \d|first,|then,|finally)\b; \b(option|approach|alternative(ly)?|
  instead|we could|one way|another way)\b) over thinking text, case-insensitive,
  per 1k thinking chars

## 5. Judge configuration

Primary judge: `claude-sonnet-5`, temperature-free (API default), structured
outputs (`output_config.format` json_schema, strict) — grammar-constrained
decoding. Secondary judges for sensitivity: (a) same model, paraphrased
instructions + reordered input sections; (b) `claude-haiku-4-5`, identical
prompt. Batch API used for the full corpus.

## 6. Validation protocol

1. Pilot: 24 stratified runs (models × variants × harnesses), annotated by
   the researcher-in-the-loop before seeing judge output; agreement reported
   (count agreement within ±1; ordinal agreement within ±1; Cohen's kappa on
   binarized presence).
2. Judge–judge agreement on a 60-run overlap sample across the three judge
   configurations.
3. Leakage checks: (a) verbosity — all count metrics also reported per 1k
   thinking chars; (b) condition-name leakage impossible by construction
   (judge never sees variant text); (c) position — input section order
   shuffled in sensitivity config.
4. Rubric frozen (this commit) before any holdout-run annotation; holdout
   annotated once, with the primary judge only.

## 7. Corpus

Method B: every valid run in the ledger (all experiments).
Method A: screening_pi (6 models × 16 dev tasks × 7 variants: baseline,
deep_thinking, exhaustive_exploration, multiple_approaches, max_certainty,
adjacent_cleanup, bounded_efficiency × 2 reps), screening_cc/pilot_b CC runs
for the same variants where they exist, stress_pi misleading_context +
ambiguous_scope vs baseline (H-S4), kimi3_pi (all), holdout_pi
(multiple_approaches, deep_thinking, bounded_efficiency + baseline; annotated
after freeze). claude-sonnet-5 excluded from Method A (no reasoning text;
tier 5).

## 8. Preregistered semantic hypotheses

- H-S1 multiple_approaches ↑ `unused_branches` and
  `alternative_approaches_considered − alternatives_implemented`, with no
  increase in `alternatives_implemented` or task success.
- H-S2 deep_thinking ↑ `task_restatements`, `redundancy_compression_ratio`,
  and elaboration counts, with no increase in `evidence_collection`,
  `factual_grounding`, or implementation quality (success unchanged).
- H-S3 max_certainty ↑ `redundant_verification` and
  `test_runs_after_first_green` / `tool_calls_after_first_green`.
- H-S4 misleading architectural hints ↑ `speculative_architecture` and
  `unsupported_assumptions`; searches concentrate before first correct
  diagnosis.
- H-S5 bounded_efficiency ↓ `unused_branches` and `post_solution_reasoning`
  without reducing `error_diagnosis` or `final_validation`.
- H-S6 Claude Code shifts composition toward planning/orchestration and
  repeated context reconstruction relative to pi at equal success.

Analysis is paired within model × harness × task blocks vs the baseline
variant, mirroring the main benchmark; task-clustered bootstrap CIs.
