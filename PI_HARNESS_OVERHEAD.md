# PI.DEV Harness Overhead (Experiment B calibration)

Fixed input overhead pi adds to every request, measured per model. This is
harness overhead — never attribute it to the user prompt (H8) or the model.

## Retained ablations (GLM-5.2, single-shot, from TOKEN-ANALYSIS.md)

| configuration | input tokens |
|---|---|
| default pi (4 tools) | ≈1,291 |
| `--no-tools` | ≈464 |
| `--no-tools` + minimal system prompt | ≈71 |

Component split: ≈827 tool schemas (edit ≈331, read ≈215, bash ≈158, write ≈123),
≈399 system prompt (≈206 of it pi self-documentation paths), ≈64 envelope,
≈1 user message. The four tools are described twice per request (prose in the
system prompt + JSON schemas).

## Per-model fixed prefix (schema-discovery wire capture, 2026-07-26)

Trivial prompt ("Reply with exactly: OK"), default pi toolset, `--thinking medium`.
`prompt_tokens` from Together's usage object — same byte prefix, different tokenizers:

| model | pi fresh-request prompt tokens |
|---|---|
| moonshotai/Kimi-K2.6 | 1,147 |
| moonshotai/Kimi-K2.7-Code | 1,147 |
| thinkingmachines/Inkling | 1,242 |
| zai-org/GLM-5.2 | 1,323 |
| deepseek-ai/DeepSeek-V4-Pro | 1,555 |
| nvidia/nemotron-3-ultra-550b-a55b | 1,642 |

Cross-model reasoning-token comparisons must be normalized within model — the
same prefix costs Kimi 1,147 and nemotron 1,642 tokens (+43%) purely from
tokenization (design §23).

## Effective thinking configuration under `--thinking medium`

From captured request bodies: all six get `reasoning: {enabled: true}`;
**DeepSeek-V4-Pro additionally gets `reasoning_effort: "high"`** (pi's level
mapping). DeepSeek pilot results are labeled effort=high accordingly (§13);
this is a harness mapping, not a benchmark manipulation.

## Notes

- These ablations are diagnostic only. The main experiment holds the default
  toolset constant across prompt variants (design §4); `--no-tools` never
  appears in Experiment A.
- pi embeds the working directory in its system prompt: slot paths are held
  constant within paired blocks so the prefix is byte-stable (design §10).
