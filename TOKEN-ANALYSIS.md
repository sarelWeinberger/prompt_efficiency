# Token Waste Analysis — What pi Sends on Every Prompt

A field-by-field description of [pi-request.log](pi-request.log) — the exact HTTP request pi sends to Together AI — with **measured** token costs for every component, and how to eliminate the waste.

## TL;DR

For the one-word prompt **"hi"**, pi sends **1,291 input tokens**. Only **1 token is your message**. The rest:

| Component | Measured tokens | Share | Needed for chat? | Needed for coding? |
|---|---|---|---|---|
| Tool JSON schemas (read/bash/edit/write) | **~827** | 64% | ❌ waste | ✅ yes |
| pi's system prompt | **~399** | 31% | ❌ waste | ✅ mostly |
| — of which: pi self-documentation paths | ~200 | 15% | ❌ waste | ⚠️ only for pi questions |
| Chat template + envelope | ~64 | 5% | fixed | fixed |
| **Your message ("hi")** | **1** | **0.08%** | ✅ | ✅ |

**This overhead is re-sent on EVERY request** — the API is stateless, and the usage report shows `cacheRead: 0, cacheWrite: 0`, so Together applies no prompt caching for GLM-5.2. You pay full price for the same 1,290 tokens every single turn.

---

## 1. How the log was captured

A local Node HTTP proxy was placed between pi and `api.together.xyz` (see [ReadMe.md](ReadMe.md)). The log entry is the verbatim `POST /v1/chat/completions` request. The `authorization` header is redacted.

## 2. The HTTP layer

```
POST https://api.together.xyz/v1/chat/completions
```

| Header group | Content | Notes |
|---|---|---|
| `user-agent`, `x-stainless-*` | OpenAI JS SDK 6.26.0, Node v22.23.1, Linux x64, retry count, 300s timeout | pi uses the standard OpenAI SDK; these headers are telemetry, zero token cost |
| `authorization` | `Bearer tgp_v1_...` (redacted) | your Together AI key |
| `content-length` | 5,817 bytes | the entire body for one word of user input |

Headers cost no tokens — only the JSON body below is tokenized by the model.

## 3. The body, field by field

### 3.1 `model`
`"zai-org/GLM-5.2"` — the target model.

### 3.2 `stream` / `stream_options`
`stream: true` with `include_usage: true` — responses arrive as SSE chunks; the final chunk carries the token counts used in this analysis.

### 3.3 `max_tokens`
`164000` — pi requests the model's full output capacity every time. Costs nothing unless used.

### 3.4 `reasoning`
`{ "enabled": true }` — thinking mode on by default. On "hi" this produced 0 reasoning tokens, but on harder prompts reasoning tokens are billed as output. Disable with `--thinking off` if unwanted.

### 3.5 `messages[0]` — the system prompt (~399 measured tokens, 2,708 chars)

Five logical sections (token estimates are tokenizer-based, scaled to the measured total):

| # | Section | Est. tokens | What it says |
|---|---|---|---|
| 1 | Role intro | ~22 | "You are an expert coding assistant operating inside pi..." |
| 2 | Available-tools prose list | ~48 | one line each for read/bash/edit/write (redundant with the schemas in 3.7!) |
| 3 | Guidelines (11 bullets) | ~113 | edit-tool discipline (exact match, no overlaps, merge nearby edits), prefer bash for ls/rg, be concise |
| 4 | **pi self-documentation paths** | **~206** | absolute paths to pi's README/docs/examples under your nvm install, plus routing rules ("extensions → docs/extensions.md...") |
| 5 | Current working directory | ~10 | `/home/user/Desktop/PIDEV` |

**Biggest system-prompt waste: section 4** — half the system prompt tells the model where pi's own documentation lives. That's only useful when you ask pi about pi. On every other prompt it's ~200 dead tokens.

Note section 2 + section 3.7 describe the same four tools twice — once as prose, once as JSON schema.

### 3.6 `messages[1]` — your message
```json
{ "role": "user", "content": [{ "type": "text", "text": "hi" }] }
```
**1 token.** 0.08% of the request.

### 3.7 `tools` — four JSON schemas (~827 measured tokens)

| Tool | Est. tokens | Description sent to the model |
|---|---|---|
| `edit` | ~331 | the heaviest — long rules about exact-match text replacement, non-overlapping edits, merging nearby changes, repeated in 3 different property descriptions |
| `read` | ~215 | file reading, image support, 2000-line/50KB truncation rules, offset/limit |
| `bash` | ~158 | command execution, output truncation rules, timeout |
| `write` | ~123 | create/overwrite, auto-creates parent dirs |

The measured cost (827) exceeds the plain-JSON estimate (612) because the server re-renders schemas into the model's chat template with additional formatting — tool definitions cost **more** than their raw JSON suggests.

## 4. Measured ablations (ground truth)

Three live runs of `-p "hi"` against GLM-5.2, varying only the flags:

| Configuration | Input tokens | Cost/turn (input) | Savings vs baseline |
|---|---|---|---|
| baseline (default pi) | **1,291** | $0.00181 | — |
| `--no-tools` | **464** | $0.00065 | −827 tok (−64%) |
| `--no-tools --system-prompt "You are a helpful assistant."` | **71** | $0.00010 | −1,220 tok (−94%) |

(Input price derived from usage report: ~$1.40/M input, ~$4.40/M output for GLM-5.2 on Together.)

## 5. Why this matters: the overhead compounds

1. **Every turn resends everything.** Chat completions are stateless. A 50-turn session pays the 1,290-token overhead 50 times = ~64,500 tokens ≈ $0.09 before any actual conversation content.
2. **History grows on top.** Each turn also resends all previous messages and tool results. The overhead is the *floor*, not the ceiling.
3. **No caching discount here.** `cacheRead: 0, cacheWrite: 0` in every response — unlike Anthropic/OpenAI prompt caching, this Together AI + GLM-5.2 path gave no cached-token discount, so the identical re-sent prefix is billed at full rate every time.

## 6. How to cut the waste

| If you want... | Do this | Saves |
|---|---|---|
| Plain Q&A, no file access | `pi --no-tools -p "..."` | ~827 tok/turn |
| Q&A with your own persona | add `--system-prompt "..."` | ~393 more tok/turn |
| Coding, but no pi-docs ballast | `--append-system-prompt` won't remove it — use a full `--system-prompt` that keeps the tool guidelines but drops the pi-docs section | ~200 tok/turn |
| No thinking tokens on output | `--thinking off` | variable |
| Fewer tools (e.g. read-only) | `--tools read,bash` | ~450 tok/turn |

## 7. Method notes

- Measured numbers come from the API's own `usage` object (authoritative). Per-section splits use `gpt-tokenizer` (cl100k) scaled to measured totals — GLM's tokenizer differs, so treat splits as ±10%.
- Baseline input varied slightly between runs (1,319 vs 1,291) — pi embeds the current working directory in the system prompt, and run context differs.
- Reproduce any measurement:
  ```bash
  pi --provider together --model "zai-org/GLM-5.2" --no-session -p --mode json "hi" | grep turn_end
  ```
