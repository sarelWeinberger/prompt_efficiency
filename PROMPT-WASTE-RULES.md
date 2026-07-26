# Prompt-Waste Rules — practical guidance from the pilot

**Phase 1 (pilot) guidance** distilled from RESULTS.md (460 valid runs,
6 models, 2 harnesses). These are working rules pending the preregistered
screening and frozen-holdout phases (RESULTS.md §8), not final conclusions. Confidence
labels: **strong** = classified wasteful/neutral with CI support on multiple
tasks; *tentative* = consistent direction, underpowered pilot cells. All of it
is pilot-scale evidence on small coding tasks; screening + holdout may revise.

## Cross-model rules (apply everywhere)

1. **Never add deep-thinking incantations to coding prompts.** (strong)
   "Think very deeply, reason through every possibility, verify repeatedly"
   multiplied reasoning tokens 1.8–3.2× on every PI.DEV model and roughly 2×
   wall time, with zero correctness gain on any task. The models already
   deliberate; the phrase only raises the deliberation floor.

2. **Keep scope-expanding language out unless you truly want expansion.** (strong)
   "Feel free to clean up anything adjacent" and "do whatever is necessary,
   don't ask questions" were the *only* phrasings that produced out-of-scope
   edits (6–7% of their runs) — and they also raised reasoning 1.8–4× on half
   the models. Thinking-style cues never widened a diff; scope-style cues did.

3. **Bounded-efficiency framing is free insurance.** (strong)
   Explicit scope + acceptance criteria + "smallest sufficient change" +
   stop condition ran at 0.9–1.2× baseline reasoning with unchanged success on
   every model. Against a sloppy prompt it prevents waste; against a precise
   one it costs nothing.

4. **Don't pay for waste twice: prompt length ≠ cost.** (strong)
   The fixed harness prefix is 1.1–1.6k tokens (pi) / 16–20k (Claude Code) per
   request. A 300-character-longer prompt is noise; one extra agent turn
   re-sends the entire prefix. Optimize for *fewer turns and less deliberation*,
   not shorter wording.

5. **Treat cache savings as a rebate, never as efficiency.** (strong)
   Caching cut the actual bill ~58% while changing zero behavioral metrics.
   A "cheap" run may be a lucky cache route; judge prompts on reasoning
   tokens, tool calls, and turns, price runs at no-cache cost.

## Model-specific notes (Together AI)

- **GLM-5.2**: most prompt-sensitive of the six. Deep-thinking 3.2×,
  adjacent-cleanup 4.2×, and exhaustive-exploration 2.4× *with a success drop*
  (−6%) — the only harmful-leaning cell in the pilot. Give GLM tight scope and
  a named starting file.
- **Kimi-K2.6**: heaviest absolute reasoner (3.3k median tokens under pi
  baseline; 8.6k under Claude Code) and 2.8× under deep-thinking. Efficiency
  phrasing pays off most here in absolute dollars.
- **Kimi-K2.7-Code vs K2.6 (Q12): yes, K2.7-Code reasons far less.**
  Under Claude Code on matched cells: 594 vs 8,645 median reasoning tokens,
  10 vs 39 turns, $0.05 vs $0.19 per success. *(Same-harness pilot evidence;
  pi-side comparison pending screening.)*
- **nemotron-3-ultra**: cheapest and fastest under pi ($0.009/success, 5
  turns) but thrashes under Claude Code (35+ turns, $0.30/success) — the
  strongest harness-interaction case. Also: expect **no cache rebate via pi**
  (0/96 runs hit).
- **DeepSeek-V4-Pro**: mildest prompt sensitivity under pi (1.3–1.8×);
  note pi runs it at `reasoning_effort: high`, so its baseline deliberation is
  already elevated.
- **Inkling**: nearly prompt-insensitive under Claude Code (0.8–1.5× across
  all variants) — but scoped_authorization showed a −20% success dip
  (underpowered; watch in screening).

## Harness-specific guidance

- **Under Claude Code, prompt discipline matters more, not less**: its loop
  amplifies exploration cues into extra turns (4–4.8× reasoning under
  exhaustive-exploration on three models), and every extra turn re-bills a
  16–20k-token prefix. State scope and stop conditions explicitly.
- **Do not carry prompt folklore across harnesses** (H12): goal-only prompts
  *reduced* reasoning under Claude Code on 4/5 models (its system prompt
  already supplies methodology) while under pi omitting criteria mainly
  degrades verifiability. Re-test per harness.
- **Explicit authorized/forbidden scope blocks** kept out-of-scope changes at
  0% in the pilot — cheap protection when combined with autonomy language.

## Open questions carried to screening

Complexity scaling (H7), ambiguity variance (H5), multi-turn restatement costs
(stress family), CC planning-turn attribution (H14), permission-mode contrast
(§14), eviction timing beyond 60 s, and whether cache rebates systematically
hide behaviorally wasteful prompts (H6 at scale).
