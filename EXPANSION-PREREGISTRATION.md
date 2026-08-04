# Expansion preregistration (FROZEN before any expansion run)

Research questions: do the four-layer findings generalize beyond the exact
prompt token sequences (E11, E12), the original 16+8 tasks (E1-E10 on new
tasks incl. long-validation family), 2 reps (stability), and the original
model set?

## Primary hypotheses (frozen)
E1 waste wording raises cost/success without success gain; E2 branches
without second implementation; E3 deep_thinking = volume without new
observable functional units or tool activity; E4 certainty -> post-success
verification; E5 misleading hints -> unsupported assumptions + pre-edit
deliberation; E6 bounded efficiency preserves diagnosis/implementation/
validation; E7 exploratory waste token-borne; E8 redundant verification
tool-borne; E9 tool results create bounded downstream model cost; E10
harness changes tool+reasoning composition; E11 mechanisms generalize
across paraphrases (paired effect same sign for >=3/4 paraphrases per
condition per model); E12 lexical form and position explain additional
heterogeneity (variance component > 0 with 95% CI excluding 0).

## Frozen elements
- Endpoints: primary = no-cache cost per compliant success + the E-specific
  mechanism metrics (identical definitions to semantic rubric v1 and tool
  rubric v1, unchanged); secondary under BH FDR q=0.10.
- Prompt arms: benchmark/expansion/paraphrase_manifest.json (frozen).
- Models: original 6 open-weight (pi); CC arm on same; sonnet-5 optional
  cost-layer arm only. New-model additions require a manifest amendment
  commit BEFORE their first run.
- Task inclusion: 24 new tasks + 16 holdout2 authored per EXPANSION-DESIGN
  categories, committed with fixtures+hidden tests BEFORE any run on them;
  holdout2 never used for tuning/rubric/thresholds/exploration.
- Reps: paraphrase 3; stability +3 (total 5 for those cells); new tasks 2;
  holdout2 1.
- Exclusions: run_validity != valid; infra errors resumable as before.
- Outliers: report medians+means+winsorized(95th)+quantiles; never drop.
- Stopping: stage caps in EXPANSION-DESIGN; infra/safety only; never on
  interim effects.
- Semantic rubric: v1 (e677e82) unchanged; judge = primary config only.
- Tool rubric: v1 (e9430aa) unchanged.
- Subgroups planned: per-model, per-harness, per-task-category,
  long-validation vs short.

Any post-hoc analysis is labeled exploratory. Results integrate into the
paper as a separately-labeled expansion layer; failed replications will be
reported prominently and abstract/conclusions revised.
