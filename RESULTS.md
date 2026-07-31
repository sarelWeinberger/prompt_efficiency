# Benchmark Results — Prompt-Induced Waste in Large Reasoning Models

**Milestone status: preregistered program COMPLETE** (Phase 1 infrastructure +
pilot; Phase 2 full six-model screening, stress family, and frozen-holdout
confirmation). One preregistered item remains open: replication on a second
gateway/region (data collection did span three days, 2026-07-26→28, giving
partial temporal replication). Design: [EXPERIMENT-DESIGN.md](EXPERIMENT-DESIGN.md).
Regenerate tables: `analysis/analyze_results.py`, `analysis/holdout_confirmation.py`,
`analysis/build_report.py`.

## 1. Scope and validity

| | |
|---|---|
| Models | 6 frozen (DeepSeek-V4-Pro, Kimi-K2.6, Kimi-K2.7-Code, nemotron-3-ultra-550b-a55b, Inkling, GLM-5.2) |
| Harnesses | pi 0.82.1 direct; Claude Code 2.1.220 via LiteLLM 1.93.0 gateway (dual-side capture) |
| Valid runs | **4,400** — pilot 460, pi screening **1,728/1,728 (complete matrix)**, CC screening 371/480, stress 432/432, pi holdout **1,198/1,200**, CC holdout 211/270, cache sessions 70 |
| Excluded | 773 records: credit-exhaustion and session-interruption infrastructure failures, all re-run; zero contaminated task results in analysis |
| Reasoning tokens | explicit for all six models (`completion_tokens_details.reasoning_tokens`) |
| Cost | **$152.54 actual / $390.53 estimated no-cache** (cache rebated ~61%) |
| Success rates | pi screening 92%, pi holdout 97%, CC screening 87%, CC holdout 98% |

## 2. Holdout-confirmed findings (the headline table)

Frozen protocol (§22): top-3 waste features per model selected from screening
only, then run on 8 never-seen holdout tasks, 5 reps, vs baseline +
bounded_efficiency controls. pi side, n=40 per cell:

| model | multiple_approaches | deep_thinking | adjacent_cleanup | max_certainty | exhaustive_expl. | bounded_efficiency |
|---|---|---|---|---|---|---|
| DeepSeek-V4-Pro | **2.92× ✓W** | **2.12× ✓W** | — | **1.85× ✓W** | — | 0.97× ✓neutral |
| Kimi-K2.6 | **7.40× ✓W** | **2.21× ✓W** | — | — | 1.29× weaker | 1.06× ✓neutral |
| Kimi-K2.7-Code | **5.98× ✓W** | **1.86× ✓W** | — | — | — | 0.98× ✓neutral |
| nemotron-3-ultra | **2.44× ✓W** | **1.57× ✓W** | — | 1.48× weaker | — | 1.16× ✓neutral |
| Inkling | **5.08× ✓W** | — | **3.13× ✓W** | — | 1.39× not repl. | 1.04× ✓neutral |
| GLM-5.2 | **6.18× ✓W** | **2.18× ✓W** | **4.25× ✓W** | — | — | **0.48× ✓neutral** |

✓W = confirmed_wasteful (median ratio >1.5, CI lower bound >1.1, no success
gain, on unseen tasks). Full CIs: results/summaries/holdout_confirmation.csv.

1. **"Develop several approaches and compare before choosing" is the single
   most wasteful instruction tested** — confirmed on **all six models**, 2.4×
   to 7.4× reasoning tokens with zero correctness gain. It was not in the
   pilot; screening found it, holdout confirmed it everywhere.
2. **Deep-thinking cues confirmed wasteful on 5/5 models selected** (1.6–2.2×),
   replicating the pilot on unseen tasks — third consecutive dataset (pilot,
   screening, holdout) across three days.
3. **Adjacent-cleanup confirmed on Inkling (3.1×) and GLM-5.2 (4.3×)** — and
   remains one of only two features that produce out-of-scope edits.
4. **Bounded-efficiency confirmed neutral-or-better on all six models**; on
   GLM-5.2 it *halved* reasoning (0.48×) at equal success. Explicit scope +
   stop conditions are free everywhere and strongly positive on GLM.
