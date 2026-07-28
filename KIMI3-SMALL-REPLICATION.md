# Kimi 3 Small Replication (post-registration)

Targeted replication testing whether `moonshotai/Kimi-K3` responds to the
three headline prompt features differently from Kimi-K2.6 and Kimi-K2.7-Code.
Protocol (tasks, variants, matrix, thresholds) frozen at commit `b8aea7b`
**before any K3 result was viewed**. Compatibility: [KIMI3-COMPATIBILITY.md](KIMI3-COMPATIBILITY.md).
Historical six-model results untouched.

## Execution

| | planned | valid | note |
|---|---|---|---|
| PI.DEV (6 tasks × 4 variants × 3 reps) | 72 | **72** | 100% success, zero failures |
| Claude Code (3 tasks × 4 × 2) | 24 | **9** | stopped by the pre-registered $24 no-cache ceiling after 9 runs (K3 CC runs average ≈$2.70 no-cache each); ceiling not raised, per protocol |
| Cost | — | **$4.46 actual / $28.43 no-cache** | pi $0.82/$4.11; CC $3.64/$24.32; K3's cache rebated 81% |

Reasoning tokens: explicit (`completion_tokens_details.reasoning_tokens`)
on both paths; cache: explicit; raw Together usage retained in
results/raw/ and the gateway capture.

## Primary comparison (pi, n=18/variant for K3; same 6 tasks; each model vs its own baseline)

| Metric | | Kimi-K2.6 | Kimi-K2.7-Code | **Kimi-K3** |
|---|---|---|---|---|
| multiple_approaches | reasoning ratio [95% CI] | 6.00 [2.38, 7.26] | 4.13 [0.16, 8.46] | **16.58 [10.75, 34.10]** |
| | absolute median (tokens) | 1,606 | 916 | **625** |
| | cost / compliant success | $0.0297 | $0.0240 | **$0.0178** |
| deep_thinking | reasoning ratio [95% CI] | 2.35 [0.74, 3.64] | 1.66 [1.36, 2.90] | **14.76 [4.07, 33.88]** |
| | absolute median (tokens) | 639 | 328 | **336** |
| | cost / compliant success | $0.0198 | $0.0125 | **$0.0155** |
| bounded_efficiency | reasoning ratio [95% CI] | 1.12 [1.06, 2.09] | 0.84 [0.69, 0.93] | **0.89 [0.83, 0.94]** |
| baseline | absolute median (tokens) | 351 | 195 | **55** |
| | cost / compliant success | $0.0076 | $0.0063 | **$0.0062** |
| scope-compliant success | all variants | 0.75–1.00 | 0.75–1.00 | **1.00 everywhere** |

Claude Code (9 valid runs — directional only, single-task cells): same
directions, larger ratios (multiple_approaches ≈66×, deep_thinking ≈11.8×,
bounded_efficiency 0.69×); CIs degenerate; excluded from formal verdicts
except as direction confirmation.

Full tables: results/summaries/kimi3_small_replication.csv,
results/summaries/kimi_generation_small_comparison.csv.

## Verdict against the frozen thresholds

**Material difference observed** — the paired reasoning ratio for
`multiple_approaches` (+176% vs K2.6, +302% vs K2.7-Code) and
`deep_thinking` (+529%, +792%) exceeds the frozen 30% threshold against
**both** comparators on pi, with the CC runs directionally consistent.

**What the difference is — and is not:**

- **It is a sensitivity difference, driven by a ~6× lower deliberation
  floor.** K3's baseline median is 55 reasoning tokens (vs 351 / 195) — it
  barely deliberates unless asked. Thinking-style cue-words therefore unlock
  proportionally enormous deliberation (15–17×).
- **It is not a direction flip and not an absolute-waste increase.** Every
  classification is preserved: multiple_approaches and deep_thinking remain
  `wasteful`, bounded_efficiency remains `neutral` (0.89×, its CI entirely
  below 1). In absolute tokens K3 wastes *less* than K2.6 under every waste
  variant, and its cost per compliant success is the lowest of the three
  generations at baseline ($0.0062) despite 2.5–3.3× unit prices.
- Scope-compliant success is 100% across all K3 cells — no quality trade-off
  in either direction (5pp threshold not crossed on pi).
- No new compatibility, reasoning-metadata, or cache issue: schema identical
  to the six frozen models; cache behavior consistent (81% rebate,
  cross-session prefix hits on first runs).

## Impact on recommendations

Qualitatively **unchanged** — the same phrases are wasteful, and
bounded-efficiency framing remains free. One K3-specific sharpening added to
PROMPT-WASTE-RULES.md: because K3's default deliberation is frugal,
prompt wording is the dominant lever on its reasoning spend — a single
deep-thinking sentence multiplies its reasoning ~15×, so prompt hygiene
matters proportionally more on K3 than on any model previously tested, even
though the absolute dollar impact stays moderate at current task sizes.

## Limitations

- 6 tasks, 3 reps, one day, one region; CC arm budget-capped at 9/24 valid
  runs (directional only).
- Ratio inflation from a small baseline denominator is inherent to
  normalized comparisons; absolute tokens and cost per success are reported
  alongside for that reason.
- K3's output price ($15/M) means absolute waste grows faster in dollars on
  longer tasks than these fixtures capture.
- Small-study rule applies: this is evidence about large practical
  differences on the tested features, not model equivalence.
