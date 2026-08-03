# Semantic reasoning analysis — does wasteful prompting change reasoning *structure*?

**Research question.** Do waste-inducing prompts merely increase the amount of
reasoning, or do they systematically change its structure — more unused
branches, unsupported hypotheses, repetition, re-verification, post-solution
deliberation?

Protocol: `benchmark/semantic_rubric.md` (frozen at commit `e677e82` before
any annotation; v1.0.1 clerical variant-name fix). Hypotheses H-S1–H-S6
preregistered there.

## 1. What reasoning artifacts actually exist (audit first)

Audited all 5,506 run directories plus the 2.5 GB dual-side wire capture
before designing anything. Five availability tiers:

| Tier | Artifact | Coverage in this dataset |
|---|---|---|
| 1 | Full textual reasoning traces | **All 7 open-weight models, both harnesses.** pi: `thinking` blocks in `turn_end` events. Claude Code: `thinking` blocks in session transcripts — the LiteLLM gateway translated Together's `reasoning` field into Anthropic thinking blocks. Independent cross-check: raw `reasoning` field in non-streaming wire-capture bodies. |
| 2 | Provider reasoning summaries | **None recorded.** claude-sonnet-5 ran with the API default `display: omitted`; summaries were never requested. |
| 3 | Visible assistant rationale | All runs (text blocks + final result messages). |
| 4 | Reasoning inferred from tool behavior | All runs — tool calls with full arguments (including Edit old/new strings) and tool results. Final diffs were not retained (workspaces reset per run); the edit-call sequence is the reconstructable record of changes. |
| 5 | Token counts only | **claude-sonnet-5** (162 runs): thinking is billed inside `output_tokens` and never returned; its Claude Code transcripts contain thinking blocks with *empty* text. Excluded from trace annotation; covered by tiers 3–4 and Method B only. |

No hidden chain-of-thought is claimed, imputed, or reconstructed anywhere.
Runs with zero thinking text on tier-1 models are real behavior (the model
chose not to think), verified against provider-reported reasoning-token
counts.

## 2. Methods

**Method A — structured judge annotation.** A condition-blind judge
(`claude-sonnet-5`, grammar-constrained JSON via strict `json_schema`
structured outputs) receives the canonical task spec (objective, acceptance
criteria, allowed paths — never the variant prompt or its name), the ordered
trace (thinking, visible text, tool calls + result excerpts), and test
outcomes. It emits 14 composition counts, 6 ordinal quality scores + 3
quality counts, and 6 waste-mechanism counts; **every nonzero count requires
an evidence quote** (≤25 words with turn + source). Corpus: 2,833 runs
(screening_pi 7 variants × 6 models × 16 tasks × 2 reps; the CC arm; the
stress misleading_architecture/ambiguous_scope runs; kimi3_pi; the frozen
holdout arm). Sensitivity: a paraphrased-prompt second judge and a
`claude-haiku-4-5` judge on a 60-run overlap. Batch API, ~50% pricing.

**Method B — deterministic behavioral reconstruction.** Pure-mechanical
proxies over all 4,644 valid runs (no model judgment): tool calls and
thinking volume before the first edit; tool calls, test runs, and output
after the first fully-green test; distinct/unedited file reads; a
task-restatement index (8-word shingle overlap between task spec and
reasoning); an internal-redundancy measure (zlib compression ratio of
thinking text); frozen regex lexicons for plan/alternative markers.

Both methods compare each variant against the precise baseline within the
same model × harness × task block (paired design, task-clustered bootstrap
CIs) — the same analysis skeleton as the main benchmark.

## 3. Validation (protocol §6)

- **Evidence-rule compliance:** 92.8% of nonzero counts in the pilot carry
  supporting quotes (154/166).
- **Researcher vs judge:** 6 stratified runs hand-labeled from raw traces
  *before* any judge output was viewed: 84.9% of 73 fields within ±1, 69.9%
  exact. All >1 disagreements were magnitude-not-direction on the two longest
  traces (the judge segments units more finely than the human). Adequate for
  paired directional analysis; absolute magnitudes carry this caveat.
- **Judge-judge agreement:** see §5 (60-run overlap, paraphrased prompt and
  different judge model).
- **Leakage controls:** the judge never sees variant text or names
  (condition-name leakage impossible by construction); verbosity leakage is
  addressed by reporting count metrics both raw and per-1k thinking chars;
  the sensitivity config reorders input sections (position check).
- **Truncation:** judge thinking counts against its output budget; pilot
  found 4/24 truncations at 16k tokens → budget raised to 24k for the
  full corpus.

## 4. Method B results (deterministic; all 6 open models, pi screening, paired vs baseline)