5. **One honest non-replication**: no_questions_autonomy showed no reasoning
   effect on K2.7-Code holdout (1.00×) — its screening signal was noise; its
   real, replicated effect is scope violations, not tokens.

Claude Code holdout (3 tasks × 3 reps; all cells below the n≥10 power gate)
is directionally consistent: multiple_approaches 4.57×/3.00×/2.08× on
Kimi-K2.6/Inkling/K2.7-Code; GLM bounded_efficiency 0.29×. Reported as
directional support only.

## 3. Screening results (6 models × 16 dev tasks × 9 variants × 2 reps, pi)

Full table: results/summaries/prompt_sensitivity_screening.csv. Median
reasoning ratios vs paired baseline, classified per §24: `multiple_approaches`
ranked top waste feature for 5/6 models (screening was where it surfaced);
`deep_thinking` second nearly everywhere; `verbose_repetition` ≈1.0× on all
models (pure redundancy is free — the fixed prefix dwarfs it); scope-language
features remain the only source of out-of-scope edits (adjacent_cleanup and
no_questions_autonomy, 5-8% of runs; all others ~0%).

## 4. Stress family (separate analysis, never causal evidence for wording)

vs same-task screening baselines, median across 6 models (pi):

| stress condition | reasoning ratio | success | note |
|---|---|---|---|
| misleading_architecture | **2.61×** | 92% | false hints are the costliest input defect — models dutifully chase the red herring |
| ambiguous_scope | 1.44× | **83%** | worst success rate in the benchmark (H5 supported) |
| full_restatement_per_turn | 1.38× | 96% | restating everything each turn costs ~40% more reasoning |
| split_across_turns | 1.31× | 92% | splitting one task over two turns costs ~30% |
| conflicting_constraints | 1.05× | 100% | models just pick a lane — surprisingly free |
| irrelevant_context | 1.03× | 92% | distractor prose is ignored almost perfectly |

## 5. Hypothesis scoreboard (final)

- **H1 deep-thinking — CONFIRMED (holdout)** on every model where selected.
- **H2 exhaustive exploration — model-specific, weak**: replicated weaker on
  Kimi-K2.6 (1.29×), not replicated on Inkling; GLM's screening effect did not
  make its holdout top-3. Real but second-order.
- **H3 scope expansion — CONFIRMED (holdout)** for adjacent_cleanup on
  Inkling/GLM reasoning + scope violations everywhere it appears.
- **H4 bounded prompting — CONFIRMED (holdout, all six models).**
- **H5 ambiguity — SUPPORTED (stress)**: worst success (83%) + 1.44× reasoning.
- **H6 cache-cost divergence — CONFIRMED**: ~61% billing rebate at zero
  behavioral difference across 4,400 runs.
- **H7 complexity scaling — PARTIAL**: high-complexity tasks show larger
  absolute excess reasoning but similar ratios; no clean interaction.
- **H8 fixed-overhead dominance — CONFIRMED (measured)**: pi prefix 1.1–1.6k,
  CC prefix 16–20k tokens (12–15×), user prompt <5% / <1% of logical input.
- **H12 harness interaction — CONFIRMED**: same prompt flips effect direction
  across harnesses (goal_only ↓ under CC, ambiguity ↑ under pi; turn counts
  5–7 vs 10–41).
- **H13 autonomy — REVISED**: scope-violation effect replicates (6-8% oos);
  reasoning effect does not (holdout 1.00×).
- **H14 CC planning overhead — SUPPORTED (screening)**: exploration cues cost
  4–4.8× under CC vs 1.1–2.4× under pi on matched cells; underpowered at
  holdout.
- **H16 gateway metadata loss / H17 retries — CONFIRMED / NOT OBSERVED**
  (direct measurement; num_retries pinned to 0, no hidden retries in capture).
- New finding (unregistered, exploratory): **multiple_approaches** — the
  strongest effect in the benchmark; treat as confirmed wasteful with the
  caveat that it was hypothesis-generating in screening, confirming in holdout.

## 6. Cache and cost accounting (final)

