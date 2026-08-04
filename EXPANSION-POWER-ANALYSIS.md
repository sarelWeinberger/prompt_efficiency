# Expansion power & coverage analysis (pre-launch)

Method: bootstrap simulation on observed per-task paired deltas from the
completed screening (192 pooled blocks per variant = 6 models x 16 tasks x 2
reps), heavy-tail aware (resampled medians, not normal approximations).
Script: analysis snippet archived in repo history; endpoints: no-cache cost,
reasoning tokens, tool calls, post-success calls, post-green repeats.

## Findings

| Endpoint (variant) | observed paired median | 95% CI width now | half-width as % of effect |
|---|---|---|---|
| cost (multiple_approaches) | +$0.0135 | $0.0038 | 14% |
| cost (max_certainty) | +$0.0069 | $0.0021 | 15% |
| reasoning tokens (multiple_approaches) | +770 | 262 | 17% |
| post_success_calls (max_certainty) | +2.0 | 0.5 | 12.5% |
| post_green_repeat_tests | median 0 (94% zeros) | -- | rare-event: precision limited by zero inflation, not n |

**Conclusion: pooled primary effects are already adequately precise
(half-width <= 25% of effect, our frozen precision target). Halving CI
widths would need 4.8-50x more identical blocks (up to 9,731 for
zero-inflated counts) and buys little.** The expansion is therefore designed
for COVERAGE, not more of the same cells:

1. Paraphrase generalization (E11-E12): zero existing data - the largest
   evidence gap.
2. Task generalization + harder/longer-validation tasks: 16 dev tasks now;
   external-validity gap.
3. Repetition stability: 2 reps/cell cannot estimate direction-reversal
   probability; >=5 reps needed on a designed subset.
4. Per-model precision: 32 blocks/model/variant -> CIs ~2.4x wider than
   pooled; new tasks fix this jointly with (2).

## Justified target

~5,600 new valid runs -> ~10,250 total valid (meets the >=10,000 guideline
via designed coverage, not repetition of saturated cells):
- Paraphrase arms: 25 prompt arms (5 conditions x 4 paraphrases + 4
  length/position controls + baseline) x 6 tasks x 3 models x 3 reps ~ 1,350
- Repetition-stability arm: 9 variants x 16 tasks x 2 models x +3 reps ~ 864
- New tasks: 24 authored tasks x 9 variants x 6 models x 2 reps (pi) ~ 2,592
  + Claude Code arm ~ 432
- New frozen holdout: 16 tasks x 4 variants x 6 models ~ 384

Budget estimate (from observed per-run costs): Together ~$200-260 billed
(pi-dominated) + ~$25-40 Claude Code arms + ~$25 judge annotation of new
traces => ~$250-325 total. Stop rules: per-stage caps below; no early stop
on attractive results.
