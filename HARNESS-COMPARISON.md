# Harness Comparison: PI.DEV vs Claude Code on Together AI models

**Final (Phases 1+2 complete).** Compatibility and metadata-preservation
findings (§2–§4, §6) are direct measurements; the behavioral comparison (§5)
now includes pilot + screening data (see RESULTS.md for holdout-confirmed
prompt effects per harness). One open item: replication on a second
gateway/region.

How the same six Together AI models behave on the same tasks and user prompts
when operated by PI.DEV 0.82.1 (direct) versus Claude Code 2.1.220 (through a
protocol gateway). Data: pilot runs in results/runs.jsonl; calibration in
PI_HARNESS_OVERHEAD.md / CLAUDE_CODE_HARNESS_OVERHEAD.md; compatibility
evidence in results/compatibility/.

## 1. Integration method

```
claude -p … --model benchmark-<alias>
  → capture proxy :8903      (Anthropic-side stream, redacted)
  → LiteLLM 1.93.0 :4000     (Anthropic Messages → OpenAI chat completions)
  → capture proxy :8901      (Together-side stream, redacted)
  → api.together.xyz
```

Aliases map 1:1 to exact Together model IDs (benchmark/gateway/litellm.yaml,
secrets via environment). Claude Code runs with an isolated per-run HOME,
`--permission-mode acceptEdits`, `--max-turns 40` (80 in Phase 2), non-essential traffic
disabled, and `ANTHROPIC_SMALL_FAST_MODEL` pinned to the same alias so every
request in a run hits the same upstream model (validated per run from capture).

## 2. Compatibility (empirical, three gateway routes attempted)

| route | tool loop result |
|---|---|
| LiteLLM `openai/` → **/v1/responses** | 3/6 pass; GLM-5.2, DeepSeek-V4-Pro, Inkling return **empty continuations** after tool results (reasoning items not replayed) — `protocol_translation_failure`, not model failure |
| LiteLLM `together_ai/` + `drop_params: true` | 0/6 — LiteLLM **silently dropped all 24 tool schemas** (models never saw tools) |
| LiteLLM `together_ai/` + `model_info.supports_function_calling: true`, no drop_params | **6/6 pass** the full 14-capability suite (final configuration) |

Full matrices: results/compatibility/cc_compat.md (+ preserved failed-route
records). Lesson: a text response proves nothing; only the empirical
multi-step tool loop counts (design §3), and gateway defaults can invalidate a
benchmark silently.

## 3. Metadata preservation (H16 — confirmed)

| field | Together upstream | visible to Claude Code |
|---|---|---|
| input/output token totals | ✓ | ✓ (sums match capture exactly) |
| `reasoning_tokens` | ✓ explicit, all 6 models | ✗ dropped by the gateway |
| `cached_tokens` | ✓ explicit | ✗ re-derived/zeroed in translation |
| cost | n/a (computed) | ✗ `total_cost_usd` uses Claude Code's own price table for the alias — measured $0.17 reported vs ≈$0.05 actual |

Authoritative metrics for claude-code runs therefore come from the
Together-facing capture at catalog prices (`upstream_reasoning_tokens`,
`reasoning_metadata_preservation: dropped` recorded per run).

## 4. Fixed prefix (harness treatment, not model property)

Claude Code sends ≈6.7 KB system prompt + **24 tool schemas** ≈ 16–20k tokens
per request; pi sends ≈0.4k system prompt + 4 tool schemas ≈ 1.1–1.6k tokens —
**12–15× across every tokenizer** (tables in the two overhead reports). Every
extra agent turn re-transmits the whole prefix, so turn count multiplies the
prefix difference.

## 5. Matched behavioral comparison (pilot, shared cells)

Same tasks (py-low-01, js-med-03, js-high-01), same prompt variants, same
fixtures, evaluators, and timeouts. `analysis/build_report.py harness`
regenerates this table from runs.jsonl:

