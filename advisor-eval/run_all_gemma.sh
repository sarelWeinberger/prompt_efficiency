#!/usr/bin/env bash
# Sequential Gemma runs against the already-running llama-server.
# Order: finish dev (exploratory) -> holdout unconstrained -> holdout constrained
#        -> thinking probe. Each step resumes if interrupted.
set -u
cd "$(dirname "$0")"
log() { echo "[$(date +%H:%M:%S)] $*"; }

log "dev unconstrained"
python3 run_eval.py --system gemma --data data/dev.jsonl \
  --out results/dev/gemma_uncon.jsonl --resume > results/dev/gemma_uncon.log 2>&1
log "dev done: $(wc -l < results/dev/gemma_uncon.jsonl)"

log "holdout unconstrained"
python3 run_eval.py --system gemma --data data/holdout.jsonl \
  --out results/holdout/gemma_uncon.jsonl --resume > results/holdout/gemma_uncon.log 2>&1
log "holdout uncon done: $(wc -l < results/holdout/gemma_uncon.jsonl)"

log "holdout constrained"
python3 run_eval.py --system gemma --constrained --data data/holdout.jsonl \
  --out results/holdout/gemma_con.jsonl --resume > results/holdout/gemma_con.log 2>&1
log "holdout con done: $(wc -l < results/holdout/gemma_con.jsonl)"

log "thinking probe"
python3 probe_thinking.py --data data/holdout.jsonl \
  --out results/holdout/think_probe.jsonl > results/holdout/think_probe.log 2>&1
log "ALL GEMMA RUNS COMPLETE"
