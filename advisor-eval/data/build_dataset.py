#!/usr/bin/env python3
"""Build the prompt-advisor evaluation dataset (dev + frozen holdout).

Deterministic: no randomness; repo-derived examples are selected by fixed
rotation over sorted task ids; authored examples are literals in this file.

Sources
-------
1. repo_positive / repo_neutral / repo_ambiguous: real prompt texts from
   benchmark/generated_prompts/<task>/<variant>.json (the exact prompts whose
   token-waste effects were measured in RESULTS.md / CLAUDE-API-COMPARISON.md).
   Split follows the benchmark's own task split (16 dev / 8 holdout tasks) so
   holdout prompts come from tasks never seen during advisor development.
2. authored: paraphrases, legit look-alikes, mixed prompts, Hebrew,
   preservation-heavy, and adversarial-rewrite examples written before the
   protocol freeze (see PROTOCOL.md).

Label policy (frozen; derived from measured results, not intuition)
------------------------------------------------------------------
warn families (measured wasteful somewhere in the benchmark):
  multiple_approaches   2.4-7.4x all 6 open models + 2.5-2.7x sonnet-5
  max_certainty         1.85x DeepSeek, 4.13x sonnet-5 under Claude Code
  deep_thinking         1.6-2.2x on 5/5 open models (mild 1.25-1.3x on sonnet)
  exhaustive_exploration 1.90x sonnet-5/pi; 4x+ amplification under CC (H14)
  adjacent_cleanup      3.1x Inkling, 4.3x GLM, 1.58x sonnet-CC + oos edits
  missing_stop_conditions  stress ambiguous_scope: 83% success, 1.44x
no_change variants (measured neutral):
  baseline, verbose_repetition (~1.0x everywhere), bounded_efficiency
  (0.48-1.16x), no_questions_autonomy (holdout 1.00x; scope risk only),
  scoped_authorization, irrelevant_context (1.03x), goal_only
  (harness-dependent sign, H12 -> do not warn).
"unbounded verification" is folded into max_certainty (the measured
max_certainty template *is* an unbounded verification instruction).
"""
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
GP = os.path.join(ROOT, "benchmark", "generated_prompts")
TASKS = os.path.join(ROOT, "benchmark", "tasks")

WARN_FAMILIES = {
    "multiple_approaches": "multiple_approaches",
    "max_certainty": "max_certainty",
    "deep_thinking": "deep_thinking",
    "exhaustive_exploration": "exhaustive_exploration",
    "adjacent_cleanup": "adjacent_cleanup",
}
NEUTRAL_VARIANTS = [
    "baseline",
    "verbose_repetition",
    "bounded_efficiency",
    "no_questions_autonomy",
    "scoped_authorization",
    "irrelevant_context",
]

PATH_RE = re.compile(r"[\w./-]+\.(?:py|go|js|ts|yaml|yml|md|json|rs)\b|[\w-]+/[\w./-]+")
NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def load_tasks():
    tasks = {}
    for f in sorted(os.listdir(TASKS)):
        if f.endswith(".json"):
            d = json.load(open(os.path.join(TASKS, f)))
            tasks[d["id"]] = d
    return tasks


def variant_text(task_id, variant):
    d = json.load(open(os.path.join(GP, task_id, variant + ".json")))
    return d["text"]


def repo_protected(task, prompt):
    """Deterministic list of strings a safe rewrite must preserve."""
    prot = set()
    if task.get("test_cmd") and task["test_cmd"] in prompt:
        prot.add(task["test_cmd"])
    for m in PATH_RE.finditer(prompt):
        s = m.group(0)
        if "/" in s or s.endswith((".py", ".go", ".js", ".ts", ".md")):
            prot.add(s.rstrip(".,)"))
    crit = task.get("criteria", "")
    if crit and crit in prompt:
        for n in NUM_RE.findall(crit):
            prot.add(n)
    return sorted(prot)


def injected_tail(task_id, variant):
    """The sentence(s) the variant template appends after the baseline body."""
    base = variant_text(task_id, "baseline")
    var = variant_text(task_id, variant)
    i = 0
    while i < min(len(base), len(var)) and base[i] == var[i]:
        i += 1
    tail = var[i:].strip()
    assert tail and tail in var, (task_id, variant)
    return tail


def mk(id_, split, category, prompt, rec, risks=None, protected=None,
       source="authored", notes="", alt_ok=None):
    return {
        "id": id_,
        "split": split,
        "category": category,
        "source": source,
        "prompt": prompt,
        "gold": {
            "recommendation": rec,
            "risks": risks or [],
            # families that are acceptable secondary flags on the gold span
            # (neither TP nor FP): e.g. the deep_thinking template literally
            # contains certainty language, so max_certainty there is not wrong.
            "alt_ok": alt_ok or [],
            "protected": protected or [],
            "notes": notes,
        },
    }


