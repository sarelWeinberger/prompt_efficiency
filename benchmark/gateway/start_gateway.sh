#!/bin/bash
# Start the Claude Code -> Together AI gateway chain:
#   claude (ANTHROPIC_BASE_URL=:8903)
#     -> capture-proxy :8903 (anthropic-facing log)        [gateway_inbound.jsonl]
#     -> litellm :4000 (Anthropic Messages -> OpenAI chat) [litellm.log]
#     -> capture-proxy :8901 (together-facing log)         [together_capture.jsonl]
#     -> api.together.xyz
#
# Usage: start_gateway.sh <log_dir>
# Requires: TOGETHER_API_KEY, GATEWAY_MASTER_KEY exported; node + venv litellm installed.
set -euo pipefail
LOGDIR="${1:?usage: start_gateway.sh <log_dir>}"
mkdir -p "$LOGDIR"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
NODE="${NODE_BIN:-$HOME/.nvm/versions/node/v22.23.1/bin/node}"
LITELLM="$ROOT/.venv-gateway/bin/litellm"

: "${TOGETHER_API_KEY:?TOGETHER_API_KEY must be exported}"
: "${GATEWAY_MASTER_KEY:?GATEWAY_MASTER_KEY must be exported}"

"$NODE" "$ROOT/benchmark/gateway/capture-proxy.js" 8901 https://api.together.xyz \
  "$LOGDIR/together_capture.jsonl" together >"$LOGDIR/proxy8901.log" 2>&1 &
echo $! > "$LOGDIR/proxy8901.pid"

"$LITELLM" --config "$ROOT/benchmark/gateway/litellm.yaml" --port 4000 \
  >"$LOGDIR/litellm.log" 2>&1 &
echo $! > "$LOGDIR/litellm.pid"

"$NODE" "$ROOT/benchmark/gateway/capture-proxy.js" 8903 http://127.0.0.1:4000 \
  "$LOGDIR/gateway_inbound.jsonl" anthropic >"$LOGDIR/proxy8903.log" 2>&1 &
echo $! > "$LOGDIR/proxy8903.pid"

# Wait for litellm to come up (it is the slow one).
for i in $(seq 1 60); do
  if curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:4000/health/liveliness | grep -q 200; then
    echo "gateway ready"
    exit 0
  fi
  sleep 1
done
echo "gateway failed to start; see $LOGDIR/litellm.log" >&2
exit 1
