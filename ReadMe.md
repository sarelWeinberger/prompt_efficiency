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

**Status: preregistered program COMPLETE** — infrastructure, pilots, full
six-model screening (1,728-run pi matrix), stress family, and frozen-holdout
confirmation. 4,400 valid runs, $152.54 total spend. Headline: *"develop
several approaches and compare"* is the most wasteful phrase tested
(2.4–7.4× reasoning, all six models, holdout-confirmed); bounded-efficiency
prompting is free everywhere and halves GLM-5.2's reasoning. Open item:
second-gateway/region replication.

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
| [RESULTS.md](RESULTS.md) | Final results: holdout-confirmed waste features, hypothesis scoreboard |
| [PROMPT-WASTE-RULES.md](PROMPT-WASTE-RULES.md) | Holdout-validated prompting rules (cross-model + per-model) |

Infrastructure: [benchmark/](benchmark/) (frozen configs, 24 tasks, fixtures,
hidden evaluators, LiteLLM gateway), [src/](src/) (runners, parsers, orchestrator),
[analysis/](analysis/), [tests/](tests/), machine-readable outputs under
[results/](results/) (`runs.jsonl`, `summaries/*.csv`, compatibility and
schema-discovery records).

### What the benchmark measured (final)

| | |
|---|---|
| Models | DeepSeek-V4-Pro, Kimi-K2.6, Kimi-K2.7-Code, nemotron-3-ultra-550b-a55b, Inkling, GLM-5.2 (frozen) |
| Harnesses | PI.DEV 0.82.1 (direct) and Claude Code 2.1.220 (via LiteLLM 1.93.0 gateway, dual-side redacted capture) |
| Valid runs | **4,400** — pilots 460, pi screening 1,728/1,728 (full matrix), CC screening 371, stress family 432, pi holdout 1,198/1,200, CC holdout 211, cache sessions 70 |
| Spend | $152.54 actual / $390.53 estimated no-cache (caching rebated ~61%) |
| Collection | Three days (2026-07-26→28); findings replicate across all three |

### Headline findings (holdout-confirmed)

1. **"Develop several approaches and compare before choosing" is the most
   wasteful phrase tested** — 2.4–7.4× reasoning tokens on all six models,
   zero correctness gain, confirmed on 8 never-seen holdout tasks.
2. **Deep-thinking incantations confirmed wasteful** (1.6–2.2×) on every
   model where selected — replicated across pilot, screening, and holdout.
3. **Bounded-efficiency prompting confirmed free on all six models** and
   *halves* GLM-5.2's reasoning (0.48×). Explicit scope + stop conditions
   cost nothing, ever.
4. **A wrong architectural hint costs 2.6×** (models chase red herrings);
   ambiguous scope is the only input defect that hurts correctness (83%
   success); irrelevant prose is nearly free (1.03×) — models filter noise.
5. **The harness dwarfs the prompt**: same model, same task = 5–30× more per
   success under Claude Code (16–20k-token prefix × 2–7× turns), and prompt
   effects flip direction between harnesses.

Full numbers: [RESULTS.md](RESULTS.md) · screening CSV:
[results/summaries/prompt_sensitivity_screening.csv](results/summaries/prompt_sensitivity_screening.csv) ·
holdout verdicts: [results/summaries/holdout_confirmation.csv](results/summaries/holdout_confirmation.csv) ·
stress family: [results/summaries/stress_family.csv](results/summaries/stress_family.csv) ·
cache ledger: [results/summaries/cache_behavior.csv](results/summaries/cache_behavior.csv)

### Open items

Second-gateway/region replication; normalized-harness comparison (design §9);
permission-mode contrast (§14); harder task tiers to break the pi success
ceiling. Detailed in [RESULTS.md §7](RESULTS.md).
