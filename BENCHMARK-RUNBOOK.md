# Benchmark Runbook

How to reproduce every part of the prompt-efficiency benchmark. All commands run
from the repository root. Real API spend is billed to the Together key in `.env`.

## 0. One-time setup

```bash
# toolchains: python3.12+PyYAML, go (>=1.24 at /usr/local/go), node 22 via nvm
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh"
npm install -g --ignore-scripts @earendil-works/pi-coding-agent   # pi 0.82.1
npm install -g @anthropic-ai/claude-code                          # claude 2.1.220
python3 -m venv .venv-gateway && .venv-gateway/bin/pip install "litellm[proxy]"  # 1.93.0

# secrets in .env (git-ignored): togever_ai=<together key>, GATEWAY_MASTER_KEY=<any>
# pi auth: ~/.pi/agent/auth.json  { "together": { "type": "api_key", "key": "..." } }
```

## 1. Materialize tasks and prompts

```bash
python3 benchmark/scaffold_py.py && python3 benchmark/scaffold_js.py && python3 benchmark/scaffold_go.py
python3 src/generate_prompts.py         # 432 prompts, validation must be clean
python3 -m unittest discover -s tests -t .   # 19 checks must pass
```

## 2. Start the Claude Code gateway (needed for any claude-code runs)

```bash
export TOGETHER_API_KEY=$(grep '^togever_ai=' .env | cut -d= -f2)
export GATEWAY_MASTER_KEY=$(grep '^GATEWAY_MASTER_KEY=' .env | cut -d= -f2)
bash benchmark/gateway/start_gateway.sh results/raw/gateway-live   # waits until ready
# chain: claude -> :8903 capture -> :4000 litellm -> :8901 capture -> Together
bash benchmark/gateway/stop_gateway.sh results/raw/gateway-live    # to stop
```

The LiteLLM config (benchmark/gateway/litellm.yaml) MUST keep
`model_info.supports_function_calling: true` per model and MUST NOT set
`drop_params: true` — without these LiteLLM silently drops tool schemas and
every agent loop dies (documented failure, results/compatibility/).

## 3. Compatibility smoke suite (before any claude-code benchmark)

```bash
python3 src/cc_smoke.py            # all 6 models; ~$0.5, ~2 min
cat results/compatibility/cc_compat.md
```

## 4. Schema discovery

```bash
python3 src/discover_schema.py     # 12 probes; writes results/schema_discovery/
```

## 5. Pilots

```bash
python3 src/run_benchmark.py --experiment pilot_a --workers 6 \
    --max-cost 8 --max-nocache-cost 25            # PI.DEV 360 runs
python3 src/run_benchmark.py --experiment pilot_b \
    --max-cost 10 --max-nocache-cost 45           # Claude Code 252 runs
```

The runner is resumable: re-running the same command skips completed cells
(runs.jsonl is the ledger; infra_error cells are retried). Budget caps stop
scheduling, never kill in-flight runs. Timeouts (240/360/480 s by complexity)
kill the harness process group and record a timeout outcome.

Ad-hoc cells:

```bash
python3 src/run_benchmark.py --harnesses pi --models zai-org/GLM-5.2 \
    --tasks py-low-01 --variants baseline,deep_thinking --reps 2 --workers 2
```

## 6. Cache experiment (Experiment C)

```bash
python3 src/run_cache_experiment.py pi   # pi-side conditions, any time
python3 src/run_cache_experiment.py cc   # ONLY when no pilot-B runs in flight
```

## 7. Analysis

```bash
python3 analysis/analyze_results.py      # -> results/summaries/prompt_sensitivity.csv
python3 analysis/cache_analysis.py       # -> results/summaries/cache_behavior.csv
```

## Safety and hygiene

- Agents run only inside /tmp/pi-prompt-benchmark/slot-* disposable dirs.
- Claude Code runs get an isolated HOME per run; never the real one.
- `bypassPermissions` is allowed only inside slots (config: permission experiment).
- Raw captures are redacted at write time (capture-proxy + common.redact).
- Hidden tests live in benchmark/evaluators/ and are never present in a slot
  while an agent is running.
- results/raw/ is git-ignored; keep representative samples only.
