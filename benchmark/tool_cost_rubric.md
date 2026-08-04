# Tool-cost analysis — frozen rubric (v1)

Status: FROZEN before any condition-aware tool-cost analysis. Definitions
below were fixed after a read-only telemetry audit and before joining tool
metrics to variant labels in outcome tables.

## 1. Telemetry audit (read-only, 2026-08-03)

Recoverable per tool invocation:

| Field | pi | Claude Code | Notes |
|---|---|---|---|
| tool name + full arguments | yes | yes | `tool_execution_start`.args / `tool_use`.input |
| invocation timestamp | turn-level only | **yes, per record (ISO ms)** | pi events carry no per-call ts; turn_end timestamps bound each turn |
| duration | **missing** (inter-turn deltas only) | yes (tool_use ts -> tool_result ts) | |
| exit status / error flag | yes (`isError`) | yes (`is_error`) | numeric exit codes only when echoed in output text |
| stdout/stderr size | yes (full result content) | yes (full tool_result + structured `toolUseResult`) | |
| serialized result token count | estimated (chars/4) | estimated (chars/4) | provider tokenizers differ; documented approximation |
| file state at invocation | reconstructable only by replaying edit args | same | workspaces were reset; not materialized in this analysis |
| changed-since-last-equivalent-call | yes (deterministic from edit sequence) | yes | basis of redundancy rules |
| direct monetary charge | **none exists** | **none exists** | all tools are local (bash/read/edit/write); no paid search/API/CI was used anywhere in the benchmark. No dollar figure is fabricated for local compute. |
| per-turn model usage | **yes** (input/output/cacheRead/cacheWrite/reasoning per turn) | **yes** (usage per assistant API call) | enables direct measurement of context growth |
| cache read/write telemetry | yes (per turn) | yes (per call) | |
| first green visible test | yes (deterministic) | yes | |
| hidden-evaluator mid-run completion point | **not recoverable** | **not recoverable** | hidden tests never entered the workspace; would require file-state replay. Operational completion proxy (frozen): last edit AND first fully-green visible test. "Post-success" analyses use this proxy and say so. |
| CPU/GPU time, peak memory | **missing** | **missing** | never recorded |

claude-sonnet-5: included in all deterministic tool-level analyses (its
transcripts carry tool calls, results, timestamps, usage); excluded from any
reasoning-trace claim (no thinking text; unchanged from semantic rubric).

## 2. Tool taxonomy (deterministic; name + normalized-command regex)

Categories (first match wins, applied to bash commands; non-bash tools map
directly): `navigation` (ls/pwd/tree/find -type d), `file_search`
(grep/rg/ag/find -name), `file_read` (read tool; cat/head/tail/sed -n),
`code_edit` (edit/write/MultiEdit), `test_execution` (go test/pytest/
unittest/npm test/node --test), `build_compile` (go build/vet OFF —> see
lint; make, npm ci/install, pip install, tsc, go mod), `lint_static`
(lint/eslint/flake8/go vet), `git_inspect` (git status/log/diff/show),
`env_inspect` (--version/which/echo $/uname), `external_network`
(curl/wget/pip download), `other_bash`.

Overlay flags (not categories): `failed` (isError), `error_recovery` (call
immediately after a failed call), `post_success` (after the frozen
completion proxy), `pre_first_edit`.

## 3. Redundancy rules (conservative, deterministic)

Normalization: strip the run workdir prefix (`/tmp/pi-prompt-benchmark/
slot-*/`) from paths and commands; collapse whitespace; drop leading
`cd <workdir> && `.

- `duplicate_command`: identical normalized bash command re-run with **no
  intervening code_edit anywhere in the run** since its last execution.
- `repeated_read`: same normalized file path read again with **no
  intervening edit to that same path**.
- `post_green_repeat_test`: a test_execution whose normalized command
  already produced a fully-green result, re-run with no intervening
  code_edit.
- `abandoned_exploration` (proxy): file_read/file_search calls whose target
  path is never edited in the run AND is not adjacent to the final edit set
  (same directory); reported as a proxy, with the judge-level
  `unused_branches` mediator carrying the semantic attribution.
- Diagnosis reads, final validation, and first test runs are NEVER counted
  redundant by construction.

## 4. Cost decomposition (per run)

- **A. Model cost:** from the ledger (uncached input, cache read/write,
  output/reasoning; reported + no-cache reconstruction). Unchanged fields.
- **B. Direct tool cost:** counts, failed counts, per-category counts,
  wall-clock (CC: summed per-call durations; pi: run wall time and
  inter-turn deltas). **No dollar figure** — no tool in this benchmark has
  an external charge. Scenario pricing, if ever added, must be labeled as
  scenario, not measurement.
- **C. Tool-induced model cost:** est_result_tokens = result_chars/4.
  - direct measurement (both harnesses): per-turn logical-input growth
    (turn t's input+cacheRead+cacheWrite minus turn t-1's) attributable to
    the previous turn's tool results + assistant output; reported at run
    level.
  - lower bound: sum over calls of est_result_tokens x (1 x input_price +
    max(0, turns_after - 1) x cache_read_price)
  - upper bound: sum of est_result_tokens x turns_after x input_price
    (no-cache re-transmission).
  Exact per-turn billing attribution is impossible because a turn's input
  mixes tool results, assistant output, and harness scaffolding; bounds and
  the direct growth measurement are reported instead.
- **D. End-to-end:** total cost/run and per compliant success; latency;
  tool calls; redundant calls and their induced-cost share; post-success
  calls; abandoned-exploration calls. Dollars, latency, and local compute
  are reported as separate dimensions, never merged.

## 5. Frozen hypotheses

- H-T1 multiple_approaches: ↑ exploratory calls (file_read/file_search,
  esp. abandoned_exploration) with no increase in implemented approaches
  (semantic `alternatives_implemented` stays +1) and no success gain.
- H-T2 deep_thinking: incremental cost is predominantly token cost;
  tool-call counts and category mix approximately unchanged.
- H-T3 max_certainty: ↑ post_green_repeat_test and duplicate_command;
  post-success calls carry the induced-cost increase.
- H-T4 misleading_architecture: ↑ pre_first_edit calls, failed calls,
  abandoned_exploration; tool activity concentrates before the first edit.
- H-T5 bounded_efficiency: ↓ redundant categories, unchanged
  diagnosis/test/validation counts, unchanged success.
- H-T6 harness: CC vs pi differ in tool composition (shares of
  test_execution, navigation, error_recovery, repeated reads), not only
  reasoning composition.

## 6. Statistical design

Paired within task x model x harness x experiment block vs precise
baseline (same machinery as the main benchmark): per-task deltas/ratios,
median across tasks, task-clustered bootstrap 95% CI, plus a paired
sign-flip permutation test (10,000 resamples) on per-task median deltas.
Primary economic endpoint: **no-cache cost per compliant success**
(billing-policy independent); reported cost secondary. Count variables:
report zero fraction and max alongside medians (zero inflation, heavy
tails); no Pearson-only claims. Mediation (condition -> unused branches ->
exploratory calls -> cost) is presented as a descriptive decomposition
only; no formal causal-mediation claim.

## 7. Validation

Deterministic layer: unit tests for normalization, duplicate detection,
repeated-read, post-green rules; researcher-blind manual labels on a
stratified sample of calls before viewing classifier output; agreement
reported. Judge-derived fields reuse the validated semantic annotations
(no new judge pass); deterministic and judge-derived fields are reported
separately. Outlier inspection: Inkling write/delete cycles, K2.6
re-derivation spiral, post-green loops, large repeated reads,
malformed-call recovery.
