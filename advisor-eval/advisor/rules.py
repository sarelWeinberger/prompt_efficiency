"""Deterministic rules baseline + hybrid triage.

Patterns were derived ONLY from the frozen prompt-family templates
(benchmark/prompt_families.yaml) and the dev split; frozen before the
holdout was opened (see PROTOCOL.md).

Guard rationale (precision-first): each family has both trigger patterns
and, where needed, "legit" guards that suppress a match when the surrounding
prompt shows the look-alike is a bounded, user-chosen requirement.
"""
import re

FLAGS = re.IGNORECASE | re.DOTALL

# --- triggers -------------------------------------------------------------
RULES = {
    "multiple_approaches": [
        r"(develop|come up with|sketch out|brainstorm|generate|work out|gbš)[^.?!\n]{0,80}\b(several|multiple|a few|handful of|competing|distinct|different|alternative|candidate)\b[^.?!]{0,80}\b(approach|solution|way|design|implementation|option)\w*[^.?!]{0,120}\b(compare|weigh|evaluate|trade-?offs?|against each other|pick|choose|select|settle)",
        r"\b(compare|weigh|evaluate)[^.?!]{0,80}\b(approaches|designs|solutions|alternatives|options)\b[^.?!]{0,80}\b(before|then|only then)\b[^.?!]{0,60}\b(select|choos|pick|implement|writ|settl|commit)",
        # Hebrew: "develop several approaches, compare, then choose"
        r"(פתח|גבש)[^.?!]{0,40}(כמה|מספר)\s+גישות[^.?!]{0,120}(השווה|השוואה)",
    ],
    "max_certainty": [
        r"\b(absolutely|utterly|100%|completely|beyond any (possible )?doubt)\b[^.?!]{0,60}\b(certain|confident|sure)\b",
        r"\b(certain|confident|sure)\b[^.?!]{0,50}\bbeyond any (possible )?doubt",
        r"\bre-?(verify|check|run)\w*[^.?!]{0,90}\b(repeatedly|again and again|over and over|as many times as it takes|until)\b[^.?!]{0,90}\b(nothing|no\w*|zero|certain|doubt|wrong|flawless|perfect|mistake)",
        r"\b(keep|continue)\b[^.?!]{0,60}\b(checking|verifying|going over|re-?verify\w*)\b[^.?!]{0,90}\b(until|zero chance|no (possible )?doubt|nothing)\b",
        r"\bzero chance\b|\bnot even a remote possibility\b|\bstake your reputation\b",
        r"(תוודא|בדוק)[^.?!]{0,30}(שוב ושוב)|בטוח במאה אחוז|ודאות מוחלטת",
    ],
    "deep_thinking": [
        r"\b(think|ponder|mull|ruminate|reflect|deliberate)\w*[^.?!]{0,60}\b(very deeply|deeply|at great length|as hard|extremely hard|exhaustively|every angle|every possibilit)",
        r"\breason\w*\s+through\s+every\s+possibilit",
        r"\b(re-?examin|re-?deriv|question)\w*[^.?!]{0,50}\b(each|every)\s+(conclusion|assumption)",
        r"\bverify your reasoning repeatedly\b",
        r"תחשוב[^.?!]{0,30}לעומק|תהרהר[^.?!]{0,40}לעומק",
    ],
    "exhaustive_exploration": [
        r"\b(read|inspect|open|walk through|survey|review)\b[^.?!]{0,60}\b(every|each|all( of)? the|the entire|the whole|the complete)\b[^.?!]{0,40}\b(source files?|files?|modules?|repositor\w+|codebase)",
        r"\b(entire|whole|complete)\s+(repository|codebase|system)\b[^.?!]{0,100}\b(before|prior to|so (that )?you|first)",
        r"\bfile by file\b[^.?!]{0,80}\bbefore\b",
        r"\b(understand|know|familiar\w*)[^.?!]{0,60}\b(whole|entire|complete|every)\b[^.?!]{0,40}\b(system|codebase|module|project|repositor)\w*[^.?!]{0,60}\b(before|prior|inside out)",
        r"(קרא|עבור על|סרוק)[^.?!]{0,30}(כל|את כל)[^.?!]{0,30}(הקבצים|הריפו|הקוד)",
    ],
    "adjacent_cleanup": [
        r"\bwhile you('| a)re (in there|there|at it|passing through|in that)[^.?!]{0,100}\b(clean|tidy|polish|improve|spruce|refactor|fix up)",
        r"\b(clean up|tidy|polish|spruce up|improve)\b[^.?!]{0,60}\b(anything|whatever|whatever else|everything)\b[^.?!]{0,60}\b(adjacent|nearby|around|in that area|you (see|spot)|looks (shabby|crufty)|could (use|be improved)|bothers you)",
        r"\bif you spot anything\b[^.?!]{0,80}\b(polish|clean|tidy|improve|fix)",
        r"\b(feel free|go ahead)\b[^.?!]{0,60}\b(clean|tidy|refactor|improve|spruce)\b[^.?!]{0,80}\b(adjacent|nearby|around|else|other|area|whatever)",
        r"אם אתה כבר שם[^.?!]{0,80}(לסדר|לשפר|לנקות)|תרגיש חופשי[^.?!]{0,60}(לסדר|לשפר)[^.?!]{0,60}(בסביבה|מסביב|כל דבר)",
    ],
    # intentionally recall-limited: only the clearest "vague ask + no stop" forms
    "missing_stop_conditions": [
        r"\b(improve|make)\b[^.?!]{0,40}\b(the situation|things|it)\b[^.?!]{0,20}\b(better)?\s*(\.|$|until it feels)",
        r"\bsomething\b[^.?!]{0,60}\b(wrong|off|producing wrong results)\b",
    ],
}

