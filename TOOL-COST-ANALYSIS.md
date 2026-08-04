# Tool-cost analysis — from reasoning waste to end-to-end cost

**Research question.** Do waste-inducing prompt formulations raise total agent
cost only through reasoning tokens and turns, or also through the tools that
reasoning causes the agent to invoke — more calls, costlier categories,
repeats, larger outputs fed back into context, extra turns, more wall-clock?

Causal chain under test: prompt wording → reasoning mechanism → tool
behavior → end-to-end cost. Protocol frozen pre-analysis at commit `e9430aa`
(`benchmark/tool_cost_rubric.md`); analysis covers **4,644 valid runs**
(every run with a retained trace; zero skips), including claude-sonnet-5 in
deterministic tool-level analyses only.

## 1. Telemetry inventory (Phase 1, read-only audit)

See rubric §1 for the full field table. Summary: both harnesses record tool
name, full arguments, error flags, full result contents, and per-turn/
per-call model usage (input, output, cache read/write). Claude Code records
per-record ISO timestamps → **per-call durations recoverable**; pi records
turn-level timestamps only → per-call duration missing (inter-turn bounds
only). **No tool in this benchmark carries a direct monetary charge** — all
invocations are local (bash, read, edit, write); no paid search/API/CI was
used, so no dollar figure is reported for local compute (counts + wall-clock
instead). Not recoverable: CPU/GPU time, peak memory, per-call file-state
snapshots, and the hidden-evaluator mid-run completion point (hidden tests
never entered workspaces; the frozen operational proxy is *last edit AND
first fully-green visible test*). claude-sonnet-5 remains excluded from all
reasoning-trace claims (no thinking text is returned by the API).

## 2. Headline: the two dominant waste mechanisms have different cost carriers

Joining judge-annotated mechanisms (validated in the semantic study) to
deterministic tool metrics, per run (medians; success is flat across all
levels, 0.86–0.97):

| Mechanism level | n | tool calls | no-cache $ | wall s |
|---|---|---|---|---|
| unused_branches = 0 | 1,934 | 7 | 0.020 | 11.6 |
| unused_branches = 1 | 354 | 8 | **0.038** | 22.2 |
| unused_branches ≥ 2 | 513 | 8 | 0.035–0.039 | 24.6–27.7 |
| redundant_verification = 0 | 1,585 | 6 | 0.019 | 11.4 |
| redundant_verification = 1 | 835 | 8 | 0.028 | 17.3 |
| redundant_verification = 2 | 168 | 9 | 0.044 | 20.6 |
| redundant_verification = 3+ | 213 | **15** | **0.341** | **35.3** |

- **Unused branches are token-borne.** The first discarded branch doubles
  run cost while tool calls stay ~flat (7→8), and the effect *plateaus* —
  more branches add words, not work. The tournament happens in the model's
  head, not in the repository (on these ≤4-file tasks).
- **Redundant verification is tool-borne and escalates.** Cost rises
  monotonically to 18× baseline at level 3+, carried by tool executions
  (6→15) and wall-clock (3×). This is the one mechanism that turns into real
  execution load.

This decomposition is descriptive (mediator strata, not formal causal
mediation; rubric §6).

## 3. Hypothesis verdicts (paired vs baseline; median across 6 open models [min,max]; sign-flip permutation p on per-task medians)

**H-T1 multiple_approaches — token-first, tools secondary.** Tool calls
+1.5 [+1.0,+2.75] (p≈.06); file reads +0.75; **code edits +0.0 on 6/6**;
abandoned-exploration calls +0.0; result tokens +224 (p=.024); no-cache cost
+$0.018/run (p=.022), of which the tool-induced component is ≤$0.0013 —
**the branch tournament is elaborated mentally, not explored via tools**, and
never becomes a second implemented approach (consistent with the semantic
+1.0 alternatives_implemented). Task-scale caveat: on larger repositories
branches may demand real exploration; untested here.

**H-T2 deep_thinking — confirmed: the cost is tokens.** Tool calls +1.0
(p=.26, ns); result tokens +79 (ns); category mix unchanged; the significant
cost increase (+$0.005/run, p=.03) is carried by reasoning/output tokens.
No meaningful extra tool execution.

**H-T3 max_certainty — confirmed: post-success verification load.**
Post-success calls +1.75 [+1.0,+2.5] (sign-consistent on 6/6 models); test
executions +1.0; post-green repeat tests +0 to +0.5 (p=.06); result tokens
+212 (p=.024); +4.1 s latency. The worst single loop in the corpus is this
mechanism: Kimi-K2.6 re-running an already-green suite 6 times
(`js-low-01_max_certainty_r2`).

