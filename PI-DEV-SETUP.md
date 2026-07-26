# PI.DEV + Together AI — Installed & Configured

## What was installed

1. **nvm** (Node Version Manager) → `~/.nvm`
2. **Node.js v22.23.1** (via nvm, set as default)
3. **PI.DEV v0.82.1** (`@earendil-works/pi-coding-agent`, installed globally via npm)

## Configuration

- **API key**: stored in `~/.pi/agent/auth.json` (provider `together`, key from `.env`)
- **Defaults**: `~/.pi/agent/settings.json` sets:
  - `defaultProvider`: `together`
  - `defaultModel`: `moonshotai/Kimi-K2.7-Code`

## Usage

Open a **new terminal** (so nvm is loaded from `.bashrc`), then:

```bash
pi                          # interactive TUI with default model
pi -p "your prompt"         # non-interactive, print and exit
pi --list-models together   # list available Together AI models
pi --model "zai-org/GLM-5.2"  # use a different model
```

Switch models mid-session with Ctrl+P, or change the default in `~/.pi/agent/settings.json`.

## Available Together AI models (as of install)

- deepseek-ai/DeepSeek-V4-Pro (512K context)
- moonshotai/Kimi-K2.7-Code (coding-focused, current default)
- moonshotai/Kimi-K2.6
- Qwen/Qwen3.7-Max (1M context)
- zai-org/GLM-5.2
- meta-llama/Llama-3.3-70B-Instruct-Turbo
- nvidia/nemotron-3-ultra-550b-a55b
- ...and more (`pi --list-models together`)

## Docs

- PI.DEV repo: https://github.com/earendil-works/pi
- Local docs: `~/.nvm/versions/node/v22.23.1/lib/node_modules/@earendil-works/pi-coding-agent/docs/`

**Note**: Keep your API key secure. Never commit `.env` or `auth.json` to version control.
