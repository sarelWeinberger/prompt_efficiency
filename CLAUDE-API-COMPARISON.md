# Claude-API study — the reversal experiment

**Question.** The main benchmark measured prompt-family waste on six open-weight
models served by Together AI, driven through pi and through Claude Code via a
translation gateway. This post-registration study runs the *opposite* setup:
both harnesses against the **first-party Anthropic API** (`claude-sonnet-5`),
with Claude Code in its native environment (no gateway, no model aliasing) —
and asks whether the prompt-family effects found on open models carry over to a
frontier closed model on its home stack.

**Scale.** 162 runs (108 pi + 54 Claude Code native), 9 prompt families,
6 frozen pilot tasks (3 for CC), 2 reps; 162/162 valid. Spend: $8.81 billed /
$34.31 no-cache. Protocol frozen before results (commit `028a2d3`).

## Measurement constraint (preregistered)

The Anthropic API **does not report thinking tokens separately** — thinking is
billed inside `output_tokens` (`reasoning_token_status =
included_in_output_but_not_separable`, the §12 taxonomy category). The frozen
primary metric is therefore the **paired total-output-token ratio** vs each
model's own baseline. This is defined identically on both providers: Together's
`completion_tokens` also includes reasoning tokens. It aggregates deliberation
+ response, so it is *diluted* relative to the reasoning-only ratios in the
main benchmark — a 2.7× output ratio implies a larger underlying deliberation
multiplier.

## Results — claude-sonnet-5 vs the six open models, same tasks, same metric

Median paired output-token ratio (task-clustered bootstrap 95% CI); "open-6
range" is the per-model median range for the same variant/harness/tasks from
screening data.

### pi (6 tasks × 2 reps per cell)

| Variant | Sonnet 5 | 95% CI | Open-6 range | Verdict |
|---|---|---|---|---|
| multiple_approaches | **2.70×** | [2.14, 3.86] | 2.12–4.03 | wasteful — inside the open-model range |
| exhaustive_exploration | **1.90×** | [1.22, 2.04] | 1.32–1.62 | wasteful — *above* every open model |
| max_certainty | **1.68×** | [1.22, 2.51] | 1.29–1.69 | wasteful — top of the open range |
| adjacent_cleanup | 1.32× | [0.94, 2.17] | 1.25–2.24 | elevated, CI spans 1 |
| deep_thinking | 1.30× | [1.04, 1.46] | 1.42–1.99 | elevated — *below* every open model |
| verbose_repetition | 1.10× | [0.76, 1.16] | 0.63–1.09 | neutral |
| bounded_efficiency | 1.02× | [0.74, 1.07] | 0.57–1.14 | neutral |
| no_questions_autonomy | 0.97× | [0.78, 1.05] | 0.63–1.06 | neutral |

### Claude Code native (3 tasks × 2 reps per cell)

| Variant | Sonnet 5 | 95% CI | Verdict |
|---|---|---|---|
| max_certainty | **4.13×** | [1.42, 8.57] | wasteful — Sonnet's worst family under CC ($1.12 vs $0.41 no-cache per success, 2.7× cost) |
| multiple_approaches | **2.52×** | [1.73, 3.48] | wasteful |
| adjacent_cleanup | **1.58×** | [1.29, 2.18] | wasteful |
| exhaustive_exploration | 1.52× | [1.08, 1.73] | elevated |
| deep_thinking | 1.25× | [1.00, 5.61] | elevated, wide CI |
| no_questions_autonomy | 0.98× | [0.85, 1.07] | neutral |
| bounded_efficiency | 0.93× | [0.77, 1.13] | neutral |
| verbose_repetition | 0.84× | [0.74, 1.09] | neutral |

Open-model CC comparators exist only for the variants screening_cc covered
(deep_thinking 0.95–4.64×, exhaustive_exploration 1.12–4.17×,
bounded_efficiency 0.29–2.09×, no_questions_autonomy 0.76–5.59×) — Sonnet sits
inside every one of those ranges.

## Findings

1. **Frontier ≠ immune.** The same prompt families that waste tokens on open
   models waste tokens on claude-sonnet-5 through the first-party API.
   `multiple_approaches` is again the reliable offender on both harnesses
   (2.5–2.7×), landing inside the open-model range. The main benchmark's #1
   rule transfers unchanged.
2. **`max_certainty` is the frontier-specific hazard.** On open models,
   certainty pressure was mostly a DeepSeek quirk (1.85×). On Sonnet 5 under
   native Claude Code it is the single worst family measured in this study
   (4.13×, 2.7× no-cache cost per success): the model buys extra verification
   loops — more turns, more tool calls, more re-checking — exactly what an
   agentic harness lets it do.
3. **Adaptive thinking absorbs "think deeply" better than open reasoners.**
   `deep_thinking` — confirmed wasteful on 5/5 open models — is the *smallest*
   elevated effect on Sonnet 5 (1.25–1.30×, below every open model on pi).
   Anthropic's adaptive thinking appears to damp explicit thinking
   incantations that fixed-reasoning open models obey literally.
4. **The neutral set replicates exactly.** Verbose repetition ≈1× (prompt
   length ≠ cost), autonomy language ≈1× (the screening non-replication holds),
   bounded-efficiency framing free (0.93–1.02×) but — unlike GLM-5.2's 0.48× —
   no active saving.
5. **Perfect scope compliance.** 162/162 runs scope-compliant-successful,
   including `adjacent_cleanup`, which caused out-of-scope edits on open
   models. On these tasks Sonnet 5 read scope-expanding language without
   acting beyond scope.
6. **Harness economics persist on the frontier stack.** Same model, same
   tasks: CC-native baseline ≈ $0.41 no-cache per success vs pi ≈ $0.027 —
   ~15×, consistent with the 5–30× found on open models. The harness choice
   still dwarfs every prompt effect.
7. **Anthropic caching rebates more than Together's.** 69% (pi) / 75% (CC)
   billing reduction vs ~61% on Together — despite the 1.25× write premium,
   which pi pays on every cold session. Same standing rule: a rebate, not
   efficiency; behavioral metrics were identical.

## Caveats

- Small post-registration study (n=162, 6/3 tasks): CIs are wide
  (CC `max_certainty` [1.42, 8.57]); direction is what's tested, not precise
  magnitudes.
- Output-token ratios under-state deliberation multipliers (response tokens
  dilute the denominator); Claude-side effects are lower bounds on the
  thinking-level effect.
- One frontier model at one price point (intro $2/$10 per MTok); results say
  nothing about Opus/Haiku tiers.
- Open-model CC comparators cover only the four screening_cc variants.

Data: `results/summaries/claude_api_comparison.csv` (76 rows,
Sonnet + 6 open models, both harnesses). Analysis:
`analysis/claude_api_comparison.py`.
