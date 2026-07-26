# Experiment Design — Prompt-Induced Waste in Large Reasoning Models under PI.DEV and Claude Code

**Status: pre-registered.** Hypotheses, metrics, waste definitions, and protocols in this
document were frozen before any benchmark (pilot/screening/holdout) results were examined.
Compatibility smoke tests and harness calibration measurements are validation steps, not
benchmark results, and preceded this freeze only where §0 says so.

## 0. Measured priors (from this repository, retained unchanged)

From [TOKEN-ANALYSIS.md](TOKEN-ANALYSIS.md) (GLM-5.2, PI.DEV 0.82.1, single-shot):

| Configuration | Input tokens |
|---|---|
| default PI.DEV | ≈1,291 |
| `--no-tools` | ≈464 |
| `--no-tools` + minimal system prompt | ≈71 |

Component split: ≈827 tokens tool schemas, ≈399 system prompt (≈206 of which are pi
self-documentation paths), ≈64 chat template/envelope, ≈1 user message.

From [CACHE-ANALYSIS.md](CACHE-ANALYSIS.md) (continuous sessions): Together applies
automatic, free-to-populate prefix caching (cached input at $0.17–0.26/M vs $0.60–1.74/M
list); hits are probabilistic (observed hit→partial→miss→hit within one session); the
cache can hit on the first turn of a new session (shared static prefix); a miss re-bills
the entire accumulated history.

Gateway calibration (2026-07-26, smoke run): Claude Code 2.1.220 through LiteLLM 1.93.0
sends ≈16.9k input tokens per request to Together for a trivial task (≈6.7 KB system
prompt + 24 tool schemas) vs PI.DEV's ≈1.29k — a ≈13× fixed-prefix difference.
LiteLLM upstream protocol is the OpenAI Responses API (`/v1/responses`), which returns
explicit `output_tokens_details.reasoning_tokens` and `input_tokens_details.cached_tokens`;
the Anthropic-side translation preserves input/output totals but **drops** reasoning and
cache detail fields.

Consequences built into this design:
1. Prompt character count is not a measure of input cost (fixed overhead dominates short tasks).
2. Tool configuration is held constant within every comparison; `--no-tools` appears only in calibration (Experiment B).
3. Behavioral efficiency and billing efficiency are tracked as separate metric families (§5).
4. A cache hit is a billing event, not a reasoning-efficiency event.
5. Authoritative reasoning tokens come from the Together-facing capture, never from harness-displayed estimates.

## 1. Research objective

Identify user-prompt formulations that cause each tested model, under each harness, to
consume excess reasoning tokens, tool calls, turns, time, or no-cache cost **without a
corresponding improvement in correctness, reliability, or scope compliance**.

Primary metric: `reasoning_tokens_per_success`, interpreted only alongside success rate,
hidden-test score, scope compliance, and the paired baseline (§8).

Outcome classes: `useful_deliberation`, `wasteful`, `harmful_overthinking`,
`inconclusive` — plus `harness_overhead` and `cache_savings` as non-prompt attributions.

## 2. Fixed scope

Models (frozen, [benchmark/models.yaml](benchmark/models.yaml)): DeepSeek-V4-Pro,
Kimi-K2.6, Kimi-K2.7-Code, nemotron-3-ultra-550b-a55b, Inkling, GLM-5.2 — all ≥500B-class
per provider metadata. Qwen3.6-Plus/Qwen3.7-Max excluded: no authoritative parameter-count
source (unknown size ≠ inclusion).

Harnesses: `pi` (0.82.1, direct to Together) and `claude-code` (2.1.220, via LiteLLM
1.93.0 gateway with dual-side capture). The real harnesses are used as shipped; the
gateway translates protocol only. A model enters the Claude Code arm only after its tool
loop passes the empirical smoke suite (results/compatibility/).

Primary matrix: `model × harness × task × prompt_variant × repetition`.

## 3. Pre-registered hypotheses

- **H1 Deep-thinking cues** ("think very deeply", "reason through every possibility",
  "be absolutely certain", "verify repeatedly") increase reasoning tokens more than
  correctness.