# --- guards: suppress a family match when the look-alike is legitimate -----
GUARDS = {
    "multiple_approaches": [
        r"\b(memo|document|doc|report|table|answer|question|write)\b[^.?!]{0,120}\b(compar|options|strategies|ways)",
        r"\bdocs?/[\w./-]+\.md\b",
        r"\bnot a code change\b|\bno code change\b|\bdo not (modify|change) any (source|code)\b|אל תשנה קוד",
        r"\bquestion\b[^.?!]{0,30}(only|not a code|,)",
    ],
    "max_certainty": [
        r"\b(twice|two consecutive|second green run|run [^.?!]{0,40} twice)\b",
        r"\bmake sure (that )?(specific )?test\w* pass\w*\b",
    ],
    "exhaustive_exploration": [
        r"\bread only\b|\bread-only\b|\bchange nothing\b",
        r"\bmust read [\w./-]+\.(py|go|js|ts|md)\b",
    ],
    "adjacent_cleanup": [
        r"\brename\b[^.?!]{0,80}\bis the (entire )?task\b",
        r"\bthe rename IS the task\b",
    ],
    "missing_stop_conditions": [
        r"\b(pytest|go test|npx jest|cargo test|acceptance|verify with|stop when)\b",
        r"עצור|קריטריון",
    ],
}

# --- soft indicators: hybrid triage sends these to the model ---------------
SOFT = re.compile(
    r"approach|option|alternativ|compare|weigh|certain|confident|verify|"
    r"double-check|thorough|deep|ponder|reflect|ruminate|explore|entire|"
    r"whole|every file|codebase|clean|tidy|refactor|polish|improve|"
    r"situation|better|solid|"
    r"גישות|בטוח|לעומק|לסדר|לשפר|תוודא|כל הקבצים",
    FLAGS,
)

_COMPILED = {
    fam: [re.compile(p, FLAGS) for p in pats] for fam, pats in RULES.items()
}
_GUARDS = {
    fam: [re.compile(p, FLAGS) for p in pats] for fam, pats in GUARDS.items()
}

SUGGESTIONS = {
    "multiple_approaches": "Ask for one direct fix; if you want options, request them as an explicit deliverable instead.",
    "max_certainty": "Name the specific test command and stop condition instead of open-ended re-verification.",
    "deep_thinking": "Drop the thinking incantation; state the acceptance criteria instead.",
    "exhaustive_exploration": "Point at the specific files involved instead of a whole-repo read.",
    "adjacent_cleanup": "Limit the change to the named fix; list any extra cleanup items explicitly if wanted.",
    "missing_stop_conditions": "State what exactly is wrong, the scope, and a concrete acceptance test / stop condition.",
}
REASONS = {
    "multiple_approaches": "Internal design tournaments multiply reasoning tokens 2-7x with no correctness gain.",
    "max_certainty": "Unbounded certainty-seeking buys extra verification loops (up to 4x under agentic harnesses).",
    "deep_thinking": "Deep-thinking incantations cost 1.6-2.2x reasoning with nothing in return.",
    "exhaustive_exploration": "Whole-repo reads before a small change amplify cost, especially under agentic harnesses.",
    "adjacent_cleanup": "Open-ended cleanup invitations cause 3-4x reasoning and out-of-scope edits.",
    "missing_stop_conditions": "Vague scope with no stop condition is the one defect that reliably hurts correctness (+44% reasoning).",
}


def rules_detect(prompt):
    """Return list of {type, evidence} rule hits with guards applied."""
    hits = []
    for fam, pats in _COMPILED.items():
        guarded = any(g.search(prompt) for g in _GUARDS.get(fam, []))
        if guarded:
            continue
        for p in pats:
            m = p.search(prompt)
            if m:
                hits.append({"type": fam, "evidence": m.group(0)})
                break
    return hits


def rules_predict(prompt):
    """Full prediction in the shared output schema (no rewrite: rules never rewrite)."""
    hits = rules_detect(prompt)
    if hits:
        risks = [{
            "type": h["type"],
            "evidence": h["evidence"],
            "reason": REASONS[h["type"]],
            "suggestion": SUGGESTIONS[h["type"]],
        } for h in hits]
        return {"recommendation": "warn", "risks": risks,
                "revised_prompt": None, "confidence": 0.9}
    return {"recommendation": "no_change", "risks": [],
            "revised_prompt": None, "confidence": 0.8}


def is_ambiguous(prompt):
    """Hybrid triage: no exact rule hit, but soft indicators present."""
    return SOFT.search(prompt) is not None
