# Claude Code compatibility matrix (gateway: litellm 1.93.0)

| capability | deepseek-v4-pro | kimi-k2-6 | kimi-k2-7-code | nemotron-3-ultra | inkling | glm-5-2 |
|---|---|---|---|---|---|---|
| text_completion | supported | supported | supported | supported | supported | supported |
| system_prompt | supported | supported | supported | supported | supported | supported |
| streaming | supported | supported | supported | supported | supported | supported |
| tool_definition | supported | supported | supported | supported | supported | supported |
| single_tool_call | supported | supported | supported | supported | supported | supported |
| sequential_tool_calls | partially_supported | supported | supported | supported | partially_supported | partially_supported |
| tool_result_continuation | unknown | supported | supported | supported | unknown | unknown |
| long_output | supported | supported | supported | supported | supported | supported |
| reasoning_token_reporting | unsupported | supported | supported | supported | supported | supported |
| cached_input_reporting | supported | supported | supported | supported | supported | supported |
| error_propagation | supported | supported | supported | supported | supported | supported |
| timeout_handling | supported | supported | supported | supported | supported | supported |
| stop_reason | supported | supported | supported | supported | supported | supported |
| context_continuation | supported | supported | supported | supported | supported | supported |
| **tool_loop_valid** | False | True | True | True | False | False |
