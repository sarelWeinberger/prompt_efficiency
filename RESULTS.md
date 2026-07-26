# Phase 1 Results — Infrastructure and Pilot Benchmark

**Milestone status: Phase 1 (completed infrastructure and pilot benchmark).**
The preregistered program is NOT complete: the full six-model screening
(§21 of the design brief), the frozen holdout confirmation, and the multi-turn
stress variants have not been executed. Every "confirmed" label below means
**confirmed at pilot scale** — a paired, CI-supported effect on the pilot
tasks — and still requires screening + holdout validation before it should be
treated as a final benchmark conclusion. See §8 for the remaining
preregistered work.

Results from the cost-bounded pilots defined in
[EXPERIMENT-DESIGN.md](EXPERIMENT-DESIGN.md). Regenerate every table with
`python3 analysis/analyze_results.py && python3 analysis/build_report.py`.

## 1. Scope and validity

| | |
|---|---|
| Models | 6 (frozen, benchmark/models.yaml); Pilot A used 4, Pilot B all 6 |
| Harnesses | pi 0.82.1 (direct); claude-code 2.1.220 via LiteLLM 1.93.0 gateway |
| Tasks | 24 built (8 low / 8 med / 8 high; py 9, js 9, go 6; 16 dev + 8 frozen holdout). Pilot A: 6 dev tasks; Pilot B: 3 dev tasks |
| Pilot A (pi) | **360/360 runs — full matrix** (4 models × 6 tasks × 5 variants × 3 reps), $6.45 reported |
| Pilot B (claude-code) | **100/252 runs — budget-capped** at $11.27 reported (cap $10 checked pre-run); coverage skewed to fast models (K2.7-Code 32, Inkling 32, nemotron 15, DeepSeek 10, Kimi-K2.6 6, GLM-5.2 5) |
| Experiment C (cache) | 70 session records across 6 models × 6 pi conditions + 2 CC conditions |
| Validity | **460/460 pilot records `valid`** — zero parse failures, zero infra failures, zero timeouts; 10/100 CC runs right-censored at `--max-turns 40` |
| Reasoning tokens | `explicit` for all 6 models (`completion_tokens_details.reasoning_tokens`; schema_discovery/) |
| Cost (all ledgers) | **$17.98 reported / $42.68 estimated no-cache**; cache rebates cut the actual bill by ~58% |
| Success | pi 99.7% (359/360); claude-code 99% (99/100). Δ-success cells in §3 are therefore ~0 almost everywhere: on these tasks extra reasoning bought nothing |

Thinking was enabled everywhere (`--thinking medium` for pi). Labeled caveat:
pi maps medium to `reasoning_effort: "high"` for DeepSeek only (PI_HARNESS_OVERHEAD.md).

## 2. Fixed overhead (H8 — directly measured calibration)

pi fresh-request prefix: 1,147–1,642 tokens; Claude Code: 15,983–20,330 —
**12–15× per request, on every tokenizer** (calibration reports). For low-complexity
tasks the user prompt is <5% of logical input under pi and <1% under Claude Code:
prompt length is a negligible cost driver; prompt *content* is not.

## 3. Prompt-variant effects (paired, within model×harness×task)

Median reasoning-token ratio vs paired baseline (Δ success), classification per
the §24 rule — **W** wasteful, **H!** harmful, · neutral, ? inconclusive:

### PI.DEV (full matrix; 18 baseline-paired runs per cell)

| variant | DeepSeek-V4-Pro | Kimi-K2.6 | nemotron-3-ultra | GLM-5.2 |
|---|---|---|---|---|
| deep_thinking | 1.81× (+0%) **W** | 2.82× (+0%) **W** | 2.12× (+0%) **W** | 3.22× (+0%) **W** |
| adjacent_cleanup | 1.30× (+0%) ? | 1.85× (+0%) **W** | 1.83× (+0%) **W** | 4.16× (+0%) ? |
| exhaustive_exploration | 1.43× (+0%) ? | 1.14× (+0%) · | 1.30× (+0%) ? | 2.40× (−6%) **W** |
| bounded_efficiency | 0.91× (+0%) · | 1.12× (+0%) · | 1.19× (+0%) · | 1.10× (+0%) · |