**H-T4 misleading_architecture — direction supported, reasoning-dominated.**
Tool calls +1.75 [+0.5,+5.5]; failed calls +0.5; file reads +0.5. Modest
tool effects next to the 4.2× pre-edit *reasoning* inflation (semantic
study): a wrong hint mostly buys deliberation about the red herring, plus
some extra inspection of it.

**H-T5 bounded_efficiency — perfect tool-layer null (confirmed).** Every
redundancy metric +0.00 [0,0] (permutation p=1.0), AND test executions,
edits, and diagnosis counts unchanged, success unchanged. The efficiency
template removes nothing useful and adds nothing — at the reasoning layer
and the tool layer alike.

**H-T6 harness composition — confirmed.** Baseline tool-call composition:

| Group | mean calls/run | test share | read share | edit share |
|---|---|---|---|---|
| Claude Code / open-6 | 14.5 | **0.52** | 0.21 | 0.10 |
| Claude Code / sonnet-5 | 5.7 | 0.56 | 0.21 | 0.18 |
| pi / open-6 | 6.3 | 0.22 | **0.40** | 0.18 |
| pi / sonnet-5 | 3.5 | 0.38 | 0.33 | 0.29 |

Claude Code's tool profile is verification-dominated (half of all calls are
test executions); pi's is inspection-dominated. claude-sonnet-5 is
tool-frugal on both harnesses (2.6× fewer calls than open models under CC)
with a higher edit share — more of its activity is the change itself.
Failed-call outliers (77–79 failures/run) are all CC+GLM permission-friction
loops occurring across *different* variants — harness-caused, not
prompt-caused.

## 4. Cost decomposition (pi screening medians per run, open-6)

| Variant | reasoning tok | tool-result tok | induced $ (lo–hi) | no-cache $ | wall s | calls |
|---|---|---|---|---|---|---|
| baseline | 237 | 392 | 0.0006–0.0013 | 0.0144 | 9.9 | 6 |
| multiple_approaches | 1,108 | 606 | 0.0011–0.0026 | 0.0321 | 22.4 | 7 |
| deep_thinking | 538 | 478 | 0.0007–0.0018 | 0.0209 | 13.7 | 7 |
| max_certainty | 359 | 592 | 0.0010–0.0026 | 0.0228 | 13.9 | 8 |
| bounded_efficiency | 216 | 410 | 0.0006–0.0014 | 0.0151 | 9.4 | 6 |

Tool-induced model cost (result tokens re-entering context; bounds per
rubric §4C, exact per-turn attribution impossible because a turn's input
mixes tool results, assistant output, and harness scaffolding) is **4–9% of
run cost at baseline and ≤12% under every waste variant** on pi. Dollars,
latency, and call counts are reported as separate dimensions throughout —
never merged. Under Claude Code the induced share is larger in absolute
terms (more calls × bigger prefix re-reads) but the harness static prefix
still dominates (main benchmark finding, unchanged).

Zero-inflation disclosure (run level, n=4,644): duplicate_commands 82% zero
(max 77), repeated_reads 93% zero (max 21), post_green_repeat_tests 94% zero
(max 6), post_success_calls 60% zero (max 29), failed_calls 53% zero
(max 79). Medians understate tails; paired tests use per-task medians with
sign-flip permutation.

## 5. Validation

- 13 unit tests freeze the normalization, duplicate-command, repeated-read,
  post-green, and completion-proxy rules (`tests/test_tool_taxonomy.py`).
- Researcher-blind check: expected metric values hand-derived from two fully
  read traces before viewing classifier output; 11/12 fields matched, the
  one mismatch exposed a real extractor bug (TAP `# fail 0` misread as
  failure + 400-char truncation), fixed and re-validated 12/12.
- Outliers inspected: K2.6 6× post-green loop (max_certainty), Inkling
  write/delete reversal cycles (adjacent_cleanup; 4 cycles, all captured as
  code_edit + other_bash sequences), CC+GLM permission-friction loops
  (77–79 failed calls, variant-independent), top induced-cost runs
  (DeepSeek max_certainty go-high-02: $0.79 upper bound from repeated
  large file reads).
- Judge-derived fields (unused_branches, redundant_verification) reuse the
  semantic study's validated annotations; deterministic and judge-derived
  fields are never mixed in one metric.

## 6. Literature note (positioning; audited 2026-08-03)

