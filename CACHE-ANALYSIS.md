# Continuous-Session Cache Analysis — Together AI Prompt Caching, Measured

Follow-up to [TOKEN-ANALYSIS.md](TOKEN-ANALYSIS.md). That doc found `cacheRead: 0` on single-shot runs and concluded "no caching discount." **In continuous multi-turn sessions, that conclusion flips**: Together applies automatic prefix caching — but unreliably.

## Method

Real multi-turn conversations (not repeated one-shots): each turn continues the same pi session with `-c`, so the request contains the full prior history — exactly like an interactive chat. Per-turn numbers come from the API's own `usage` object.

```bash
pi --provider together --model <M> --session-dir <dir> -p --mode json "msg1"   # turn 1
pi --provider together --model <M> --session-dir <dir> -c -p --mode json "msg2" # turns 2+
```

## Raw results

### GLM-5.2 — 5-turn session

| Turn | Input (uncached) | Cache read | Output | Cost | Cache? |
|---|---|---|---|---|---|
| 1 | 1,355 | 0 | 42 | $0.00208 | cold start |
| 2 | **35** | **1,344** | 77 | **$0.00074** | ✅ full hit |
| 3 | 1,257 | 192 | 57 | $0.00206 | ⚠️ partial (85% missed) |
| 4 | 1,518 | 0 | 96 | $0.00255 | ❌ full miss |
| 5 | **140** | **1,472** | 37 | **$0.00074** | ✅ full hit |

Session total: **$0.00817**. Without any caching it would have been ~$0.0116 — caching saved **~29%**, but a reliable cache would have saved ~55%.

### DeepSeek-V4-Pro — 3 turns

| Turn | Input | Cache read | Output | Cost | Cache? |
|---|---|---|---|---|---|
| 1 | 1,582 | 0 | 50 | $0.00293 | cold |
| 2 | 110 | 1,536 | 58 | $0.00070 | ✅ hit |
| 3 | 1,715 | 0 | 49 | $0.00316 | ❌ miss |

### Kimi-K2.6 — 3 turns

| Turn | Input | Cache read | Output | Cost | Cache? |
|---|---|---|---|---|---|
| 1 | 407 | **768** | 37 | $0.00081 | ✅ **hit on turn 1!** |
| 2 | 58 | 1,152 | 141 | $0.00094 | ✅ hit |
| 3 | 119 | 1,152 | 136 | $0.00099 | ✅ hit |

## Pricing (from pi's Together catalog, $/M tokens)

| Model | Input | Cached input | Cache write | Discount on hit |
|---|---|---|---|---|
| GLM-5.2 | $1.40 | $0.26 | **$0** | **81%** |
| DeepSeek-V4-Pro | $1.74 | $0.20 | **$0** | **89%** |
| Kimi-K2.6 | $1.20 | $0.20 | **$0** | **83%** |

## Findings

1. **Together's caching is automatic and free to populate.** No API flag, no `cache_control` blocks (unlike Anthropic), and `cacheWrite` is billed at $0. You get it without doing anything.

2. **A cache hit collapses the bill.** GLM turn 2 sent a ~1,379-token prompt but paid full price on only 35 tokens — the turn cost $0.00074 instead of $0.00227 (−67%).

3. **Hits are probabilistic, not guaranteed.** GLM went hit → partial → miss → hit on identical-prefix requests seconds apart; DeepSeek missed on turn 3 and re-billed all 1,715 tokens. The likely cause: requests are load-balanced across replicas and only some hold your prefix in KV-cache. Observed continuation hit rates in this sample: GLM 2.5/4, DeepSeek 1/2, Kimi 3/3.

4. **The cache is shared across sessions (and possibly users).** Kimi got a 768-token cache hit on the *first* turn of a brand-new session — pi's static system-prompt+tools prefix was already cached from an earlier, unrelated request. A stable harness prefix is cache gold.

5. **Single-shot `--no-session` runs never showed hits** (all the TOKEN-ANALYSIS runs). Continuous sessions are what make the prefix hot and reusable within a short window.

6. **Misses compound with history growth.** By GLM turn 4, a miss re-billed 1,518 tokens (overhead + all prior turns) at full rate. The longer the session, the more expensive each miss.

## Practical guidance

- **Keep your prefix byte-stable.** Any change to the system prompt or tool set invalidates everything after it. (pi does this correctly — its system prompt only varies with the working directory.)
- **Budget on list price, treat cache as a rebate.** With hit rates this variable you can't rely on the discount — in this sample it materialized on ~60% of continuation turns.
- **Trimming waste still matters most.** An 81% discount on 1,290 wasted tokens still costs more than not sending 827 of them (`--no-tools`) when you don't need tools — and on every miss you pay the full toll.
- **Send follow-ups promptly.** KV-caches evict quickly under load; long pauses between turns likely lower hit odds.

## Caveats

- Small sample (11 requests, one afternoon, one region). Hit rates will vary with Together's load and routing.
- "Partial hit" (GLM turn 3, 192 tokens) suggests block-level prefix caching — only the first cache blocks matched.
- Prices from pi's bundled catalog; verify against Together's current price list before extrapolating.