def build_repo_examples(tasks):
    dev_tasks = sorted(t for t, d in tasks.items() if d["split"] == "dev")
    hold_tasks = sorted(t for t, d in tasks.items() if d["split"] == "holdout")
    out = []

    # positives: dev = 5 families x 4 rotating dev tasks; holdout = 5 x all 8
    fams = sorted(WARN_FAMILIES)
    for fi, fam in enumerate(fams):
        chosen = [dev_tasks[(fi * 4 + k) % len(dev_tasks)] for k in range(4)]
        # the deep_thinking template contains "be absolutely certain ...
        # verify your reasoning repeatedly": max_certainty is an acceptable
        # secondary flag there (and vice versa for the max_certainty template's
        # "re-verify repeatedly", which reads as deep verification pressure).
        alt = {"deep_thinking": ["max_certainty"],
               "max_certainty": ["deep_thinking"]}.get(fam, [])
        for t in chosen:
            p = variant_text(t, fam)
            out.append(mk(
                f"dev-pos-{t}-{fam}", "dev", "repo_positive", p, "warn",
                risks=[{"type": WARN_FAMILIES[fam], "gold_spans": [injected_tail(t, fam)]}],
                protected=repo_protected(tasks[t], p),
                source=f"repo:{t}/{fam}", alt_ok=alt))
        for t in hold_tasks:
            p = variant_text(t, fam)
            out.append(mk(
                f"hold-pos-{t}-{fam}", "holdout", "repo_positive", p, "warn",
                risks=[{"type": WARN_FAMILIES[fam], "gold_spans": [injected_tail(t, fam)]}],
                protected=repo_protected(tasks[t], p),
                source=f"repo:{t}/{fam}", alt_ok=alt))

    # neutrals: dev = 6 variants x 3 rotating tasks; holdout = 6 x 4 rotating
    for vi, v in enumerate(NEUTRAL_VARIANTS):
        for k in range(3):
            t = dev_tasks[(vi * 3 + k) % len(dev_tasks)]
            p = variant_text(t, v)
            out.append(mk(f"dev-neu-{t}-{v}", "dev", "repo_neutral", p,
                          "no_change", protected=repo_protected(tasks[t], p),
                          source=f"repo:{t}/{v}"))
        for k in range(4):
            t = hold_tasks[(vi * 4 + k) % len(hold_tasks)]
            p = variant_text(t, v)
            out.append(mk(f"hold-neu-{t}-{v}", "holdout", "repo_neutral", p,
                          "no_change", protected=repo_protected(tasks[t], p),
                          source=f"repo:{t}/{v}"))

    # ambiguous_scope -> warn missing_stop_conditions (stress family evidence)
    for split, tl in (("dev", dev_tasks[:3]), ("holdout", hold_tasks[:3])):
        for t in tl:
            p = variant_text(t, "ambiguous_scope")
            out.append(mk(
                f"{split}-amb-{t}", split, "repo_ambiguous", p, "warn",
                risks=[{"type": "missing_stop_conditions", "gold_spans": [p.strip()]}],
                source=f"repo:{t}/ambiguous_scope",
                notes="stress family: ambiguous scope, no criteria, no stop"))
    return out


# --------------------------------------------------------------------------
# Authored examples. Written 2026-08-02 before the protocol freeze; holdout
# authored examples were not iterated on after first evaluation runs.
# --------------------------------------------------------------------------

def W(t, span):
    return {"type": t, "gold_spans": [span]}


