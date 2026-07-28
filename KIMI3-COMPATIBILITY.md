# Kimi-K3 Compatibility Record (post-registration replication)

Verified 2026-07-28 against the live Together API and this repo's harness
stack, before any paid replication run.

## Verified

| Item | Value | Evidence |
|---|---|---|
| Together model ID | `moonshotai/Kimi-K3` | live `/v1/models` listing |
| API route | OpenAI chat completions (`/v1/chat/completions`), direct (pi) and via LiteLLM `together_ai/` (Claude Code) | wire capture |
| Context window | 1,000,000 tokens | Together metadata |
| Pricing | $3.00/M input, $15.00/M output, $0.30/M cached input | Together pricing object |
| Tool calls (pi) | ✅ full coding loop: solved py-low-01 in 4 turns / 4 tool calls, scope-compliant | probe run, results/raw/k3-probe/ |
| Tool calls (Claude Code) | ✅ 14-capability smoke passed, `tool_loop_valid: true` | results/compatibility/cc_compat_kimi_k3.json |
| Reasoning tokens | ✅ explicit `completion_tokens_details.reasoning_tokens`, both paths | pi normalized usage + together-side capture |
| Cached-input reporting | ✅ explicit `prompt_tokens_details.cached_tokens`; large first-run hits observed (3.3k on pi prefix, 15–17k on Claude Code prefix) | capture |
| pi catalog | knows K3 pricing; cost computation correct | probe |

## Uncertain / not verified

- **Output token limit**: not directly probed; pi caps `max_tokens` from its
  catalog and runs completed normally. Not load-tested near the limit.
- **Native vision via Together**: endpoint lists `image_pixel: 0` pricing;
  irrelevant to this text-only replication, noted for completeness.
- **Parameter count**: public sources report a 2.8T-parameter MoE
  (16-of-896 experts) — satisfies the repo's >500B inclusion rule, but the
  figure is from Moonshot's announcement, not independently verified.
- **Smoke-suite artifact (documented)**: `cc_smoke.py`'s reasoning/cache
  detection uses capture-tail seq matching, which collides across proxy
  restarts; its initial "unsupported" flags for K3 were disproven by direct
  inspection of the fresh capture segment. The runner's offset-windowed
  attribution is unaffected.

## Frozen replication protocol (recorded before any result was viewed)

- **Tasks (rule: reuse the frozen Phase 1 pilot set unchanged)**:
  py-low-01, go-low-01 (low); py-med-01, js-med-03 (medium); js-high-01,
  go-high-01 (high). Satisfies the constraints: py-med-01 is multi-file
  (cart package); js-high-01 is invariant-preservation (a failed load must
  never be cached; concurrent dedup) and go-high-01 is concurrency-safety;
  js-high-01 showed the strongest prior Kimi prompt effect (Kimi-K2.6:
  34.8k reasoning tokens under an exploration cue in pilot B).
- **Variants**: baseline, multiple_approaches, deep_thinking,
  bounded_efficiency.
- **Matrix**: pi 6×4×3 = 72; Claude Code 3×4×2 = 24 (py-low-01, js-med-03,
  js-high-01). Hard cap: 96 paid runs; reruns only for
  infrastructure/gateway/interruption/parsing failures.
- **Material-difference thresholds**: benchmark/config.yaml
  `kimi3_material_difference` (frozen with this commit).
- **Comparators**: Kimi-K2.6 and Kimi-K2.7-Code screening runs restricted to
  the same 6 tasks, each model against its own baseline.
