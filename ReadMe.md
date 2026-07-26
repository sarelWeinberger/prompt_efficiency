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