- **H2 Exhaustive exploration** ("inspect the entire repository first") increases
  reasoning tokens, files read, search commands, duplicate reads, and time to first
  relevant edit.
- **H3 Scope expansion** (permission for adjacent cleanup/refactoring) increases changed
  files/lines, out-of-scope changes, tests run, and reasoning tokens.
- **H4 Bounded prompting** (clear scope + acceptance criteria + stop condition) reduces
  work without materially reducing success.
- **H5 Ambiguity** increases run-to-run variance and produces model-specific failure
  modes (over-investigation, premature edits, wrong inferred requirements).
- **H6 Cache-cost divergence**: continuous-session cache hits reduce billed cost but not
  reasoning tokens, tool calls, or logical context size.
- **H7 History amplification**: a cache miss late in a long session costs more than one
  early in a short session (whole history re-billed).
- **H8 Fixed-overhead dominance**: for simple tasks, harness overhead dominates input
  tokens, making prompt length a weak cost predictor (much stronger under Claude Code's
  ≈17k prefix than PI.DEV's ≈1.3k).
- **H12 Harness interaction**: the same prompt feature produces different waste patterns
  under PI.DEV vs Claude Code (different system prompts, tools, permissions, context
  management).
- **H13 Claude Code autonomy**: "do not ask questions / do whatever is necessary"
  interacts with permission mode and may increase attempted out-of-scope actions.
- **H14 Claude Code planning overhead**: deep-thinking / exhaustive / maximum-certainty
  cues increase pre-edit planning turns more under Claude Code than PI.DEV.
- **H15 Harness-native guardrails**: explicit authorized/forbidden-scope blocks have
  smaller marginal effect where the harness already enforces permissions.
- **H16 Gateway metadata loss**: reasoning/cache metadata is dropped or transformed
  between Together, the gateway, and Claude Code (already observed in calibration; the
  benchmark quantifies it per model).
- **H17 Gateway-induced retries**: protocol incompatibilities trigger retries or
  malformed-tool-call recovery, inflating cost and tool-loop length independent of the
  user prompt.

## 4. Experiment families

- **A — prompt-induced waste** (primary): fresh single-task sessions; everything constant
  except user-prompt wording. Within-block randomized variant order, paired analysis.
- **B — harness overhead calibration**: fixed-prefix measurement per harness/model;
  PI.DEV ablations (default / --no-tools / reduced / minimal system prompt); Claude Code
  observable ablations (permission modes, with/without CLAUDE.md, tool restriction).
  Diagnostic only — never merged with A.
- **C — session & cache behavior**: cold vs continuous sessions, immediate/delayed
  follow-ups, restatements, prefix perturbations (system prompt byte-change, tool-set
  change, cwd change), per harness. Never merged with A.

## 5. Metric families (kept separate)

Behavioral: reasoning tokens, visible output tokens, tool calls (by tool), turns, files
inspected, duplicate reads, repeated searches, repeated test runs, time to first tool
call / first relevant edit, wall time, work after acceptance, out-of-scope changes,
visible/hidden test results, success.

Billing: uncached input tokens, cached input tokens, `logical_input = uncached + cached`,
`reported_cost_usd`, `estimated_no_cache_cost_usd`, `estimated_cache_savings_usd`,
`cache_read_ratio`. Costs for gateway runs are computed from the Together-facing capture
at catalog prices (Claude Code's own `total_cost_usd` is known-wrong for aliased models —
calibration measured $0.17 reported vs ≈$0.05 actual).

## 6. Task dataset

24 deterministic tasks: 8 low / 8 medium / 8 high; Python 9, JS 9, Go 6; independent
fixtures per task; each with clean fixture, one concrete objective, explicit acceptance
criteria, visible tests, hidden deterministic tests (never present in the workspace),
allowed/forbidden paths, expected scope, complexity label, per-task evaluator.
16 development + 8 frozen holdout ([benchmark/tasks/](benchmark/tasks/)). Holdout prompts
and evaluators are frozen before holdout results are viewed.

## 7. Prompt variants

Primary (semantically matched; acceptance criteria identical): `baseline`,
`verbose_repetition`, `deep_thinking`, `exhaustive_exploration`, `multiple_approaches`,
`max_certainty`, `adjacent_cleanup`, `no_questions_autonomy`, `bounded_efficiency`,
plus `goal_only` and `scoped_authorization` for the harness/permission axes.
Stress (analyzed separately; not causal evidence for wording): `missing_criteria`,
`ambiguous_scope`, `conflicting_constraints`, `irrelevant_context`,
`misleading_architecture`, `split_across_turns`, `full_restatement_per_turn`.
Definitions frozen in [benchmark/prompt_families.yaml](benchmark/prompt_families.yaml);
generator validation asserts criteria invariance for primary variants.

## 8. Analysis plan

Paired within model×harness×task blocks. Per feature×model×harness: n valid runs,
failures/timeouts, median reasoning tokens, median excess vs paired baseline
(`excess = r − median_baseline`), median ratio (`ratio = r / median_baseline`; a
zero-token baseline reports excess only and flags ratio undefined — no division by zero,
no substitute denominator), success rate, cost and no-cache cost per success, tool calls,
repeated operations, task-clustered bootstrap 95% CIs. Cross-model comparisons use
within-model normalized effects only (tokenizers and reporting semantics differ).
Cross-harness comparisons pool only `run_validity = valid` runs; compatibility failures
are excluded from task-quality conclusions and reported separately.

Waste classification (provisional thresholds in benchmark/config.yaml; sensitivity
reported): `wasteful` requires (1) increased reasoning/tool work/time/no-cache cost,
(2) no material success or hidden-test improvement, (3) effect on ≥2 tasks/reps,
(4) not explained by cache outcome alone, (5) CI excluding trivial effect
(median ratio > 1.5, CI lower bound > 1.1) or operationally large effect.
`harmful_overthinking` adds lower success / regressions / scope violations / timeouts /
reverted edits. Otherwise `useful_deliberation` or `inconclusive`.

## 9. Pilot protocol

**Pilot A (PI.DEV)**: DeepSeek-V4-Pro, Kimi-K2.6, nemotron-3-ultra, GLM-5.2 × 6 dev tasks
(2 low / 2 med / 2 high) × {baseline, deep_thinking, exhaustive_exploration,
adjacent_cleanup, bounded_efficiency} × 3 reps, randomized within blocks, budget-capped.
Validates parsing, capture, resets, evaluation, timeouts, cache classification, cost
estimation, resume, redaction. K2.7-Code and Inkling join at screening.

**Pilot B (Claude Code)**: smoke suite for all six models first; then all tool-loop-valid
models × 3 tasks (1 low / 1 med / 1 high) × {baseline, goal_only, scoped_authorization,
deep_thinking, exhaustive_exploration, no_questions_autonomy, bounded_efficiency} × 2
reps. If cost-constrained, tasks are cut before model coverage. Incompatible models are
documented with the failing step, never silently dropped.

Budgets: pilot ≤ $10 reported / $20 estimated-no-cache (benchmark/config.yaml); per-run
cost cap $0.60; per-run timeouts 240/360/480 s by complexity. Screening starts only after
pilot validation and an explicit cost-ceiling confirmation.

## 10. Controls

Fixed workspace slots under /tmp/pi-prompt-benchmark/slot-NN (stable absolute paths;
contents reset per run; same slot within every paired block). Recorded per run: slot,
cwd hash, system-prompt hash, tool-schema hash, prefix hashes before/after gateway
translation, fixture hash, generator version, pi/claude/gateway versions, permission
mode, thinking setting (requested + effective from captured request bodies), execution
timestamp and order index, environment metadata. Raw event streams and gateway captures
retained with secrets redacted. Runner: resumable, deduplicating, budget- and
timeout-enforcing, kills expired processes, restores fixtures, validates the expected
model actually served the run (captured request body model field).