| Variant | Signal | Median (range across models) |
|---|---|---|
| multiple_approaches | alternative-lexicon markers, ratio | **18×** (10–22.5×) |
| multiple_approaches | alternative markers per 1k thinking chars, delta | **+2.2/1k** (+1.3 to +3.4) — denser in alternatives, not just longer |
| deep_thinking | internal redundancy (compression ratio), delta | **+0.05** (+0.03 to +0.07) on 6/6 models |
| deep_thinking | thinking volume, ratio | 2.2× (1.5–2.6×) |
| max_certainty | test runs after first green test, delta | **+1.0** (0 to +1.75) |
| max_certainty | tool calls after first green test, delta | **+2.0** (+1 to +2) |
| max_certainty | post-green output chars, ratio | 2.6× (1.2–16×) |
| bounded_efficiency | post-green output, ratio | 1.00 (0.67–1.06) — nothing useful removed |
| bounded_efficiency | alternative markers, ratio | 0.0 (0–1.3×) |
| misleading_architecture (stress) | thinking before first edit, ratio | **4.2×** (1.2–11.7×) |
| misleading_architecture | tool calls before first edit, delta | +1.0 (+0.5 to +6.75) |
| ambiguous_scope (stress) | tool calls before first edit, delta | +2.75 (+1.5 to +4.75) |
| ambiguous_scope | files read but never edited, delta | +1.0 (0 to +1.5) |

Harness composition at baseline (H-S6, same models/tasks): Claude Code runs
**3× the test executions** (median 3 vs 1), ~2× the thinking volume, and
spends only **27% of its tool activity before the first edit vs pi's 57%** —
a verification-heavy, edit-early/verify-long composition, versus pi's
explore-then-edit profile.

## 5. Method A results (judge annotation, 2,801 valid of 2,833 submitted)

Per-model paired deltas vs own baseline (median across the 6 open models
[min,max]; pi screening unless noted). Counts are judge-annotated reasoning
units with mandatory evidence quotes.

**H-S1 — CONFIRMED, and replicated on the frozen holdout.**
`multiple_approaches` adds **+3.5 considered approaches [+3,+4]** of which
**+3.0 become unused branches [+2,+3]**; `alternatives_implemented` rises
exactly +1.0 on every model — from 0 (baseline: the single solution is not
an "alternative") to 1 (the chosen branch). The tournament produces
discarded elaborations, never a second implemented idea. Holdout deltas are
identical (+3.5 / +3.0 / +1.0). `planning_without_implementation` unchanged.

**H-S2 — REFINED: elaboration without units.** The judge finds *no* new
functional units under `deep_thinking`: task_restatements +0.0,
redundant_verification +0.0, factual_grounding +0.0, hypotheses_grounded
+0.0, evidence_collection +0.5 at most. Yet Method B shows 2.2x thinking
volume and +0.05 internal redundancy. Resolution: deep-thinking cues make
each reasoning move *longer and more repetitive in phrasing* (intra-unit
verbosity, caught by compression) without adding a single extra hypothesis,
verification, or piece of evidence (unit level, caught by the judge). More
words per thought; not more thoughts; no better grounding.

**H-S3 — CONFIRMED.** `max_certainty`: redundant_verification **+1.0 on
6/6 models** [+1,+1.5], testing_verification +1.25, post_solution_reasoning
+1.0, final_validation +0.5 — converging with Method B's +1 test run and
+2 tool calls after the first green test. Certainty pressure buys
re-verification of already-established facts.

**H-S4 — CONFIRMED via the ungrounded-hypothesis channel.**
`misleading_architecture` (stress family): unsupported_assumptions **+1.0**
[0,+2], hypotheses_stated +1.0 while hypotheses_grounded stays **+0.0** —
the hint injects hypotheses that never acquire grounding in inspected code.
The narrow `speculative_architecture` label stayed at 0 median (its
cross-judge reliability was also indeterminate); the effect lives in the
assumptions/hypotheses fields. Method B adds the behavioral half: 4.2x
pre-first-edit deliberation.

**H-S5 — CONFIRMED.** `bounded_efficiency` is semantically inert in both
directions: unused_branches +0.0, post_solution_reasoning +0.0 (to -0.25),
and — critically — error_diagnosis +0.0 and final_validation +0.0. The
efficiency template removes no useful diagnosis or validation; it simply
declines to add waste. (Baselines already sit near zero on branch counts,
so "reduces abandoned branches" realizes as "keeps them at zero".)

**H-S6 — CONFIRMED.** Judge-annotated composition shares at baseline
(median share of composition units; pi n=192, CC n=85): Claude Code shifts
reasoning toward planning (0.158 vs 0.111), error_diagnosis (0.091 vs
0.000 — much of it recovering from harness-environment friction such as
permission dialogs), and self_corrections (0.048 vs 0.000); pi spends
relatively more on evidence_collection (0.143 vs 0.083),
implementation_reasoning (0.125 vs 0.083), problem_understanding, and
final_validation. Same models, same tasks: the harness changes what the
reasoning is *about*, not just how much of it there is.

