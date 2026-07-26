# Prompt Efficiency

Measuring what an AI coding agent *actually* sends to the model — and what it costs — using [pi.dev](https://pi.dev) with [Together AI](https://www.together.ai/) as the model provider.

## What's in this repo

| File | Description |
|---|---|
| [PI-DEV-SETUP.md](PI-DEV-SETUP.md) | Full install & configuration guide (nvm → Node 22 → pi → Together AI) |
| [pi-request.log](pi-request.log) | The exact HTTP request pi sends to Together AI for a one-word "hi" prompt, captured with a local logging proxy (API key redacted) |

## Key finding

Sending **"hi"** (1 word) through pi to `zai-org/GLM-5.2` costs **1,319 input tokens** (~5.8 KB of JSON):

| Component | Share |
|---|---|
| System prompt (agent instructions, tool guidelines, local paths) | ~45% |
| Tool JSON schemas (`read`, `bash`, `edit`, `write`) | ~45% |
| The actual user message | ~1% |

Total for the round trip: 1,330 tokens (1,319 in + 11 out) ≈ **$0.0019**.

## Quick start

```bash
# 1. Install Node.js 22+ (via nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh"
nvm install 22

# 2. Install pi
npm install -g --ignore-scripts @earendil-works/pi-coding-agent

# 3. Configure Together AI (key goes in ~/.pi/agent/auth.json, or:)
export TOGETHER_API_KEY="tgp_v1_..."

# 4. Run
pi --provider together --model "zai-org/GLM-5.2" -p "hi"
```

## Inspecting token usage

JSON mode exposes the per-message `usage` object (tokens + cost):

```bash
pi --provider together --model "zai-org/GLM-5.2" --no-session -p --mode json "hi" 2>&1 | tail -20
```

## Capturing the raw request

pi's wire payload was captured by running a small Node HTTP proxy in front of `api.together.xyz` and overriding the provider's `baseUrl` with a one-line pi extension:

```js
export default function (pi) {
  pi.registerProvider("together", { baseUrl: "http://127.0.0.1:8901/v1" });
}
```

```bash
pi --provider together --model "zai-org/GLM-5.2" --no-session -e proxy-extension.js -p "hi"
```

See [pi-request.log](pi-request.log) for the result.

## Notes

- API keys live in `.env` (git-ignored) and `~/.pi/agent/auth.json` — never committed.
- Default provider/model are set in `~/.pi/agent/settings.json`.
- List all available Together AI models: `pi --list-models together`

---

## The prompt-waste benchmark

**Status: Phase 1 — completed infrastructure and pilot benchmark.** The
preregistered full screening and frozen-holdout phases have not run yet
(see RESULTS.md §8); pilot findings are labeled as such.

The measurements above grew into a controlled benchmark: **which prompt
formulations make large reasoning models waste reasoning tokens, tool calls,
turns, and money — under PI.DEV vs Claude Code, on the same Together AI models?**

| Document | What it holds |
|---|---|
| [EXPERIMENT-DESIGN.md](EXPERIMENT-DESIGN.md) | Pre-registered hypotheses (H1–H8, H12–H17), metrics, waste definitions, protocols |
| [BENCHMARK-RUNBOOK.md](BENCHMARK-RUNBOOK.md) | How to run every part of the benchmark |
| [PI_HARNESS_OVERHEAD.md](PI_HARNESS_OVERHEAD.md) | PI.DEV fixed-prefix calibration per model |
| [CLAUDE_CODE_HARNESS_OVERHEAD.md](CLAUDE_CODE_HARNESS_OVERHEAD.md) | Claude Code fixed-prefix calibration (12–15× pi) + gateway metadata loss |
| [HARNESS-COMPARISON.md](HARNESS-COMPARISON.md) | PI.DEV vs Claude Code: measured compatibility/metadata findings + pilot-scale behavioral comparison |
| [RESULTS.md](RESULTS.md) | Phase 1 pilot results + remaining preregistered work |
| [PROMPT-WASTE-RULES.md](PROMPT-WASTE-RULES.md) | Practical guidance distilled from the data |

Infrastructure: [benchmark/](benchmark/) (frozen configs, 24 tasks, fixtures,
hidden evaluators, LiteLLM gateway), [src/](src/) (runners, parsers, orchestrator),
[analysis/](analysis/), [tests/](tests/), machine-readable outputs under
[results/](results/) (`runs.jsonl`, `summaries/*.csv`, compatibility and
schema-discovery records).

### What Phase 1 measured

| | |
|---|---|
| Models | DeepSeek-V4-Pro, Kimi-K2.6, Kimi-K2.7-Code, nemotron-3-ultra-550b-a55b, Inkling, GLM-5.2 (frozen) |
| Harnesses | PI.DEV 0.82.1 (direct) and Claude Code 2.1.220 (via LiteLLM 1.93.0 gateway, dual-side redacted capture) |
| Runs | **460 valid pilot runs** (Pilot A: full 360-run PI.DEV matrix; Pilot B: 100 Claude Code runs, budget-capped) + 70 cache-session records — 100% parse validity |
| Spend | $17.98 actual / $42.68 estimated no-cache (caching rebated ~58%) |
| Compatibility | All 6 models pass Claude Code's full tool loop — but only on 1 of 3 gateway routes tried; the failures (silent tool-schema drops, empty continuations) are preserved as evidence |

### Headline pilot findings (pending screening + holdout)

1. **"Think very deeply / verify repeatedly" is a money-burning no-op** —
   1.8–3.2× reasoning tokens on all four PI.DEV pilot models, ~2× latency,
   zero correctness gain. The only variant wasteful everywhere.
2. **The harness dwarfs the prompt** — the same model on the same task costs
   **5–30× more per success under Claude Code** than PI.DEV at equal ~100%
   success (16–20k-token fixed prefix, 12–15× pi's, × 2–7× more turns), and
   prompt effects flip direction between harnesses.
3. **Scope language, not thinking language, widens diffs** — only
   "clean up anything adjacent" (6%) and "don't ask questions, do whatever is
   necessary" (7%) produced out-of-scope edits. Bounded-efficiency prompting
   (explicit scope + stop condition) was free: ≈1.0× reasoning, no success loss.
4. **Cache facts**: reasoning metadata is dropped by the gateway (upstream
   `reasoning_tokens` is authoritative); Claude Code's `total_cost_usd` is
   wrong for gateway models; Together's cache pre-warms Claude Code's static
   prefix across sessions (32/32 first-turn hits for K2.7-Code); nemotron got
   **0 cache hits in 96 PI.DEV runs** while caching normally via the gateway.

Full numbers: [RESULTS.md](RESULTS.md) · per-variant CSV:
[results/summaries/prompt_sensitivity.csv](results/summaries/prompt_sensitivity.csv) ·
cache ledger: [results/summaries/cache_behavior.csv](results/summaries/cache_behavior.csv)

### What remains (Phase 2, preregistered)

Full six-model screening over 16 dev tasks, frozen 8-task holdout
confirmation, per-model Claude Code budget pools, longer CC turn limits,
multi-turn stress variants (runner v2), and day/region/gateway replication —
detailed in [RESULTS.md §8](RESULTS.md).
