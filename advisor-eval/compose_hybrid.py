#!/usr/bin/env python3
"""Compose hybrid predictions offline: rules -> triage -> Gemma.

hybrid(x) = rules_predict(x)            if rules hit
          = no_change (conf 0.8)        if no soft indicator
          = gemma_constrained(x)        otherwise

Semantically identical to running run_eval.py --system hybrid, but reuses the
full constrained-Gemma predictions instead of re-running inference.

Usage: compose_hybrid.py --data data/holdout.jsonl \
    --gemma results/holdout/gemma_con.jsonl --out results/holdout/hybrid.jsonl
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from advisor.rules import rules_predict, rules_detect, is_ambiguous  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--gemma", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    gem = {json.loads(l)["id"]: json.loads(l) for l in open(args.gemma)}
    routes = {"rules": 0, "clean": 0, "model": 0}
    with open(args.out, "w") as f:
        for l in open(args.data):
            ex = json.loads(l)
            prompt = ex["prompt"]
            if rules_detect(prompt):
                rec = {"id": ex["id"], "system": "hybrid",
                       "parsed": rules_predict(prompt),
                       "meta": {"latency_s": 0.0, "route": "rules"}}
                routes["rules"] += 1
            elif not is_ambiguous(prompt):
                rec = {"id": ex["id"], "system": "hybrid",
                       "parsed": {"recommendation": "no_change", "risks": [],
                                  "revised_prompt": None, "confidence": 0.8},
                       "meta": {"latency_s": 0.0, "route": "clean"}}
                routes["clean"] += 1
            else:
                g = gem[ex["id"]]
                rec = {"id": ex["id"], "system": "hybrid",
                       "parsed": g.get("parsed"),
                       "meta": {**g.get("meta", {}), "route": "model"}}
                routes["model"] += 1
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("routes:", routes)


if __name__ == "__main__":
    main()