## 6. Waste-mechanism examples (redacted)

**Re-verification loop under certainty pressure** (Kimi-K2.7-Code, pi,
max_certainty, py-low-01): after a one-line fix and a passing read-back, the
model announces *"Let me run the tests multiple times to be absolutely
confident"* — extra test executions and a file re-read after the fact,
none of which changed anything.

**Repetition spiral under deep_thinking** (Kimi-K2.6, Claude Code,
py-low-01): the model re-plans the same 5-step task twice before the first
tool call, then spends 16 turns re-deriving the same conclusion about a
blocked permission dialog ("the user explicitly said verify with... so I
should run it... but it requires approval... but the user explicitly
said...") — thousands of reasoning tokens re-establishing one already-known
fact.

**Reversals without new evidence** (Inkling, pi, adjacent_cleanup,
js-med-01): prompted to "clean up anything adjacent", the model accidentally
creates a stray blank test file, deletes it, re-creates it, deletes it —
four write/delete cycles with no new information between reversals — before
finishing an otherwise-correct fix.

**Post-solution deliberation** (same run): after the green test, two more
turns of re-reading finished files "to verify" text that had not changed.

## 7. Correlations (Spearman, n=2,792-2,801 annotated runs)

| Semantic measure | Strongest quantitative correlates | rho |
|---|---|---|
| unused_branches | reasoning tokens / output tokens | **0.54** / 0.53 |
| redundant_verification | turns / tool calls / no-cache cost | **0.58** / 0.52 / 0.48 |
| task_restatements | reasoning tokens | 0.32 |
| unsupported_assumptions | no-cache cost / turns | 0.36 / 0.34 |
| any waste mechanism | **task success** | **-0.09 to +0.11 (~0)** |
| unsupported_assumptions | task success | **-0.19** (the one semantic failure predictor) |

Reading: the semantic waste mechanisms *are* the token/turn/cost waste
(structure explains the quantity), and none of them buy success. The only
semantic marker that predicts anything about correctness is
unsupported-assumption count - negatively.

## 8. What cannot be concluded (hidden-reasoning limits)

- **Nothing semantic about claude-sonnet-5's thinking.** Its reasoning is
  never returned by the API; the Claude-API study's output-token effects
  cannot be decomposed into deliberation vs response, and none of the
  composition/quality claims here extend to it. Only Method B tool-level
  proxies and visible rationale apply.
- **Open-model traces are the provider-returned reasoning stream.** Whether
  a model's internal computation differs from its emitted reasoning text is
  unobservable; claims are about the recorded deliberation record only.
- **Truncation floor:** judge inputs cap thinking at 6k chars/turn; runs
  above the cap (rare; heaviest CC deep_thinking traces) are annotated on a
  prefix. Method B, which is computed on full text, is the check against
  cap-induced bias.
- **No causal claim about *why* adaptive thinking absorbs deep-thinking cues
  on Sonnet 5** — the mechanism is invisible by design.

## 9. Recommended paper additions

- **Methods:** one subsection ("Semantic reasoning analysis") describing the
  five-tier artifact audit, the frozen rubric/schema, the condition-blind
  judge with mandatory evidence spans and grammar-constrained decoding, the
  deterministic proxy layer, and the validation battery (researcher
  agreement, dual-judge sensitivity, evidence compliance, verbosity
  controls).
- **Results:** one subsection reporting H-S1-H-S6 with the two headline
  mechanisms: (a) the multiple-approaches effect is unused branches (+3
  elaborated-then-discarded strategies per run, exactly +1 implemented -
  replicated on the frozen holdout); (b) the deep-thinking effect is
  intra-unit elaboration (2.2x volume, higher compressibility, zero new
  functional units, zero grounding gain). Plus the certainty->re-verification
  loop, the misleading-hint->ungrounded-hypothesis channel, and the harness
  composition shift.
- **Discussion:** waste-inducing prompts do not produce "more thinking" in
  any epistemically useful sense - they produce structurally identifiable
  non-functional deliberation (branches never used, facts re-proven, prose
  re-elaborated). This licenses the practical advice: the cheapest
  optimization is deleting instructions that request non-functional
  structure.
- **Limitations:** annotated reasoning is the provider-returned stream, not
  internal computation; claude-sonnet-5 is unannotatable by design (thinking
  never returned); judge counts are reliable for direction, not absolute
  magnitude (within-1 84.9-93.6%, presence-kappa 0.44 same-model /
  0.28 cross-model, with hypothesis-critical fields at 0.55-0.68);
  post_solution_reasoning and task_restatements are judge-sensitive labels
  whose conclusions rest on the deterministic proxies instead.
