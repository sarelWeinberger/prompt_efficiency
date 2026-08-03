# Dev-set iteration log (exploratory — NOT holdout results)

All changes below happened before the protocol freeze and before any holdout
inference.

## Iteration 1 (rules baseline, scorer sanity)
- Rules v1 on dev: displayed precision 1.00, warn recall 0.92, neutral FPR 0,
  fabricated 0. The 3 misses are the dev adversarial examples, where the
  precision guards (docs/*.md, "twice", "must read <file>") suppress the
  trigger by design — models are expected to catch these.
- Finding: the repo deep_thinking template contains literal certainty
  language ("be absolutely certain … verify your reasoning repeatedly"), so a
  max_certainty flag on it is semantically defensible. Added `alt_ok`
  (acceptable secondary family, neither TP nor FP) to deep_thinking ⇄
  max_certainty template examples and 3 authored examples with the same
  mixture (dev-he-dt, hold-mix-dt, hold-adv-dt). Labeling change only;
  holdout untouched by any model at this point.

## Iteration 2 (first Gemma smoke, QAT q4_0, unconstrained)
- 2/2 smoke examples: correct family, verbatim evidence span, sensible
  reason/suggestion. Both truncated at max_tokens=900 while writing
  revised_prompt (repo prompts are ~600-800 tokens, and a full rewrite echoes
  most of that). Raised max_tokens to 1400.
- Thread sweep (llama-bench, r=1): t=4 pp512 67.5 tok/s tg64 18.1 tok/s;
  t=6 55.3/17.2; t=12 55.5/10.2. Chose -t 4 (P-cores only behavior).
- Observed server-side prefix caching: second request's prompt eval covered
  only the non-shared suffix (131 tokens) at ~65 tok/s.

## Infrastructure notes
- `pkill -f llama-server` matched the invoking shell itself and killed it,
  leaving the server down; one full dev run recorded connection errors only
  and was discarded (results/dev/gemma_uncon.jsonl overwritten by the rerun).
  Server is now started with setsid + pgrep -x checks.

## Iteration 3 (Gemma dev, first 11 examples) — two measurement fixes

Observed: every risk Gemma emitted named the correct family and quoted the
correct sentence, yet the first scoring pass reported precision 0.0 and a
100% fabricated-span rate. Two mechanical causes, both fixed in score.py
before any Gemma inference touched the holdout:

1. **Whitespace grounding.** The repo's generated prompts are hard-wrapped,
   so a correctly copied sentence differs from the prompt by newline-vs-space.
   All 14 evidence spans were exact modulo whitespace and 0 were fabricated.
   Grounding and span-overlap are now compared whitespace-normalized (a UI
   highlights a sentence, not byte offsets); `evidence_whitespace_only_diffs`
   is reported so the effect stays visible. Rules and judge results are
   unchanged by this (both had 0 such diffs), so it is not a metric that
   favors one system.

2. **Strict vs usable schema.** Unconstrained Gemma omits the optional
   `confidence` field on most outputs. Rather than weaken the metric, the
   scorer now reports BOTH `schema_compliance` (full schema.json conformance,
   the headline number) and `schema_usable` (parses, legal recommendation,
   legal risk types, string evidence). Gemma unconstrained: strict 0.09,
   usable 1.00 — precisely the gap constrained decoding is meant to close.

Interim Gemma dev (n=11, exploratory): displayed precision 1.00, warn recall
1.00, fabricated 0.00, median latency ~92 s/prompt.

## Iteration 4 (Gemma dev complete, n=61)

Detection (exploratory, dev): displayed precision 1.00, warn recall 1.00,
neutral FPR 0.00, fabricated spans 0.00, abstention 0.00. Per-family FPs: 1
(adjacent_cleanup). All three dev adversarial prompts — the ones the rules
guards deliberately suppress — were caught. 34 rewrites offered, 100%
protected-item preservation, 0 critical deletions, 0 language violations,
0 rewrites of clean prompts.

Schema: strict 0.49 / usable 1.00 (the gap is the omitted `confidence`).
23 evidence spans were exact-modulo-whitespace, 0 fabricated.

Runtime (Q4_0, -t 4, CPU): latency median 71.0 s, p90 96.9 s, min 35.3,
max 107.9. Generation 11.9 tok/s; prompt eval 235 tok/s (with server-side
prefix cache reuse across the shared system prompt). Median prompt 966
tokens, median completion 807 tokens, none hit the 1400 cap.
Split by output: with rewrite median 84.8 s (n=34), without 52.6 s (n=27).

This is the load-bearing deployment number: even a warning-only response is
~50 s, ~17x over the 3 s preflight budget frozen in PROTOCOL.md.