### Claude Code (partial coverage; treat ? cells as underpowered)

| variant | DeepSeek | Kimi-K2.6 | K2.7-Code | nemotron | Inkling | GLM-5.2 |
|---|---|---|---|---|---|---|
| deep_thinking | 2.47× ? | — | 2.19× **W** | 4.06× ? | 0.92× · | — |
| exhaustive_exploration | 1.14× ? | 4.03× ? | 4.83× ? | 4.41× ? | 1.45× ? | — |
| no_questions_autonomy | 1.36× ? | 1.03× ? | 3.23× ? | 3.54× ? | 0.83× · | — |
| goal_only | 0.76× ? | 0.23× ? | 1.41× ? | 0.37× ? | 0.26× · | — |
| scoped_authorization | — | 2.98× ? | 0.61× · | 1.36× ? | 0.67× (−20%) ? | — |
| bounded_efficiency | 0.41× ? | — | 12.91× ? | 2.81× ? | 1.15× · | — |

(The 12.91× K2.7-Code bounded_efficiency cell is a single thrashing run pair —
reported as inconclusive, not evidence against H4.)

## 4. Pre-registered hypotheses: pilot-scale status

"CONFIRMED (pilot)" = paired effect with CI support on the pilot tasks;
subject to screening + holdout confirmation. Nothing here is a final verdict.

- **H1 deep-thinking cues — CONFIRMED (pilot), the most consistent waste source.**
  Wasteful on 4/4 pi models (1.8–3.2×, CI lower bounds > 1.1, ≥4 tasks each,
  zero success gain) and on K2.7-Code under CC. Doubles wall time (11→18 s
  median) with identical tool behavior: pure reasoning burn.
- **H2 exhaustive exploration — model-specific (pilot).** Wasteful on GLM-5.2
  (2.40×, and the only pi variant that *lowered* success, −6%); +1 file
  inspected and +1 search command (median) everywhere; large but underpowered
  effects under CC (4–4.8× on three models).
- **H3 scope expansion — CONFIRMED (pilot) on behavior, partially on reasoning.**
  `adjacent_cleanup` is one of only two variants producing out-of-scope
  changes (6% of runs; `no_questions_autonomy` 7%; all others 0%), and is
  reasoning-wasteful on Kimi-K2.6 and nemotron.
- **H4 bounded prompting — CONFIRMED (pilot) as safe.** 0.91–1.19× reasoning at
  unchanged success on every pi model: explicit stop conditions and scope cost
  nothing (against an already-precise baseline they also save little).
- **H6 cache-cost divergence — CONFIRMED (pilot).** Cache hits changed billing by
  ~58% overall while reasoning tokens, tool calls, and logical input were
  unchanged (cache fields never enter the behavioral metrics).
- **H8 fixed-overhead dominance — CONFIRMED (pilot; calibration-backed)** (§2).
- **H12 harness interaction — CONFIRMED (pilot).** Same model, same task, same
  prompt: DeepSeek reasons *less* under CC than pi (0.9k vs 1.3k median)
  while Kimi-K2.6 reasons *more* (8.6k vs 3.3k); turn counts diverge 5–7 (pi)
  vs 10–41 (CC). Prompt guidance cannot be assumed to transfer across harnesses.
- **H13 autonomy cues — supported (pilot, small n).** `no_questions_autonomy` has the
  highest out-of-scope rate (7%) and 3.2–3.5× reasoning on two CC models.
- **H16 gateway metadata loss — CONFIRMED (measured directly; not sample-limited)** (HARNESS-COMPARISON.md §3).
- H5, H7, H14, H15, H17: insufficient pilot power — carried to screening.

## 5. Cache behavior (Experiment C + pilot; details in cache_behavior.csv)

- **Together's cache is real, automatic, and probabilistic** — reconfirmed at
  scale: 98–100% of pi runs for GLM/Kimi/DeepSeek saw hits; GLM alternated
  full/partial/none within identical conditions.
