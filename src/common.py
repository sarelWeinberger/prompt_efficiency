"""Shared utilities: config, secrets, hashing, redaction, pricing."""
import hashlib
import json
import os
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "benchmark"
NODE_BIN = Path.home() / ".nvm/versions/node/v22.23.1/bin"
GENERATOR_VERSION = 1


def load_config():
    return yaml.safe_load((BENCH / "config.yaml").read_text())


def load_models():
    return yaml.safe_load((BENCH / "models.yaml").read_text())["models"]


def model_cost(model_id):
    for m in load_models():
        if m["id"] == model_id:
            return m["cost"]
    raise KeyError(model_id)


def load_task(task_id):
    return json.loads((BENCH / "tasks" / f"{task_id}.json").read_text())


def all_task_ids():
    return sorted(p.stem for p in (BENCH / "tasks").glob("*.json"))


def env_secret(name):
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError(f"{name} missing from .env")


def secrets():
    out = []
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            v = line.split("=", 1)[1].strip()
            if len(v) >= 8:
                out.append(v)
    return out


_KEY_PAT = re.compile(r"(tgp_v1_|sk-ant-|github_pat_|ghp_|sk-bench-)[A-Za-z0-9_\-]{8,}")


def redact(text):
    for s in secrets():
        text = text.replace(s, "[REDACTED]")
    return _KEY_PAT.sub(r"\1[REDACTED]", text)


def sha256(data):
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def dir_hash(path):
    """Deterministic content hash of a directory tree (excluding .git)."""
    h = hashlib.sha256()
    path = Path(path)
    for p in sorted(path.rglob("*")):
        if ".git" in p.parts or not p.is_file():
            continue
        h.update(str(p.relative_to(path)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def append_jsonl(path, record):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def estimate_tokens(text):
    """Crude chars/4 estimate, labeled as such wherever it is stored."""
    return max(1, len(text) // 4)


def run_env(extra=None):
    """Environment for harness subprocesses: node + go on PATH."""
    env = dict(os.environ)
    env["PATH"] = f"{NODE_BIN}:/usr/local/go/bin:" + env.get("PATH", "/usr/bin:/bin")
    if extra:
        env.update(extra)
    return env