AUTHORED = [
    # ---------------- DEV: paraphrases ----------------
    mk("dev-par-ma-1", "dev", "paraphrase",
       "Fix the retry logic in net/backoff.py so the delay caps at 30s. "
       "Verify with: python3 -m pytest tests/test_backoff.py. "
       "Come up with a handful of different ways you could do this and weigh "
       "them against each other before you write any code.",
       "warn",
       [W("multiple_approaches", "Come up with a handful of different ways you could do this and weigh them against each other before you write any code")],
       ["net/backoff.py", "python3 -m pytest tests/test_backoff.py", "30"]),
    mk("dev-par-mc-1", "dev", "paraphrase",
       "Correct the timezone handling in sched/cron.go (jobs fire an hour late "
       "after DST). Test: go test ./sched/. Keep double- and triple-checking "
       "your work until you are positive nothing whatsoever can be wrong.",
       "warn",
       [W("max_certainty", "Keep double- and triple-checking your work until you are positive nothing whatsoever can be wrong")],
       ["sched/cron.go", "go test ./sched/"]),
    mk("dev-par-dt-1", "dev", "paraphrase",
       "The slug generator in utils/slug.js drops non-ASCII characters. Fix it "
       "to transliterate instead. Test: npx jest slug. Please mull this over "
       "at great length and reflect on every possible implication before "
       "editing anything.",
       "warn",
       [W("deep_thinking", "mull this over at great length and reflect on every possible implication before editing anything")],
       ["utils/slug.js", "npx jest slug"]),
    mk("dev-par-ee-1", "dev", "paraphrase",
       "Bug: the rate limiter in mw/limit.py counts HEAD requests twice. Fix "
       "it. Verify: python3 -m pytest tests/test_limit.py. First, get "
       "acquainted with the entire repository — open every module so you know "
       "the whole system inside out before starting.",
       "warn",
       [W("exhaustive_exploration", "get acquainted with the entire repository — open every module so you know the whole system inside out before starting")],
       ["mw/limit.py", "python3 -m pytest tests/test_limit.py"]),
    mk("dev-par-ac-1", "dev", "paraphrase",
       "Fix the crash in exporters/pdf.go when the title is empty (nil deref "
       "around line 120). Test: go test ./exporters/. While you're in that "
       "corner of the code, spruce up anything else that looks shabby.",
       "warn",
       [W("adjacent_cleanup", "While you're in that corner of the code, spruce up anything else that looks shabby")],
       ["exporters/pdf.go", "go test ./exporters/", "120"]),
    mk("dev-par-ms-1", "dev", "paraphrase",
       "Some of the dashboards feel wrong lately, numbers-wise. See what you "
       "can do to make the situation better.",
       "warn",
       [W("missing_stop_conditions", "See what you can do to make the situation better")]),

    # ---------------- DEV: legit look-alikes ----------------
    mk("dev-leg-options", "dev", "legit_lookalike",
       "Deliverable: a comparison document, not code. Write "
       "docs/retry-strategies.md comparing three retry strategies (fixed, "
       "exponential, exponential+jitter) for our HTTP client: latency impact, "
       "thundering-herd risk, implementation cost. End with a recommendation. "
       "Do not modify any source files.",
       "no_change", protected=["docs/retry-strategies.md"]),
    mk("dev-leg-verify", "dev", "legit_lookalike",
       "Fix the rounding bug in billing/tax.py (line 57: use ROUND_HALF_EVEN). "
       "This is billing-critical: CI policy requires two consecutive green "
       "runs, so run python3 -m pytest tests/test_tax.py twice and stop after "
       "the second green run.",
       "no_change", protected=["billing/tax.py", "python3 -m pytest tests/test_tax.py", "57"]),
    mk("dev-leg-explore", "dev", "legit_lookalike",
       "Inventory task, read-only: list every file that imports the deprecated "
       "helper `old_hash` (search with rg 'old_hash'). Output a markdown table "
       "of file → line numbers. Read only matching files; change nothing.",
       "no_change", protected=["old_hash"]),
    mk("dev-leg-question", "dev", "legit_lookalike",
       "Not a code change — just a question: what are two or three sensible "
       "ways to paginate a cursor-based API in Go? One short paragraph each is "
       "plenty.",
       "no_change"),

    # ---------------- DEV: mixed ----------------
    mk("dev-mix-ma", "dev", "mixed",
       "Fix the inventory double-decrement in store/stock.py: sold items are "
       "decremented in both reserve() and commit().\n"
       "Scope: the store package (store/)\n"
       "Acceptance criteria: python3 -m pytest tests/test_stock.py passes\n"
       "Stop when the tests pass.\n"
       "Also, develop several competing implementations first and compare "
       "their trade-offs in depth before picking one.",
       "warn",
       [W("multiple_approaches", "develop several competing implementations first and compare their trade-offs in depth before picking one")],
       ["store/stock.py", "python3 -m pytest tests/test_stock.py"]),
    mk("dev-mix-mc", "dev", "mixed",
       "Update parsers/iso8601.js to accept a trailing 'Z'.\n"
       "Scope: parsers/ only.\n"
       "Acceptance criteria: npx jest iso8601 passes.\n"
       "Stop when tests pass.\n"
       "Before finishing, re-verify everything over and over until there is "
       "no conceivable doubt left in your mind.",
       "warn",
       [W("max_certainty", "re-verify everything over and over until there is no conceivable doubt left in your mind")],
       ["parsers/iso8601.js", "npx jest iso8601"]),
    mk("dev-mix-ee", "dev", "mixed",
       "Fix the flag parsing in cmd/serve.go: --port is ignored when --config "
       "is also set.\n"
       "Scope: cmd/ only. Verify with: go test ./cmd/.\n"
       "Stop when the test passes.\n"
       "But first read through every source file in the repository so your "
       "change is informed by the entire codebase.",
       "warn",
       [W("exhaustive_exploration", "first read through every source file in the repository so your change is informed by the entire codebase")],
       ["cmd/serve.go", "go test ./cmd/"]),

    # ---------------- DEV: Hebrew ----------------
    mk("dev-he-ma", "dev", "hebrew",
       "תקן את הבאג בחישוב ההנחה בקובץ pricing/discount.py — ההנחה מופעלת פעמיים. "
       "בדיקות: python3 -m pytest tests/test_discount.py. "
       "לפני שאתה מיישם, פתח כמה גישות שונות לפתרון, השווה ביניהן לעומק ורק אז בחר את הטובה ביותר.",
       "warn",
       [W("multiple_approaches", "פתח כמה גישות שונות לפתרון, השווה ביניהן לעומק ורק אז בחר את הטובה ביותר")],
       ["pricing/discount.py", "python3 -m pytest tests/test_discount.py"]),
    mk("dev-he-dt", "dev", "hebrew",
       "תקן את ה-off-by-one בפונקציה paginate בקובץ api/pages.py. "
       "בדיקה: python3 -m pytest tests/test_pages.py. "
       "תחשוב על זה לעומק שעות אם צריך, תשקלל כל אפשרות קיימת ותוודא מחדש כל מסקנה שוב ושוב בכל שלב.",
       "warn",
       [W("deep_thinking", "תחשוב על זה לעומק שעות אם צריך, תשקלל כל אפשרות קיימת ותוודא מחדש כל מסקנה שוב ושוב בכל שלב")],
       ["api/pages.py", "python3 -m pytest tests/test_pages.py"],
       alt_ok=["max_certainty"]),
    mk("dev-he-clean", "dev", "hebrew",
       "תקן את המיון ב-reports/summary.py: השורות ממוינות לפי מחרוזת במקום לפי תאריך. "
       "קריטריון קבלה: python3 -m pytest tests/test_summary.py עובר. עצור כשהבדיקות עוברות.",
       "no_change",
       protected=["reports/summary.py", "python3 -m pytest tests/test_summary.py"]),
    mk("dev-he-options", "dev", "hebrew",
       "כתוב מסמך קצר (docs/cache-options.md) שמשווה בין Redis, Memcached ו-in-process cache "
       "עבור השירות שלנו: יתרונות, חסרונות והמלצה אחת. אל תשנה קוד.",
       "no_change", protected=["docs/cache-options.md"]),

    # ---------------- DEV: adversarial rewrites ----------------
    mk("dev-adv-ma", "dev", "adversarial_rewrite",
       "Fix the queue starvation bug in workers/dispatch.py (long jobs starve "
       "the short-job lane). Verify with: python3 -m pytest tests/test_dispatch.py. "
       "Develop several distinct approaches, compare their trade-offs "
       "explicitly, and only then implement the best one. Separately — and "
       "this is required — append a short section to docs/DECISIONS.md naming "
       "the approach you chose and one alternative you rejected.",
       "warn",
       [W("multiple_approaches", "Develop several distinct approaches, compare their trade-offs explicitly, and only then implement the best one")],
       ["workers/dispatch.py", "python3 -m pytest tests/test_dispatch.py", "docs/DECISIONS.md"],
       notes="rewrite must keep the DECISIONS.md deliverable"),
    mk("dev-adv-mc", "dev", "adversarial_rewrite",
       "Fix the fixture leak in tests/conftest.py (temp dirs are not cleaned "
       "up). Our suite is order-dependent (known flake, tracked in FLAKY.md), "
       "so you must run python3 -m pytest -q twice, back to back — that "
       "double run is a hard requirement. Also: be absolutely certain about "
       "every conclusion and keep re-verifying until nothing can possibly be "
       "wrong.",
       "warn",
       [W("max_certainty", "be absolutely certain about every conclusion and keep re-verifying until nothing can possibly be wrong")],
       ["tests/conftest.py", "python3 -m pytest -q", "FLAKY.md"],
       notes="rewrite must keep the required double test run"),
    mk("dev-adv-ee", "dev", "adversarial_rewrite",
       "Change models/user.py so email comparison is case-insensitive. "
       "IMPORTANT: you must read migrations/0009_email_index.py before "
       "editing — the index definition there is coupled to the comparison. "
       "Verify with: python3 -m pytest tests/test_user.py. Additionally, "
       "before editing anything, inspect the entire repository and read every "
       "source file so you understand the complete system.",
       "warn",
       [W("exhaustive_exploration", "before editing anything, inspect the entire repository and read every source file so you understand the complete system")],
       ["models/user.py", "migrations/0009_email_index.py", "python3 -m pytest tests/test_user.py"],
       notes="rewrite must keep the required migration read"),

    # ================= HOLDOUT: paraphrases =================
    mk("hold-par-ma-1", "holdout", "paraphrase",
       "Fix the race condition in worker/pool.go: two goroutines can claim "
       "the same job when the queue has exactly one item. Verify with: go "
       "test ./worker/ -race. Before you commit to anything, sketch out a few "
       "different ways this could be solved and weigh them against each "
       "other, then go with whichever wins out.",
       "warn",
       [W("multiple_approaches", "sketch out a few different ways this could be solved and weigh them against each other, then go with whichever wins out")],
       ["worker/pool.go", "go test ./worker/ -race"]),
    mk("hold-par-ma-2", "holdout", "paraphrase",
       "The pagination in api/list_endpoints.py drops the final page when "
       "total%page_size == 0. Fix it; tests: python3 -m pytest "
       "tests/test_list.py. I'd like you to brainstorm at least three "
       "candidate designs internally and pick the strongest before writing "
       "any code.",
       "warn",
       [W("multiple_approaches", "brainstorm at least three candidate designs internally and pick the strongest before writing any code")],
       ["api/list_endpoints.py", "python3 -m pytest tests/test_list.py", "3"]),
    mk("hold-par-mc-1", "holdout", "paraphrase",
       "Update the currency rounding in billing/invoice.py so totals use "
       "banker's rounding (ROUND_HALF_EVEN). Verify: python3 -m pytest "
       "tests/test_invoice.py. Keep going over your change until there is "
       "zero chance anything is off — I don't want even a remote possibility "
       "of a mistake.",
       "warn",
       [W("max_certainty", "Keep going over your change until there is zero chance anything is off")],
       ["billing/invoice.py", "python3 -m pytest tests/test_invoice.py"]),
    mk("hold-par-mc-2", "holdout", "paraphrase",
       "Patch the session-timeout logic in auth/session.js so idle sessions "
       "expire after 30 minutes, not 30 seconds. Test: npx jest session. "
       "Please re-run your checks again and again until you'd stake your "
       "reputation on it being flawless.",
       "warn",
       [W("max_certainty", "re-run your checks again and again until you'd stake your reputation on it being flawless")],
       ["auth/session.js", "npx jest session", "30"]),
    mk("hold-par-dt-1", "holdout", "paraphrase",
       "The CSV importer in ingest/reader.py mangles quoted fields that "
       "contain newlines. Fix it; verify with python3 -m pytest "
       "tests/test_reader.py. Take your time and ponder every angle "
       "exhaustively before touching the file, re-examining each conclusion "
       "you reach.",
       "warn",
       [W("deep_thinking", "Take your time and ponder every angle exhaustively before touching the file, re-examining each conclusion you reach")],
       ["ingest/reader.py", "python3 -m pytest tests/test_reader.py"]),
    mk("hold-par-dt-2", "holdout", "paraphrase",
       "Fix the off-by-one in the pagination cursor in store/cursor.go "
       "(last row of each page repeats). Verify: go test ./store/. Ruminate "
       "carefully on all the implications, questioning every assumption at "
       "each step, before and during the fix.",
       "warn",
       [W("deep_thinking", "Ruminate carefully on all the implications, questioning every assumption at each step, before and during the fix")],
       ["store/cursor.go", "go test ./store/"]),
    mk("hold-par-ee-1", "holdout", "paraphrase",
       "There's a memory leak in the websocket handler (ws/handler.js): "
       "listeners are never removed on disconnect. Fix it; test with npx "
       "jest ws. Get the full picture first — walk through the whole codebase "
       "file by file so nothing is unfamiliar before you start.",
       "warn",
       [W("exhaustive_exploration", "walk through the whole codebase file by file so nothing is unfamiliar before you start")],
       ["ws/handler.js", "npx jest ws"]),
    mk("hold-par-ee-2", "holdout", "paraphrase",
       "Bug: the config loader ignores YAML anchors (config/loader.py). Fix "
       "it; verify with python3 -m pytest tests/test_loader.py. Familiarize "
       "yourself with every module in the project and how they all "
       "interconnect prior to making the edit.",
       "warn",
       [W("exhaustive_exploration", "Familiarize yourself with every module in the project and how they all interconnect prior to making the edit")],
       ["config/loader.py", "python3 -m pytest tests/test_loader.py"]),
    mk("hold-par-ac-1", "holdout", "paraphrase",
       "Fix the nil-pointer crash in parser/tokens.go around line 88 (empty "
       "token stream). Verify: go test ./parser/. And hey — if you spot "
       "anything nearby that looks crufty, give it a polish while you're "
       "passing through.",
       "warn",
       [W("adjacent_cleanup", "if you spot anything nearby that looks crufty, give it a polish while you're passing through")],
       ["parser/tokens.go", "go test ./parser/", "88"]),
    mk("hold-par-ac-2", "holdout", "paraphrase",
       "The date formatter in utils/dates.js returns UTC instead of local "
       "time. Fix it; test: npx jest dates. Feel free to also spruce up "
       "whatever else in that area could use some love.",
       "warn",
       [W("adjacent_cleanup", "Feel free to also spruce up whatever else in that area could use some love")],
       ["utils/dates.js", "npx jest dates"]),
    mk("hold-par-ms-1", "holdout", "paraphrase",
       "Something's off somewhere in the reporting pipeline — the numbers "
       "look wrong some of the time. Make it better.",
       "warn",
       [W("missing_stop_conditions", "Make it better")]),
    mk("hold-par-ms-2", "holdout", "paraphrase",
       "Users keep complaining about the export feature being unreliable. "
       "Improve things until it feels solid.",
       "warn",
       [W("missing_stop_conditions", "Improve things until it feels solid")]),

    # ================= HOLDOUT: legit look-alikes =================
    mk("hold-leg-options", "holdout", "legit_lookalike",
       "Write a design memo at docs/cache-eviction-options.md comparing three "
       "eviction strategies for our in-memory cache: plain LRU, LRU+TTL, and "
       "2Q. For each cover memory overhead, hit-rate implications, and "
       "implementation cost, then end with a recommendation. The comparison "
       "IS the deliverable — do not change any code.",
       "no_change", protected=["docs/cache-eviction-options.md"]),
    mk("hold-leg-verify", "holdout", "legit_lookalike",
       "Fix the double-charge bug in payments/capture.py: retries after a "
       "timeout re-capture the same intent. Acceptance: tests/test_capture.py "
       "passes, and per CI policy you must run the full suite twice "
       "(python3 -m pytest -q, two consecutive green runs). Stop after the "
       "second green run.",
       "no_change",
       protected=["payments/capture.py", "tests/test_capture.py", "python3 -m pytest -q"]),
    mk("hold-leg-explore", "holdout", "legit_lookalike",
       "Read-only audit: find every import of the deprecated package "
       "`requests_toolbelt` (rg 'requests_toolbelt') and produce a table of "
       "file → usage. Read only the files that match; output the table and "
       "change nothing.",
       "no_change", protected=["requests_toolbelt"]),
    mk("hold-leg-cleanup", "holdout", "legit_lookalike",
       "Refactor task: rename the misleading variable `data2` to "
       "`normalized_rows` everywhere in etl/transform.py and update the "
       "docstring accordingly. The rename is the entire task — do not fix or "
       "improve anything else.",
       "no_change", protected=["etl/transform.py", "data2", "normalized_rows"]),
    mk("hold-leg-assurance", "holdout", "legit_lookalike",
       "Migrate the DB URL parsing in db/conn.go to use url.Parse instead of "
       "manual string splitting. Verify with: go test ./db/ -run "
       "TestConnString. I need to be confident this is right, so make sure "
       "that specific test passes before you stop.",
       "no_change", protected=["db/conn.go", "go test ./db/ -run TestConnString"]),
    mk("hold-leg-question", "holdout", "legit_lookalike",
       "Question only, no code change: what are two or three reasonable ways "
       "to throttle outbound webhooks in a Django app? A short paragraph on "
       "each is plenty.",
       "no_change"),

    # ================= HOLDOUT: mixed =================
    mk("hold-mix-ma", "holdout", "mixed",
       "Fix the checkout total bug in cart/totals.py: the flat coupon must "
       "apply before tax, not after.\n"
       "Scope: cart/ only.\n"
       "Acceptance criteria: total(100, 10) == 99.0; python3 -m pytest "
       "tests/test_totals.py passes.\n"
       "Stop when the tests pass.\n"
       "One more thing: generate multiple alternative implementations and "
       "evaluate them against each other before you settle on one.",
       "warn",
       [W("multiple_approaches", "generate multiple alternative implementations and evaluate them against each other before you settle on one")],
       ["cart/totals.py", "python3 -m pytest tests/test_totals.py", "100", "10", "99.0"]),
    mk("hold-mix-mc", "holdout", "mixed",
       "Fix the header casing bug in http/headers.go (lookups must be "
       "case-insensitive).\n"
       "Scope: http/ only. Verify with: go test ./http/.\n"
       "Stop when the test passes.\n"
       "Do not consider yourself done until you are certain beyond any "
       "possible doubt that absolutely nothing can be wrong — re-verify as "
       "many times as it takes.",
       "warn",
       [W("max_certainty", "Do not consider yourself done until you are certain beyond any possible doubt that absolutely nothing can be wrong — re-verify as many times as it takes")],
       ["http/headers.go", "go test ./http/"]),
    mk("hold-mix-dt", "holdout", "mixed",
       "Fix the locale fallback in i18n/lookup.js: missing keys should fall "
       "back to 'en', not throw.\n"
       "Scope: i18n/ only. Test: npx jest i18n.\n"
       "Stop when tests pass.\n"
       "Think about this as hard and as long as you possibly can, "
       "re-deriving every conclusion several times before acting.",
       "warn",
       [W("deep_thinking", "Think about this as hard and as long as you possibly can, re-deriving every conclusion several times before acting")],
       ["i18n/lookup.js", "npx jest i18n"],
       alt_ok=["max_certainty"]),
    mk("hold-mix-ee", "holdout", "mixed",
       "Fix the S3 key encoding bug in storage/keys.py ('+' must be encoded "
       "as %2B).\n"
       "Scope: storage/ only. Verify: python3 -m pytest tests/test_keys.py.\n"
       "Stop when the tests pass.\n"
       "Before that, though, please survey the complete repository and read "
       "every file so you understand how all parts connect.",
       "warn",
       [W("exhaustive_exploration", "survey the complete repository and read every file so you understand how all parts connect")],
       ["storage/keys.py", "python3 -m pytest tests/test_keys.py"]),
    mk("hold-mix-ac", "holdout", "mixed",
       "Fix the CSV escaping bug in export/csv.go: embedded quotes must be "
       "doubled per RFC 4180.\n"
       "Scope: export/ only. Verify with: go test ./export/.\n"
       "Stop when the test passes.\n"
       "While you're there, clean up anything adjacent that bothers you — "
       "naming, dead code, whatever you spot.",
       "warn",
       [W("adjacent_cleanup", "While you're there, clean up anything adjacent that bothers you — naming, dead code, whatever you spot")],
       ["export/csv.go", "go test ./export/", "4180"]),
    mk("hold-mix-double", "holdout", "mixed",
       "Fix the retry storm in sync/push.py: failed pushes retry with no "
       "backoff.\n"
       "Scope: sync/ only. Acceptance: python3 -m pytest tests/test_push.py "
       "passes. Stop when tests pass.\n"
       "Work out several different designs and compare them thoroughly "
       "before choosing, and afterwards keep re-verifying the change until "
       "you are utterly certain nothing can be wrong.",
       "warn",
       [W("multiple_approaches", "Work out several different designs and compare them thoroughly before choosing"),
        W("max_certainty", "keep re-verifying the change until you are utterly certain nothing can be wrong")],
       ["sync/push.py", "python3 -m pytest tests/test_push.py"]),

    # ================= HOLDOUT: Hebrew =================
    mk("hold-he-ma", "holdout", "hebrew",
       "תקן את הבאג בחישוב המע\"מ בקובץ billing/vat.py — המע\"מ מחושב לפני ההנחה במקום אחריה. "
       "בדיקות: python3 -m pytest tests/test_vat.py. "
       "לפני המימוש, גבש כמה גישות שונות, השווה את היתרונות והחסרונות של כל אחת, ורק לאחר מכן בחר את המנצחת.",
       "warn",
       [W("multiple_approaches", "גבש כמה גישות שונות, השווה את היתרונות והחסרונות של כל אחת, ורק לאחר מכן בחר את המנצחת")],
       ["billing/vat.py", "python3 -m pytest tests/test_vat.py"]),
    mk("hold-he-mc", "holdout", "hebrew",
       "עדכן את לוגיקת ה-retry בקובץ client/http.js לשלושה ניסיונות עם backoff מעריכי. "
       "בדיקה: npx jest http. "
       "תוודא שוב ושוב שאין שום סיכוי לטעות, ואל תסיים עד שאתה בטוח במאה אחוז שהכל מושלם.",
       "warn",
       [W("max_certainty", "תוודא שוב ושוב שאין שום סיכוי לטעות, ואל תסיים עד שאתה בטוח במאה אחוז שהכל מושלם")],
       ["client/http.js", "npx jest http"]),
    mk("hold-he-ac", "holdout", "hebrew",
       "תקן את הקריסה בפונקציה parse_row בקובץ ingest/rows.py (שורה 42, קלט ריק). "
       "בדיקות: python3 -m pytest tests/test_rows.py. "
       "ואם אתה כבר שם, תרגיש חופשי לסדר ולשפר כל דבר בסביבה שנראה לך מוזנח.",
       "warn",
       [W("adjacent_cleanup", "ואם אתה כבר שם, תרגיש חופשי לסדר ולשפר כל דבר בסביבה שנראה לך מוזנח")],
       ["ingest/rows.py", "python3 -m pytest tests/test_rows.py", "42"]),
    mk("hold-he-clean", "holdout", "hebrew",
       "תקן את הבאג במיון התאריכים בקובץ reports/sort.py — התאריכים ממוינים כמחרוזות במקום כתאריכים. "
       "קריטריון קבלה: python3 -m pytest tests/test_sort.py עובר. עצור כשהבדיקות עוברות.",
       "no_change",
       protected=["reports/sort.py", "python3 -m pytest tests/test_sort.py"]),
    mk("hold-he-options", "holdout", "hebrew",
       "כתוב מסמך קצר (docs/queue-options.md) שמשווה בין RabbitMQ, Kafka ו-SQS עבור תור ההודעות שלנו — "
       "יתרונות, חסרונות והמלצה. ההשוואה היא התוצר המבוקש. אל תשנה קוד.",
       "no_change", protected=["docs/queue-options.md"]),
    mk("hold-he-autonomy", "holdout", "hebrew",
       "העבר את הפונקציה slugify מ-utils/text.py ל-utils/strings.py ועדכן את היבוא בכל הקבצים. "
       "אל תשאל אותי שאלות — תשלים את הפרטים לבד. בדיקות: python3 -m pytest -q.",
       "no_change",
       protected=["utils/text.py", "utils/strings.py", "python3 -m pytest -q", "slugify"],
       notes="autonomy language is measured neutral (H13); must not warn"),

    # ================= HOLDOUT: preservation-heavy =================
    mk("hold-pres-1", "holdout", "preservation",
       "Our gateway misroutes requests when the path has a trailing slash. "
       "Fix route_key() in gateway/router.rs:\n\n"
       "```rust\nfn route_key(path: &str) -> String {\n"
       "    path.split('/').take(3).collect::<Vec<_>>().join(\"/\")\n}\n```\n\n"
       "Requirement: p95 latency must stay < 250ms (bench: cargo bench "
       "--bench routing). Tests: cargo test --package gateway. Think very "
       "deeply about every possibility and verify your reasoning repeatedly "
       "at every step before acting.",
       "warn",
       [W("deep_thinking", "Think very deeply about every possibility and verify your reasoning repeatedly at every step before acting")],
       ["gateway/router.rs", "route_key", "cargo test --package gateway",
        "cargo bench --bench routing", "250", "p95"]),
    mk("hold-pres-2", "holdout", "preservation",
       "The nightly export job writes malformed CSV when amounts are "
       "negative. Per the spec: \"Output CSV must have header id,ts,"
       "amount_eur and amounts formatted with exactly 2 decimals\". Fix "
       "exporter/nightly.py; verify with python3 -m pytest "
       "tests/test_nightly.py -k csv. Before editing anything, read every "
       "source file in the repository so you understand the complete system.",
       "warn",
       [W("exhaustive_exploration", "read every source file in the repository so you understand the complete system")],
       ["exporter/nightly.py", "python3 -m pytest tests/test_nightly.py -k csv",
        "id,ts,amount_eur", "2"]),
    mk("hold-pres-3", "holdout", "preservation",
       "Fix the broken f-string in cli/report.py line 31:\n\n"
       "```python\nprint(f\"processed {n_rows} rows in {elapsed:.2f}s\")\n```\n\n"
       "It currently crashes when elapsed is None — default it to 0.0. Keep "
       "my TODO comments in that file exactly as they are. Verify: python3 "
       "-m pytest tests/test_report.py. Stop when the test passes.",
       "no_change",
       protected=["cli/report.py", "python3 -m pytest tests/test_report.py",
                  "31", "0.0", "TODO"]),

    # ================= HOLDOUT: adversarial rewrites =================
    mk("hold-adv-ma", "holdout", "adversarial_rewrite",
       "Fix the queue starvation in workers/dispatch.go: long-running jobs "
       "starve the short-job lane. Verify with: go test ./workers/. Develop "
       "several distinct approaches to this fix, compare their trade-offs "
       "explicitly, and only then select and implement the best one. "
       "Separately — and this is a hard requirement — add a short entry to "
       "docs/ADR/0014-dispatch.md naming the approach you chose and one "
       "alternative you rejected.",
       "warn",
       [W("multiple_approaches", "Develop several distinct approaches to this fix, compare their trade-offs explicitly, and only then select and implement the best one")],
       ["workers/dispatch.go", "go test ./workers/", "docs/ADR/0014-dispatch.md"],
       notes="rewrite must keep the ADR deliverable about the rejected alternative"),
    mk("hold-adv-mc", "holdout", "adversarial_rewrite",
       "Fix the fixture teardown leak in tests/conftest.py (temp dirs "
       "survive failures). Our suite has a known order-dependence flake "
       "(see FLAKY.md), so running python3 -m pytest -q twice back-to-back "
       "is a hard CI requirement — keep that. Also, you must be absolutely "
       "confident in the result: re-verify the change repeatedly until you "
       "are certain beyond any doubt that nothing can be wrong.",
       "warn",
       [W("max_certainty", "you must be absolutely confident in the result: re-verify the change repeatedly until you are certain beyond any doubt that nothing can be wrong")],
       ["tests/conftest.py", "python3 -m pytest -q", "FLAKY.md"],
       notes="rewrite must keep the required double run"),
    mk("hold-adv-ee", "holdout", "adversarial_rewrite",
       "Make email comparison case-insensitive in models/user.py. You MUST "
       "read migrations/0007_email_index.py before editing — the functional "
       "index there is coupled to the comparison logic. Verify: python3 -m "
       "pytest tests/test_user.py. Also, before editing anything, inspect "
       "the entire repository and read every source file so your change is "
       "informed by the whole codebase.",
       "warn",
       [W("exhaustive_exploration", "before editing anything, inspect the entire repository and read every source file so your change is informed by the whole codebase")],
       ["models/user.py", "migrations/0007_email_index.py",
        "python3 -m pytest tests/test_user.py"],
       notes="rewrite must keep the required targeted read of the migration"),
    mk("hold-adv-ac", "holdout", "adversarial_rewrite",
       "Fix the toggle persistence bug in settings/flags.py: saved flags "
       "revert on reload. In the same change — this is in scope on purpose — "
       "delete the now-unused feature flag ENABLE_V1_EXPORT everywhere it "
       "appears. Verify: python3 -m pytest tests/test_flags.py. While you "
       "are in there, feel free to clean up anything else adjacent that "
       "could be improved: naming, dead code, general tidying.",
       "warn",
       [W("adjacent_cleanup", "feel free to clean up anything else adjacent that could be improved: naming, dead code, general tidying")],
       ["settings/flags.py", "ENABLE_V1_EXPORT", "python3 -m pytest tests/test_flags.py"],
       notes="rewrite must keep the explicit ENABLE_V1_EXPORT removal"),
    mk("hold-adv-dt", "holdout", "adversarial_rewrite",
       "Tighten the type hints in api/serializers.py (the Any leaks from "
       "parse_payload). Hard constraints: do not modify any public API "
       "signatures, and verify with mypy --strict api/ plus python3 -m "
       "pytest tests/test_serializers.py. Think very deeply about this, "
       "reason through every possibility before acting, and verify your "
       "reasoning repeatedly at every step.",
       "warn",
       [W("deep_thinking", "Think very deeply about this, reason through every possibility before acting, and verify your reasoning repeatedly at every step")],
       ["api/serializers.py", "mypy --strict api/",
        "python3 -m pytest tests/test_serializers.py", "parse_payload"],
       notes="rewrite must keep both verification commands and the signature constraint",
       alt_ok=["max_certainty"]),
]


def main():
    tasks = load_tasks()
    examples = build_repo_examples(tasks) + AUTHORED
    ids = [e["id"] for e in examples]
    assert len(ids) == len(set(ids)), "duplicate ids"
    # sanity: gold spans must be exact substrings
    for e in examples:
        for r in e["gold"]["risks"]:
            for s in r["gold_spans"]:
                assert s in e["prompt"], (e["id"], s[:60])
        for p in e["gold"]["protected"]:
            assert p in e["prompt"], (e["id"], p)
    dev = [e for e in examples if e["split"] == "dev"]
    hold = [e for e in examples if e["split"] == "holdout"]
    os.makedirs(HERE, exist_ok=True)
    for name, rows in (("dev.jsonl", dev), ("holdout.jsonl", hold)):
        path = os.path.join(HERE, name)
        with open(path, "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()
        print(f"{name}: {len(rows)} examples sha256={h}")
    from collections import Counter
    for split, rows in (("dev", dev), ("holdout", hold)):
        c = Counter(e["category"] for e in rows)
        g = Counter(e["gold"]["recommendation"] for e in rows)
        print(split, dict(c), dict(g))


if __name__ == "__main__":
    sys.exit(main())
