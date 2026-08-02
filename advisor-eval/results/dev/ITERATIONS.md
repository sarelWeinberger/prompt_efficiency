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
