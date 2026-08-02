# Advisor evaluation protocol — FROZEN before holdout results

Purpose: task-specific evaluation of `google/gemma-4-E2B-it` as a local
preflight prompt advisor that detects and reduces prompt-induced waste in
coding-agent prompts, built entirely from this repository's measured
prompt-waste results (RESULTS.md, PROMPT-WASTE-RULES.md,
CLAUDE-API-COMPARISON.md; benchmark state at commit `8d852da`).

## Frozen artifacts

| Artifact | Value |
|---|---|
| Dataset generator | `data/build_dataset.py` (deterministic, no RNG) |
| Dev set | `data/dev.jsonl`, 61 examples |
| Holdout set | `data/holdout.jsonl`, 105 examples, sha256 `7ff39ebf7f8e0c211699db8de5b0025be00230d1047688b0edd19c7f25aca6e1` |
| Output schema | `schema.json` (shared by all model systems) |
| Advisor prompt | `advisor/prompt.py` v2 |
| Rules baseline | `advisor/rules.py` (patterns from templates + dev only) |
| Scorer | `score.py` |
| Model under test | `google/gemma-4-E2B-it`, HF revision `3e22461f65e89153144f8adb70e3b8c2cc9845a7` |
| Primary quantization | official QAT `google/gemma-4-E2B-it-qat-q4_0-gguf`, revision `675cff42a74c774d6cb76f76d8eacb49b48c9b93` (`gemma-4-E2B_q4_0-it.gguf`, 3.10 GiB) |
| Inference engine | llama.cpp b10229 prebuilt ubuntu-x64 (`llama-server`), CPU backend |
| Generation params | temperature 0, seed 0, max_tokens 1400, thinking mode OFF (no `<|think|>`) |
| Hardware | Intel i7-1365U laptop (2P+8E, 12 threads), 32 GB RAM, no GPU; `-t 4 --parallel 1 --ctx-size 8192 --cache-reuse 256` |
| Secondary check | BF16 via transformers 5.14.1 / torch 2.12.0 CPU on a 20-example holdout subset (quantization-sensitivity only) |
| Reference judge | `claude-opus-5` via Anthropic API, structured outputs (`output_config.format` json_schema), default sampling (Claude 5 rejects temperature; judge is NOT bit-deterministic and is NOT treated as ground truth) |

## Systems compared on holdout

1. `rules` — deterministic regex + guards (no model)
2. `gemma` — Gemma-4-E2B-it alone, unconstrained decoding (JSON asked for in prompt)
3. `gemma-constrained` — same, with llama.cpp grammar-enforced JSON schema
4. `hybrid` — rules first; hard hit → warn from rules; no soft indicator → no_change;
   soft indicator without hard hit → Gemma (constrained). Composed offline
   from the rules and constrained-Gemma outputs (`compose_hybrid.py`),
   which is semantically identical to running the pipeline live; the
   model-call fraction is reported as the hybrid's latency profile.
5. `judge` — claude-opus-5, same prompt+schema (reference, not ground truth)

## Risk taxonomy → repo evidence mapping

`multiple_approaches`, `max_certainty` (includes "unbounded verification"),
`deep_thinking`, `exhaustive_exploration`, `adjacent_cleanup`,
`missing_stop_conditions` (ambiguous_scope stress family). Autonomy language,
verbose repetition, bounded efficiency framing, scoped authorization,
irrelevant context and goal-only prompts are labeled no_change per measured
results. `alt_ok` marks families acceptable as secondary flags where the
measured template itself mixes signals (deep_thinking ⇄ max_certainty).

## Metrics (definitions implemented in score.py)

Detection: displayed-warning precision (warn shown ∧ gold warn ∧ ≥1 grounded
family-and-span-correct risk), warn recall, neutral FPR, per-family P/R/F1
(span-grounded, overlap-with-gold-span required), micro/macro averages,
fabricated-span rate (evidence not a verbatim substring), abstention rate,
schema compliance, selective precision at confidence ≥0.5/0.7/0.9.
Paraphrase/mixed/Hebrew/legit-lookalike performance read from
per-category confusion.

Rewrite safety (deterministic): protected-item preservation (verbatim,
whitespace-normalized), critical-deletion rate, language preservation
(Hebrew-ratio check), rewrites-of-clean-prompts count, rewrite-offered rate.
Plus manual inspection of a stratified sample (all critical deletions, all
adversarial-category rewrites, ≥5 random successes) and a judge-assisted
read of meaning changes / unsupported additions. LLM-judge opinions are
reported separately from deterministic checks.

Deployment: model load time (cold/warm), RSS, prompt-processing and
generation tok/s (llama-bench + server timings), per-recommendation latency
and tokens, throughput at the measured settings, BF16-vs-Q4 agreement on the
subset, constrained-vs-unconstrained schema compliance, thinking-mode probe
(10-example subset with `<|think|>` on: latency vs any accuracy change).

## Decision thresholds (set before opening holdout results)

GO (direct user-facing warnings, standalone model):
- displayed-warning precision ≥ 0.95 on holdout
- neutral FPR ≤ 0.05
- fabricated-span rate ≤ 0.01
- schema compliance ≥ 0.98 (in the deployed configuration, i.e. constrained
  decoding counts)
- critical-deletion rate ≤ 0.02 among offered rewrites; language violations = 0
- warn recall ≥ 0.80 overall; recall ≥ 0.80 on repo-template
  multiple_approaches and max_certainty; ≥ 0.50 on paraphrases
- p50 end-to-end latency ≤ 3 s warm on this hardware for a warning-only
  response (rewrites may stream longer)

LIMITED GO: precision/compliance/rewrite-safety gates met only with the
hybrid architecture, confidence thresholding, or with rewrites disabled;
or latency exceeds the preflight budget so the advisor must run async.
NO-GO: precision or rewrite-safety gates unreachable under all variants;
then name the smallest next model/architecture to test.

Latency rationale: "preflight without noticeable delay" is interpreted as
p50 ≤ 3 s to a displayed warning (users tolerate a short spinner before an
agent run that itself takes minutes); full rewrites are allowed to stream.

## Dev/holdout hygiene

- Dev set used for: prompt iterations, rules patterns, triage keyword list.
- Holdout: authored before freeze, generated deterministically, evaluated
  once per system after this file is committed. No prompt/rules/schema edits
  after the first holdout run; any post-hoc analysis is labeled exploratory.
- The label refinement (`alt_ok`) and max_tokens 900→1400 change were made
  during dev iteration, before any holdout inference.

## Cost / end-to-end caveat (preregistered)

This study measures *semantic detection and rewrite safety* against labels
derived from measured token-waste effects. It does NOT measure end-to-end
cost savings of deploying the advisor (that requires running the downstream
coding agent on original vs rewritten prompts and comparing spend — a
follow-up experiment). Family-level risk is also harness- and
model-dependent (e.g. max_certainty is worst on Claude+CC, deep_thinking is
mild on Sonnet 5); the advisor reports the family so downstream policy can
weight by target harness.