Together's automatic prefix caching rebated **~61%** of the would-be bill
($390 → $153) with zero behavioral effect. nemotron+pi received 0 cached
tokens across all phases (provider anomaly, persisted for three days); CC's
static 16–20k prefix stayed hot across sessions (first-turn hit rates ~90%+
for most models). Per-turn ledger: results/summaries/cache_behavior.csv.
All costs computed from provider-reported usage at pinned catalog prices;
Claude Code's own `total_cost_usd` is wrong for gateway models and never used.

## 7. Limitations

- CC holdout underpowered (per-model budget pools capped expensive models);
  verdicts directional only.
- 2/1,200 pi holdout cells missing (timeouts); 10% of Phase 1 CC runs
  right-censored at 40 turns (raised to 80 for Phase 2).
- Session interruptions split collection over three days — an accidental
  robustness check the pi findings passed (pilot→screening→holdout all
  replicate deep_thinking); still one region, one gateway, one provider.
- Tasks remain small (≤4 files); success ceilings persist for pi (92–97%).
- Single gateway (LiteLLM 1.93.0); §9 normalized-harness comparison not run.
- The §24 classification thresholds are configurable; CSVs carry CIs for
  re-analysis under different thresholds.

## Kimi 3 small replication (post-registration, 2026-07-28)

Targeted 6-task replication of the three headline prompt features on
`moonshotai/Kimi-K3` (protocol frozen before results; full report:
[KIMI3-SMALL-REPLICATION.md](KIMI3-SMALL-REPLICATION.md)).

- Compatibility: verified on both harnesses (pi tool loop 4/4; Claude Code
  14-capability suite passed); reasoning and cache fields explicit, same
  schema as the frozen six.
- Runs: pi 72/72 valid (100% success); Claude Code 9/24 (stopped by the
  pre-registered no-cache ceiling; directional only). Cost $4.46 actual /
  $28.43 no-cache.
- **Verdict: material difference — in sensitivity, not direction.**
  K3's baseline deliberation floor is ~6× lower (55 median reasoning tokens
  vs 351/195), so multiple_approaches hits **16.6×** [10.7, 34.1] and
  deep_thinking **14.8×** [4.1, 33.9] vs its own baseline — beyond the
  frozen 30%-vs-both threshold — while **absolute** waste tokens stay at or
  below K2-generation levels and cost per compliant success is the lowest
  of the three Kimi generations at baseline. bounded_efficiency: 0.89×
  [0.83, 0.94], confirmed neutral-to-beneficial. All classifications
  preserved; scope-compliant success 100%.
- Recommendations unchanged qualitatively; K3-specific note added to
  PROMPT-WASTE-RULES.md (prompt wording is the dominant lever on K3's
  reasoning spend).
- Thresholds, task rule, and matrix were frozen at commit b8aea7b before
  any result was viewed. Historical six-model results are untouched.

## Claude-API study (post-registration, 2026-07-31)

The reversal experiment: both harnesses against the **first-party Anthropic
API** (`claude-sonnet-5`), Claude Code running **native** (no gateway). 162
runs, 162 valid, $8.81 billed / $34.31 no-cache. Protocol frozen before
results (commit `028a2d3`). Full report: `CLAUDE-API-COMPARISON.md`.

Measurement note (preregistered): Anthropic bills thinking inside
`output_tokens` and never reports it separately, so the primary metric here is
the paired **total-output-token ratio** — defined identically on Together,
whose `completion_tokens` also includes reasoning.

Headline: **the prompt-family effects transfer to the frontier model.**
`multiple_approaches` wasteful again on both harnesses (2.5-2.7x, inside the
open-model range); `max_certainty` is Sonnet's worst family under native
Claude Code (4.13x, 2.7x cost per success); `deep_thinking` is *milder* than
on every open model (1.25-1.30x) - adaptive thinking absorbs the incantation;
the neutral set (verbose_repetition, autonomy, bounded_efficiency) replicates
at ~1x; 162/162 scope-compliant successes (no adjacent-cleanup scope breaks,
unlike open models); harness economics persist (~15x CC-native vs pi per
success); Anthropic caching rebates 69-75% vs Together's ~61%.
