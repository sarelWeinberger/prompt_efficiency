#!/usr/bin/env python3
"""BF16 (transformers, CPU) quantization-sensitivity check + runtime numbers.

Runs a stratified 10-example holdout subset through the unquantized model and
records load time, RSS, latencies, and predictions in the shared format.
Run with the eval venv python (transformers 5.14.1). Stop llama-server first.

Usage: .venv/bin/python bench_bf16.py --data data/holdout.jsonl \
           --out results/holdout/bf16_subset.jsonl
"""
import argparse
import json
import os
import resource
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from advisor.prompt import build_messages  # noqa: E402
from run_eval import parse_json_loose  # noqa: E402

MODEL = "google/gemma-4-E2B-it"
REV = "3e22461f65e89153144f8adb70e3b8c2cc9845a7"

# frozen subset: 5 warn / 5 clean, chosen by fixed ids (mix of categories)
SUBSET = [
    "hold-pos-go-high-02-multiple_approaches",
    "hold-pos-js-low-02-max_certainty",
    "hold-par-dt-1",
    "hold-mix-ac",
    "hold-he-ma",
    "hold-neu-go-high-02-baseline",
    "hold-leg-verify",
    "hold-leg-options",
    "hold-he-clean",
    "hold-neu-js-high-03-verbose_repetition",
]


def rss_gib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-new", type=int, default=1400)
    args = ap.parse_args()

    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    torch.manual_seed(0)
    torch.set_num_threads(4)

    # tokenizer-only path: the multimodal AutoProcessor needs torchvision,
    # which this environment does not have and which the text-only advisor
    # task does not require.
    t0 = time.monotonic()
    processor = AutoTokenizer.from_pretrained(MODEL, revision=REV)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, revision=REV, dtype=torch.bfloat16)
    model.eval()
    load_s = time.monotonic() - t0
    print(f"load: {load_s:.1f}s rss={rss_gib():.2f}GiB")

    rows = {json.loads(l)["id"]: json.loads(l) for l in open(args.data)}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(json.dumps({"id": "_meta", "load_s": load_s,
                            "rss_after_load_gib": rss_gib(),
                            "torch_threads": 4, "dtype": "bfloat16"}) + "\n")
        for sid in SUBSET:
            ex = rows[sid]
            msgs = build_messages(ex["prompt"])
            ids = processor.apply_chat_template(
                msgs, add_generation_prompt=True, return_tensors="pt")
            n_in = ids.shape[-1]
            t0 = time.monotonic()
            with torch.no_grad():
                out = model.generate(ids, max_new_tokens=args.max_new,
                                     do_sample=False)
            dt = time.monotonic() - t0
            new = out[0][n_in:]
            text = processor.decode(new, skip_special_tokens=True)
            rec = {"id": sid, "system": "bf16", "raw": text,
                   "parsed": parse_json_loose(text),
                   "meta": {"latency_s": round(dt, 1),
                            "prompt_tokens": int(n_in),
                            "completion_tokens": int(len(new)),
                            "rss_gib": round(rss_gib(), 2)}}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{sid}: {dt:.0f}s {len(new)}tok -> "
                  f"{(rec['parsed'] or {}).get('recommendation', 'PARSE_FAIL')}")


if __name__ == "__main__":
    main()
