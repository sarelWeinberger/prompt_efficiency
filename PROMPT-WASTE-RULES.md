# Prompt-Waste Rules — holdout-validated guidance

Distilled from the completed benchmark (4,400 valid runs; 6 models × 2
harnesses; frozen-holdout confirmation on 8 unseen tasks). Confidence labels:
**confirmed** = replicated on the frozen holdout with CI support;
*screening/stress* = strong screening or stress-family evidence, no holdout
pass; (directional) = consistent but underpowered.

## The five rules that survived holdout

1. **Never ask for "several approaches compared before choosing." (confirmed, 6/6 models)**
   The single most expensive phrase tested: 2.4×–7.4× reasoning tokens
   (worst: Kimi-K2.6 at 7.4×) with zero correctness gain on unseen tasks.
   If you want options, ask for options as the deliverable — don't bolt an
   internal design tournament onto a fix request.

2. **Never add deep-thinking incantations. (confirmed, 5/5 selected models)**
   "Think very deeply / verify repeatedly" = 1.6–2.2× reasoning, ~2× latency,
   nothing in return — replicated across pilot, screening, and holdout on
   three different days.

3. **Keep scope-expanding language out unless you want expansion. (confirmed)**
   "Clean up anything adjacent" holds up as wasteful on Inkling (3.1×) and
   GLM-5.2 (4.3×) and remains one of only two phrasings that produce
   out-of-scope edits. Autonomy language ("don't ask questions, do whatever is
   necessary") turned out to be a scope risk (6–8% oos), NOT a reasoning
   cost — its screening token-signal did not replicate.

4. **Bounded-efficiency framing is free everywhere and pays on GLM. (confirmed, 6/6)**
   Explicit scope + acceptance criteria + smallest-sufficient-change + stop
   condition: 0.97–1.16× on five models, **0.48× on GLM-5.2** — the only
   intervention that actively saved reasoning tokens at equal success.

5. **Certainty pressure costs real money on DeepSeek. (confirmed on DeepSeek, 1.85×; weaker on nemotron, 1.48×)**
   "Be absolutely certain, re-verify until nothing can be wrong" buys extra
   verification loops, not extra correctness.

## Input-defect costs (stress family — what to fix in your own prompts)

- **A wrong architectural hint is the costliest defect measured (2.61×)**:
  models chase your red herring diligently. If you're not sure where the bug
  is, say nothing — don't guess.
- **Ambiguous scope is the only thing that reliably hurts correctness**
  (83% success, worst in benchmark, +44% reasoning). Precision beats brevity.
- **Restating the full task every turn costs ~40% extra reasoning**; splitting
  one task across turns costs ~30%. Say it once, completely, in turn one.
- **Irrelevant background prose is nearly free (1.03×)** — models filter
  noise well. Cutting fluff saves little; cutting *misleading* content saves a lot.
- Conflicting constraints (1.05×): models silently pick one side — cheap but
  unpredictable; still worth avoiding for control, not cost.

## Model-specific notes (Together AI, holdout-backed where marked)

- **GLM-5.2** — most prompt-sensitive model tested: multiple_approaches 6.2×✓,
  adjacent_cleanup 4.3×✓, deep_thinking 2.2×✓, but also the biggest
  bounded-efficiency payoff (0.48×✓). Prompt discipline matters most here.
- **Kimi-K2.6** — largest single effect in the benchmark
  (multiple_approaches 7.4×✓) on the heaviest baseline reasoner; efficiency
  wording saves the most absolute dollars.
- **Kimi-K2.7-Code** — reasons far less than K2.6 (Q12 answered: ~594 vs
  8,645 median under CC; 5-8× less across pi cells) but still 6.0×✓ under
  multiple_approaches — no model is immune.
- **DeepSeek-V4-Pro** — the certainty-pressure model (max_certainty 1.85×✓);
  note pi maps thinking=medium to reasoning_effort=high for it.
- **nemotron-3-ultra** — smallest ratios of the six (1.5–2.4×✓) and cheapest
  per success under pi; but zero cache rebate via pi (0 cached tokens in
  every phase) — budget it at list price.
- **Inkling** — insensitive to thinking-style cues, sensitive to scope cues
  (adjacent_cleanup 3.1×✓, multiple_approaches 5.1×✓).

- **Kimi-K3 (post-registration small replication)** — lowest deliberation
  floor measured (baseline ≈55 reasoning tokens): thinking-style cues
  multiply its reasoning ~15× (vs 2–6× on K2.x), though absolute waste and
  cost per success stay at or below K2 levels on these tasks. Same rules
  apply, with more force: never use deep-thinking or multiple-approaches
  language on K3; bounded-efficiency confirmed neutral (0.89×). At $15/M
  output, absolute waste scales fastest here on longer tasks.

- **claude-sonnet-5 via the first-party Anthropic API (post-registration
  reversal study)** — the rules transfer to the frontier model:
  multiple_approaches 2.5-2.7x on both harnesses; **max_certainty is the
  worst family under native Claude Code (4.1x, 2.7x cost per success)** —
  certainty pressure is a bigger hazard on Claude+CC than anywhere else
  tested; deep_thinking is the mildest measured (1.25-1.3x — adaptive
  thinking absorbs it); bounded_efficiency/autonomy/verbose all neutral;
  scope compliance was perfect (162/162). Note: Anthropic does not report
  thinking tokens separately, so these are total-output ratios (lower bounds
  on the deliberation effect).

## What the waste actually is (semantic analysis)

Trace-level annotation of 2,801 runs shows each rule's mechanism:
- multiple_approaches buys **discarded branches** — ~3 extra strategies
  elaborated then abandoned, never a second implemented idea.
- deep_thinking buys **padding** — zero new hypotheses, evidence, or
  verification; the same reasoning moves written longer and more
  repetitively.
- max_certainty buys **re-proofs** — re-verification of already-established
  facts after the tests are already green.
- A wrong architectural hint buys **ungrounded hypotheses** — theories that
  never acquire support from inspected code (and the only semantic marker
  that predicts *failure*).
- bounded_efficiency removes none of the useful work (diagnosis and final
  validation unchanged) — it is genuinely free.

## Harness rules

- **The harness choice dwarfs every prompt effect**: same model, same task =
  5–30× more per success under Claude Code (16–20k prefix × 2–7× turns),
  at equal success. Choose/trim the harness before tuning wording.
- **Do not carry prompt folklore across harnesses (H12 confirmed)**: goal-only
  prompts cut reasoning under Claude Code but degrade verifiability under pi;
  exploration cues amplify 4×+ under CC vs mildly under pi. Re-test per harness.
- **Treat cache savings as a rebate, never as efficiency**: ~61% billing
  reduction across 4,400 runs with zero behavioral change. Judge prompts on
  reasoning/tool/turn metrics; budget at no-cache prices.
- **Prompt length ≠ cost**: verbose_repetition ≈1.0× everywhere. The waste is
  in what you *ask for*, not how many words you use.