- **nemotron-3-ultra received 0 cached tokens in 96 pi runs** while caching
  normally through the Claude Code gateway (31% mean ratio) — a provider-side,
  model-and-route-specific anomaly. Do not budget on cache for nemotron+pi.
- **Cross-session prefix sharing at scale**: 32/32 K2.7-Code and 10/10
  Kimi-K2.6 CC runs got *first-turn* hits (~90–99% of the 16–17k prefix);
  fresh CC sessions are effectively pre-warmed by earlier ones.
- 60s-delayed follow-ups still hit (6/6 models with hits in the delayed
  condition, ratios 0.55–0.99) — no eviction observed at one minute; longer
  intervals untested.
- `changed_cwd` (pi) breaks prefix reuse as predicted (system prompt embeds
  the working directory).

## 6. Three strongest pilot findings

1. **"Think very deeply / verify repeatedly" is a money-burning no-op** on
   these tasks: 1.8–3.2× reasoning tokens on all four pi models, no
   correctness gain, ~2× latency. It is the only variant wasteful everywhere.
2. **The harness dwarfs the prompt.** Claude Code's 12–15× prefix × its 2–7×
   turn count makes the same model on the same task 5–30× more expensive per
   success than pi at equal success — and prompt effects flip direction
   between harnesses (H12). Optimizing prompt wording before harness/tooling
   choice optimizes the small term.
3. **Scope language, not thinking language, causes scope damage.** Only
   `adjacent_cleanup` and `no_questions_autonomy` produced out-of-scope edits;
   deep-thinking/exhaustive cues burned tokens but never widened the diff.
   Bounded-efficiency prompts were free insurance (≈1.0×, no success loss).

## 7. Limitations

- Pilot tasks are small and were solved at ~100% regardless of prompt —
  ceiling effects hide correctness differences; complexity-dependent waste
  (H7/Q7) needs the full 16-task screening with the holdout set.
- Pilot B under-covered GLM-5.2 and Kimi-K2.6 (shared budget pool; fix:
  per-model pools). CC turn metrics right-censored at 40 for 10% of runs.
- Multi-turn stress variants (split_across_turns, full restatement) not yet
  executed by runner v1.
- Single gateway (LiteLLM); single region/day; Together load varies.
- Cross-model reasoning comparisons are within-model normalized only.
- The §24 classification thresholds are provisional; prompt_sensitivity.csv
  carries CIs so alternative thresholds can be re-applied offline.

## 8. Remaining preregistered work (Phase 2+)

Phase 1 delivered the infrastructure and the pilots only. Still outstanding
from the preregistered design:

1. **Full six-model screening** — all 6 models × 16 development tasks ×
   selected variants × ≥2 reps, both harnesses (design §21/§18), with
   worst-case no-cache costing and run-count confirmation before launch.
2. **Frozen holdout confirmation** — per model, the 3 most waste-inducing
   features + baseline + bounded_efficiency on the 8 holdout tasks, ≥5 reps,
   with prompts/thresholds/evaluators/analysis code frozen beforehand (§22).
3. **Per-model Claude Code budget pools** — Pilot B's shared pool starved
   GLM-5.2 (5 runs) and Kimi-K2.6 (6); screening must budget per model.
4. **Longer Claude Code turn limits** — 10% of CC pilot runs were
   right-censored at --max-turns 40; screening should raise the ceiling (and
   record subtype) so turn/cost distributions are uncensored.
5. **Multi-turn stress variants** — split_across_turns and
   full_restatement_per_turn need runner v2 session support (pi -c /
   claude --resume) before the stress family can run.
6. **Replication across a different day, region, and/or gateway** — all
   Phase 1 data is one day, one region, one gateway (LiteLLM 1.93.0); cache
   and latency findings especially need temporal/geographic replication,
   and H16/H17 deserve a second translator implementation.

Also carried: H5/H7/H14/H15/H17 (underpowered at pilot scale), harder tasks to
break the ~100% success ceiling, the §9 normalized-harness comparison, the §14
permission-mode contrast, and cache-eviction timing beyond 60 s.