- **When2Tool** (arXiv:2605.09252) shows models know *when* a tool call is
  necessary and proposes suppressing unnecessary calls (48% reduction).
- **CostBench** (arXiv:2511.02734) benchmarks cost-optimal *planning* and
  re-planning for tool-use agents in dynamic environments.
- **CATP-LLM** (arXiv:2411.16313) trains cost-aware tool *planning*.
- **Toward Efficient Agents** (arXiv:2601.14192) surveys efficiency levers
  (memory, tool learning, planning; context compression, RL rewards that
  minimize tool use).
- **CORVUS** (arXiv:2607.22711) reduces context cost of file-read
  observations in coding agents.
- **Not All LLM Reasoning Is Visible in the CoT** (arXiv:2607.22925) shows
  frontier models perform hidden computation beyond visible tokens —
  directly supporting our tier-5 treatment of claude-sonnet-5 and the
  limitation that recorded traces are the *emitted* deliberation record.

All six study *whether, when, or how cheaply an agent should call tools* —
the decision, planning, or context layer. Our contribution differs: we hold
the agent, model, and task fixed and vary only **user-prompt wording**,
showing it causally changes reasoning structure (branches, re-verification)
that in turn produces measurable — and mechanism-specific — downstream tool
execution and end-to-end cost. To our knowledge the prior work above does
not measure this prompt-wording → reasoning-structure → tool-cost chain; we
make no broader novelty claim.

## 7. What cannot be concluded

- No dollar cost of local compute (none is charged; none is fabricated).
- No CPU/GPU/memory accounting (never recorded).
- pi per-call durations unavailable (turn-level only).
- "Post-success" uses the frozen visible-test proxy; true hidden-evaluator
  mid-run satisfaction is unobservable without file-state replay.
- Exact per-turn billing attribution of tool results is impossible; bounds
  and direct context-growth measurements are reported instead.
- Small tasks (≤4 files) cap exploration demand: the "branches are
  token-borne" finding may weaken on repository-scale tasks where
  alternative approaches require real exploration.
- claude-sonnet-5: tool-level findings only; nothing about its reasoning.

## 8. Paper-ready additions

**Results subsection (proposed text).** "Joining the semantic annotations to
deterministic tool telemetry shows the two dominant waste mechanisms have
different cost carriers. Unused solution branches are token-borne: the first
discarded branch doubles run cost while tool calls stay flat, and the effect
plateaus — solution tournaments are elaborated in reasoning, not explored
through the repository. Redundant verification is tool-borne and escalates:
runs with 3+ redundant re-verifications execute 2.5× the tool calls, 3× the
wall-clock, and 18× the cost of clean runs, with identical success.
Prompt-level effects mirror this: certainty pressure adds post-success
verification activity on 6/6 models (+1.75 calls after the completion
point), while deep-thinking and multiple-approaches wording leave the tool
layer essentially unchanged and put their entire increment into tokens.
Bounded-efficiency wording is a perfect null at both layers. Tool-induced
model cost — tool results re-entering context — is bounded at 4–12% of run
cost under pi; the harness static prefix remains the dominant non-reasoning
cost. Tool composition is harness-shaped: half of Claude Code's calls are
test executions versus 22% under pi."

**Limitations addition (proposed text).** "Our tool-cost decomposition
carries no direct monetary tool charges (all benchmark tools are local), no
CPU/GPU accounting, and turn-level-only timing for pi. Post-success analyses
use a visible-test completion proxy. Per-turn billing attribution of tool
results is bounded, not exact. Task scale (≤4 files) limits exploration
demand, so the token-borne character of branch waste may not extend to
repository-scale tasks."

**Abstract/contribution update (proposed).** Append: "(7) joining semantic
annotations to tool telemetry, waste mechanisms split by cost carrier:
discarded solution branches are token-borne (cost doubles at the first
branch, tool activity flat), while redundant verification is tool-borne
(2.5× calls, 3× latency, 18× cost at its extreme) — so prompt-induced waste
is mostly cheap words, except certainty pressure, which buys real
execution."

## Artifacts

`results/summaries/tool_cost_run_level.csv` (4,644 rows),
`tool_cost_paired_effects.csv` (224), `tool_cost_by_mechanism.csv` (9),
`tool_cost_by_tool_type.csv` (43); scripts `analysis/tool_cost_extract.py`,
`analysis/tool_cost_analysis.py`; tests `tests/test_tool_taxonomy.py`;
frozen rubric `benchmark/tool_cost_rubric.md` (commit `e9430aa`). All fields
additive; no prior semantic or benchmark result was modified.
