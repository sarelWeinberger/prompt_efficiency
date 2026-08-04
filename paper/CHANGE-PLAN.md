# Manuscript integration — section-by-section change plan (pre-edit)

Audited: paper/main.tex (461 lines), SEMANTIC-ANALYSIS.md, TOOL-COST-ANALYSIS.md,
benchmark/semantic_rubric.md (e677e82), benchmark/tool_cost_rubric.md (e9430aa),
results/summaries/semantic_*.csv, tool_cost_*.csv, rv_cost_robustness.json (new,
distributional context for the 18x claim), annotations_primary.jsonl. Citations
verified against arXiv abs pages (titles + full author lists + years).

Narrative: one four-layer argument — wording -> work & cost (Claim 1, unchanged
preregistered core) -> observable reasoning structure (Claim 2, 7 open models
only) -> visible traces are not complete computation (Claim 3, scoped via
arXiv:2607.22925) -> mechanism-specific propagation into tools/latency/cost
(Claim 4, token-borne vs tool-borne).

| Section | Action |
|---|---|
| Title | Candidates: (a) keep; (b) "Prompt Wording Changes How Coding Agents Spend: Reasoning, Tools, and End-to-End Cost"; (c) "Prompt-Induced Waste in Coding Agents: Reasoning Structure, Tool Behavior, and End-to-End Cost (A Preregistered Two-Harness Benchmark)". ADOPT (c): more accurate (contribution now spans semantics+tools+cost), not broader than evidence; preserves the recognizable "Prompt-Induced Waste" head. |
| Abstract | Rewrite: causal question, scale (4,644 valid runs + 2,801 annotated), primary economic result, mechanism result, token-/tool-borne split, bounded-efficiency null, trace-incompleteness + Sonnet-5 limitation. |
| Introduction | Motivation from token cost to total agent work; introduce four layers. |
| Contributions | Rewrite as 5 claims incl. careful "to our knowledge" chain claim (supported by 6-paper audit). |
| Methods | Add: trace-availability inventory + Sonnet-5 exclusion; semantic rubric/judge/validation summary; tool taxonomy/redundancy/first-green proxy/cost decomposition/attribution bounds; zero-inflation handling. |
| Results | Reorder: (1) primary effects (existing tables unchanged), (2) observable reasoning mechanisms, (3) cost carriers by mechanism (+ integrated mechanism table + robustness table for 18x), (4) tools/post-success/latency, (5) harness composition, (6) bounded efficiency, (7) robustness & validation. Stress/cache/Kimi-K3/Claude-API sections retained. |
| Figures | Add 2, generated from CSVs by paper/make_figures.py: fig1 cost-carrier comparison (branch level vs cost & calls; verification level vs cost/calls/latency), fig2 harness tool composition. No prose-derived charts. |
| Related work | NEW section, 7 categories, 6 verified arXiv citations + positioning sentence (no "first" claim). |
| Discussion | Lead: "cost is determined not only by how long it reasons but by what reasoning causes the agent to do"; mechanism-specific guidance list. |
| Limitations | Full list per spec (trace faithfulness, Sonnet-5, attribution bounds, no tool charges, no CPU/GPU, pi timing, first-green proxy, heavy tails, H-T1/H-T4 directional, task scale, judge agreement numbers verified from source). |
| Conclusion | Rewrite per agreed wording; no new claims. |
| Bibliography | +6 verified entries; repo entry updated. |
| Claim audit | paper/CLAIM-AUDIT.md: claim -> result -> source file/field -> n -> strength -> scope; plus excluded-claims list. |

Excluded claims (evidence too weak for the paper):
- H-T1 tool-call increase as a confirmed effect (perm p~.06, near-zero medians) — directional only.
- H-T4 tool-layer magnitudes (p=.19) — directional only.
- Any semantic statement about claude-sonnet-5 reasoning (no trace).
- task_restatements / post_solution_reasoning judge counts as primary evidence (cross-judge kappa ~0) — deterministic proxies used instead.
- Formal causal mediation (descriptive strata only).
- "First to..." novelty (only the scoped to-our-knowledge chain sentence).
- Any dollar figure for local tool execution (no charge exists).
