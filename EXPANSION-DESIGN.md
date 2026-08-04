# Expansion design (separately preregistered replication)

The original study (4,644 valid runs; commits through 6110bdb) stays frozen
and is reported as the original study. Expansion runs carry experiment tags
`exp_*` and are never merged into original preregistered results.

## Arms

| Arm | Purpose | Matrix | Est. runs |
|---|---|---|---|
| exp_paraphrase (E11, E12) | semantic vs lexical vs length vs position | 25 prompt arms (frozen manifest) x 6 pilot tasks x 3 models (GLM-5.2, Kimi-K2.6, DeepSeek-V4-Pro) x 3 reps, pi | ~1,350 |
| exp_stability (repetition) | within-cell variance, direction-reversal prob. | 9 variants x 16 dev tasks x 2 models (GLM-5.2, Inkling) x +3 reps, pi | ~864 |
| exp_newtasks (E1-E10 generalization) | 24 authored tasks: multi-file fixes, refactors, test repair, spec implementation, misleading failures, dependency/config, navigation-heavy, single- vs broad-solution, short vs LONG-VALIDATION family (slow suites, repeated builds, large reads) | x 9 variants x 6 models x 2 reps, pi; CC arm on 8 tasks x 4 variants x 6 models | ~2,592 + ~432 |
| exp_holdout2 | frozen second holdout, 16 unseen tasks | x 4 variants x 6 models x 1 rep, pi | ~384 |
| exp_judge | semantic annotation of new traces (frozen rubric v1, primary judge only) | batch | ~1,500 calls |

Task properties recorded per new task: repo size, relevant-file count,
baseline tool calls, baseline test duration, difficulty tier, expected
solution breadth, natural multi-approach plausibility, misleading-surface
flag. New-task fixtures must fail visible tests pre-fix; hidden evaluators
never enter workspaces (unchanged).

## Instrumentation deltas (validated before campaign)
Addable WITHOUT harness-behavior change: normalized command+args (already),
stdout/stderr byte counts (already), tool-result token estimates (already),
per-call CC timestamps (already), per-turn cache read/write (already),
baseline test duration per task (new, measured at fixture build), repo
state hash before/after run (new, evaluator-side). NOT addable without
changing harness behavior (documented, excluded): pi per-call timestamps,
CPU/GPU/memory per call, mid-run repository hashes, mid-run
hidden-evaluator checks (would leak evaluator).

## Stages & budget caps
1. Instrumentation validation (unit tests + 3 smoke runs) - $1
2. Smoke: 1 run/arm-type - $2
3. Variance pilot: exp_stability arm - cap $30
4. Main: exp_paraphrase + exp_newtasks - cap $220
5. Frozen holdout2 - cap $25
6. Judge batches - cap $30
Total cap $308. No condition-aware inspection between stages beyond frozen
stop rules (validity rate, spend, infra errors). No early stopping on
attractive results.

## Statistics
Paired within task x model x harness x provider blocks as before; per-model
AND pooled; bootstrap CIs; sign-flip permutation; zero-inflated counts via
randomization tests; FDR (Benjamini-Hochberg, q=0.10) over secondary
endpoints with E1-E12 primaries kept separate; repetition stability =
P(paired-effect sign reverses across rep subsets); paraphrase decomposition:
variance components across semantic condition / lexical form / length
control / position (hierarchical bootstrap).
