# Claude Code Harness Overhead (Experiment B calibration)

Fixed input overhead Claude Code 2.1.220 adds to every request when driving
Together AI models through the LiteLLM 1.93.0 gateway. Harness overhead — never
attribute it to the user prompt or to the model (design §6).

## Structure of a fresh Claude Code agent request

From the Anthropic-facing capture (gateway_inbound.jsonl): system prompt
≈6.7 KB of text plus **24 tool schemas** (vs pi's 4), streamed, `max_tokens`
32,000. The tool schemas dominate the prefix.

## Per-model fixed prefix (Together-side capture, median over pilot smoke+B runs)

Median `prompt_tokens` of fresh agent-shaped requests (system + 24 tools +
one short user message):

| model | Claude Code prefix (logical tokens) | pi prefix | ratio |
|---|---|---|---|
| moonshotai/Kimi-K2.7-Code | ≈15,983 | 1,147 | 13.9× |
| moonshotai/Kimi-K2.6 | ≈17,004 | 1,147 | 14.8× |
| thinkingmachines/Inkling | ≈17,415 | 1,242 | 14.0× |
| zai-org/GLM-5.2 | ≈18,032 | 1,323 | 13.6× |
| deepseek-ai/DeepSeek-V4-Pro | ≈19,638 | 1,555 | 12.6× |
| nvidia/nemotron-3-ultra-550b-a55b | ≈20,330 | 1,642 | 12.4× |

Claude Code's fixed prefix is consistently **12–15× pi's** across all six
tokenizers. At list prices this is $0.010–0.035 of input per request before
any conversation content; Together's automatic prefix caching frequently
rebates most of it on continuation requests (see cache_behavior.csv), but a
cache miss re-bills the full prefix.

## Metadata translation (H16, measured)

- Upstream (Together chat completions): explicit
  `completion_tokens_details.reasoning_tokens` and
  `prompt_tokens_details.cached_tokens` for all six models.
- Claude Code-visible usage: input/output totals preserved (sum matches
  capture exactly); reasoning detail **dropped**; cache fields unreliable
  (cache accounting is re-derived by the gateway, not passed through).
- `total_cost_usd` reported by Claude Code is computed against its own price
  table for the alias and is **wrong** for gateway models (measured: $0.17
  reported vs ≈$0.05 actual for the calibration task). All cost figures for
  claude-code runs are computed from the Together-side capture at catalog
  prices (§25).

## Observable ablations attempted

- Permission mode (acceptEdits vs bypassPermissions): available, part of the
  §14 permission experiment.
- `ANTHROPIC_SMALL_FAST_MODEL` pinned to the same alias so background calls
  stay on-model; `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` set for all runs.
- No CLAUDE.md, no MCP servers, no skills in benchmark HOMEs (isolated per run).
- A "reduced tool set" ablation comparable to pi's `--no-tools` is not
  attempted: Claude Code's toolset is integral to its agent loop, and forcing
  nominally matched ablations across fundamentally different harnesses is
  explicitly out of scope (design §7 addendum). Structural difference reported
  instead: 24 tools/≈16-20k tokens vs 4 tools/≈1.1-1.6k tokens.