| model | harness | n | success | reasoning (med) | tool calls | turns | logical input | reported $/success | no-cache $/success | wall s |
|---|---|---|---|---|---|---|---|---|---|---|
| DeepSeek-V4-Pro | claude-code | 6 | 100% | 788 | 14.0 | 15 | 257764 | 0.1088 | 0.4625 | 70 |
| DeepSeek-V4-Pro | pi | 36 | 100% | 384 | 5.0 | 5 | 14740 | 0.0167 | 0.0316 | 25 |
| Kimi-K2.6 | claude-code | 2 | 100% | 21730 | 62.5 | 40 | 958854 | 0.3342 | 1.2698 | 162 |
| Kimi-K2.6 | pi | 36 | 100% | 662 | 6.0 | 6 | 12242 | 0.0206 | 0.0409 | 8 |
| Kimi-K2.7-Code | claude-code | 18 | 100% | 516 | 8.5 | 10 | 133706 | 0.0482 | 0.1715 | 14 |
| nemotron-3-ultra-550b-a55b | claude-code | 9 | 100% | 1026 | 40 | 41 | 825277 | 0.3207 | 0.4140 | 54 |
| nemotron-3-ultra-550b-a55b | pi | 36 | 100% | 508 | 7.0 | 7 | 20348 | 0.0176 | 0.0176 | 11 |
| Inkling | claude-code | 19 | 100% | 309 | 10 | 11 | 190051 | 0.0758 | 0.2457 | 15 |
| GLM-5.2 | claude-code | 2 | 100% | 862 | 35.5 | 36 | 641866 | 0.2723 | 0.9104 | 185 |
| GLM-5.2 | pi | 36 | 100% | 640 | 6.0 | 6 | 13704 | 0.0301 | 0.0438 | 24 |

(Medians over pilot cells; screening-scale prompt effects per harness are in results/summaries/prompt_sensitivity_screening.csv.)

Findings (pilot-scale for §5 rows; see banner):

1. **Success parity, radically different cost.** Both harnesses solved the
   matched pilot cells at ≈100%, but Claude Code cost **5–30× more per
   success** (nemotron: $0.30 vs $0.009). The driver is turns × prefix:
   CC's loop takes 10–41 API rounds where pi takes 5–7, and each round
   re-sends a 12–15× larger prefix.
2. **Model × harness interaction (H12) is real.** Kimi-K2.7-Code stays tight
   under CC (10 turns); GLM-5.2, Kimi-K2.6, and nemotron thrash toward the
   40-turn ceiling on the same tasks they solve in ≤7 turns under pi.
   10/100 CC pilot runs hit the `--max-turns 40` ceiling (still passing the
   evaluator) — their turn/cost figures are right-censored.
3. **Reasoning tokens do not follow a single harness direction.** Under CC,
   DeepSeek reasons *less* (900 vs 1,345) while Kimi-K2.6 reasons *more*
   (8,645 vs 3,280) than under pi — reinforcing that reasoning effects must
   be analyzed within model × harness, never pooled.
4. **Cache behavior differs by harness and model.** CC runs get first-turn
   hits almost universally (the static 16–20k prefix stays hot across runs);
   via pi, nemotron got **zero** cache reads across 30 pilot runs while all
   other models cached normally — a provider-side, model-specific anomaly.
   Cache rebates cut CC's actual bill by ~60% (still net far more expensive
   than pi).

## 6. Gateway retries and artifacts

`num_retries: 0` is pinned in the gateway; capture shows no hidden retry
requests in the pilot. The known artifacts are the metadata drops (§3) and
Claude Code's `contextWindow: 200000` assumption for aliased models (wrong for
262k/512k models; harmless in the pilot because runs stayed far below it).

## 7. Limitations

- Pilot B was budget-capped at 100/252 planned runs; the shared spend pool
  favored fast, cheap models (K2.7-Code and Inkling completed all cells;
  GLM-5.2 got 5). Per-model budget pools are the fix for screening.
- One gateway (LiteLLM) was tested; a different translator could preserve
  metadata or induce different loop behavior.
- CC turn counts are right-censored at 40 for a tenth of runs.
- Normalized-harness comparison (design §9) not yet run — the real-default
  comparison came first.
- All caveats about cross-model token comparability apply (tokenizers differ).
