#!/bin/bash
# Stop the gateway chain started by start_gateway.sh.
LOGDIR="${1:?usage: stop_gateway.sh <log_dir>}"
for p in proxy8901 litellm proxy8903; do
  if [ -f "$LOGDIR/$p.pid" ]; then
    kill "$(cat "$LOGDIR/$p.pid")" 2>/dev/null || true
    rm -f "$LOGDIR/$p.pid"
  fi
done
echo "gateway stopped"
