# Reasoning-token schema discovery (pi -> Together, chat completions)

| model | status | raw reasoning field | raw cached field | effective request params |
|---|---|---|---|---|
| deepseek-ai/DeepSeek-V4-Pro | explicit | completion_tokens_details.reasoning_tokens | prompt_tokens_details.cached_tokens | `{"reasoning": {"enabled": true}, "reasoning_effort": "high", "max_tokens": 384000}` |
| moonshotai/Kimi-K2.6 | explicit | completion_tokens_details.reasoning_tokens | prompt_tokens_details.cached_tokens | `{"reasoning": {"enabled": true}, "max_tokens": 131000}` |
| moonshotai/Kimi-K2.7-Code | explicit | completion_tokens_details.reasoning_tokens | prompt_tokens_details.cached_tokens | `{"reasoning": {"enabled": true}, "max_tokens": 131072}` |
| nvidia/nemotron-3-ultra-550b-a55b | explicit | completion_tokens_details.reasoning_tokens | prompt_tokens_details.cached_tokens | `{"reasoning": {"enabled": true}, "max_tokens": 506826}` |
| thinkingmachines/Inkling | explicit | completion_tokens_details.reasoning_tokens | prompt_tokens_details.cached_tokens | `{"reasoning": {"enabled": true}, "max_tokens": 131072}` |
| zai-org/GLM-5.2 | explicit | completion_tokens_details.reasoning_tokens | prompt_tokens_details.cached_tokens | `{"reasoning": {"enabled": true}, "max_tokens": 164000}` |
