#!/usr/bin/env python3
"""Materialize the 9 Python benchmark tasks: fixtures, task metadata, hidden evaluators.

Run: python3 benchmark/scaffold_py.py   (idempotent; overwrites generated files)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIX = ROOT / "fixtures"
TASKS = ROOT / "tasks"
EVAL = ROOT / "evaluators"

T = {}

# ---------------------------------------------------------------- py-low-01
T["py-low-01"] = dict(
    meta=dict(
        language="python", complexity="low", split="dev", pilot=True,
        objective="Fix the discount bug in shop/discount.py: apply_discount(price, pct) "
                  "must return the price AFTER applying a pct-percent discount, not the "
                  "discount amount itself.",
        objective_vague="price and discount calculations",
        misleading_hint="test fixtures in tests/",
        scope="shop/discount.py only",
        allowed_paths=["shop/discount.py"],
        criteria="apply_discount(100, 20) == 80.0 and every test under tests/ passes",
        test_cmd="python3 -m unittest discover -s tests -t . -v",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "shop/__init__.py": "",
        "shop/discount.py": '''\
def apply_discount(price, pct):
    """Return the price after applying a pct-percent discount.

    pct must be between 0 and 100 inclusive.
    """
    if pct < 0 or pct > 100:
        raise ValueError("pct out of range")
    return price * pct / 100
''',
        "tests/__init__.py": "",
        "tests/test_discount.py": '''\
import unittest

from shop.discount import apply_discount


class TestDiscount(unittest.TestCase):
    def test_twenty_percent_off(self):
        self.assertEqual(apply_discount(100, 20), 80.0)

    def test_no_discount(self):
        self.assertEqual(apply_discount(50, 0), 50.0)


if __name__ == "__main__":
    unittest.main()
''',
    },
    hidden={
        "test_hidden.py": '''\
import unittest

from shop.discount import apply_discount


class TestDiscountHidden(unittest.TestCase):
    def test_full_discount(self):
        self.assertEqual(apply_discount(100, 100), 0.0)

    def test_fractional(self):
        self.assertEqual(apply_discount(80, 25), 60.0)

    def test_range_low(self):
        with self.assertRaises(ValueError):
            apply_discount(10, -1)

    def test_range_high(self):
        with self.assertRaises(ValueError):
            apply_discount(10, 101)


if __name__ == "__main__":
    unittest.main()
''',
    },
)

# ---------------------------------------------------------------- py-low-02
T["py-low-02"] = dict(
    meta=dict(
        language="python", complexity="low", split="dev", pilot=False,
        objective="Fix the username validation rule in users/validate.py: usernames of "
                  "length 3 through 20 (inclusive) consisting of lowercase letters, "
                  "digits and underscores must be accepted; currently 3-character names "
                  "are wrongly rejected.",
        objective_vague="user input validation",
        misleading_hint="regular expression pattern",
        scope="users/validate.py only",
        allowed_paths=["users/validate.py"],
        criteria='is_valid_username("abc") is True; boundary lengths 3 and 20 accepted; '
                 "2 and 21 rejected; every test under tests/ passes",
        test_cmd="python3 -m unittest discover -s tests -t . -v",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "users/__init__.py": "",
        "users/validate.py": '''\
import re

USERNAME_RE = re.compile(r"^[a-z0-9_]+$")


def is_valid_username(name):
    """A valid username is 3-20 characters of [a-z0-9_], inclusive bounds."""
    if not isinstance(name, str):
        return False
    if len(name) <= 3 or len(name) > 20:
        return False
    return bool(USERNAME_RE.match(name))
''',
        "tests/__init__.py": "",
        "tests/test_validate.py": '''\
import unittest

from users.validate import is_valid_username


class TestValidate(unittest.TestCase):
    def test_three_chars_valid(self):
        self.assertTrue(is_valid_username("abc"))

    def test_two_chars_invalid(self):
        self.assertFalse(is_valid_username("ab"))

    def test_twenty_chars_valid(self):
        self.assertTrue(is_valid_username("a" * 20))


if __name__ == "__main__":
    unittest.main()
''',
    },
    hidden={
        "test_hidden.py": '''\
import unittest

from users.validate import is_valid_username


class TestValidateHidden(unittest.TestCase):
    def test_twenty_one_invalid(self):
        self.assertFalse(is_valid_username("a" * 21))

    def test_uppercase_invalid(self):
        self.assertFalse(is_valid_username("Abc"))

    def test_underscore_digit_valid(self):
        self.assertTrue(is_valid_username("user_1"))

    def test_non_string(self):
        self.assertFalse(is_valid_username(123))


if __name__ == "__main__":
    unittest.main()
''',
    },
)

# ---------------------------------------------------------------- py-low-03 (holdout, locate & explain)
T["py-low-03"] = dict(
    meta=dict(
        language="python", complexity="low", split="holdout", pilot=False,
        objective="Investigate why parse_size('10KB') returns 10240 rather than 10000, "
                  "and write ANSWER.md at the repository root explaining the behavior. "
                  "Name the module, the function, and the constant responsible, and "
                  "state the multiplier value used for KB. Do not change any code.",
        objective_vague="size parsing output",
        misleading_hint="string handling in the CLI layer",
        scope="create ANSWER.md only; no code changes",
        allowed_paths=["ANSWER.md"],
        criteria="ANSWER.md exists, names parse_size and BINARY_BASE, and states 1024",
        test_cmd="python3 -m unittest discover -s tests -t . -v",
        stop="Stop once ANSWER.md is written.",
        expected_scope_files=1,
    ),
    fixture={
        "utils/__init__.py": "",
        "utils/size.py": '''\
BINARY_BASE = 1024

_SUFFIXES = {
    "B": 1,
    "KB": BINARY_BASE,
    "MB": BINARY_BASE ** 2,
    "GB": BINARY_BASE ** 3,
}


def parse_size(text):
    """Parse a human-readable size such as '10KB' into a number of bytes."""
    text = text.strip().upper()
    for suffix, mult in sorted(_SUFFIXES.items(), key=lambda kv: -len(kv[0])):
        if text.endswith(suffix):
            return int(float(text[: -len(suffix)]) * mult)
    return int(text)
''',
        "tests/__init__.py": "",
        "tests/test_answer.py": '''\
import os
import unittest


class TestAnswerExists(unittest.TestCase):
    def test_answer_file(self):
        self.assertTrue(os.path.exists("ANSWER.md"), "ANSWER.md must be created")
        body = open("ANSWER.md").read()
        self.assertIn("1024", body)


if __name__ == "__main__":
    unittest.main()
''',
    },
    hidden={
        "test_hidden.py": '''\
import os
import unittest


class TestAnswerHidden(unittest.TestCase):
    def test_names_the_cause(self):
        self.assertTrue(os.path.exists("ANSWER.md"))
        body = open("ANSWER.md").read()
        self.assertIn("parse_size", body)
        self.assertIn("BINARY_BASE", body)
        self.assertIn("1024", body)


if __name__ == "__main__":
    unittest.main()
''',
    },
)

# ---------------------------------------------------------------- py-med-01
T["py-med-01"] = dict(
    meta=dict(
        language="python", complexity="medium", split="dev", pilot=True,
        objective="Fix the checkout total bug: the flat coupon amount must be deducted "
                  "from the subtotal BEFORE tax is applied (see the docstring in "
                  "cart/checkout.py), but the current code deducts it after tax.",
        objective_vague="order totals",
        misleading_hint="rounding helpers in cart/pricing.py",
        scope="the cart package (cart/)",
        allowed_paths=["cart/checkout.py", "cart/pricing.py"],
        criteria="total(100, 10) == 99.0 and total(200, 50) == 165.0; every test under "
                 "tests/ passes",
        test_cmd="python3 -m unittest discover -s tests -t . -v",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "cart/__init__.py": "",
        "cart/pricing.py": '''\
TAX_RATE = 0.10


def taxed(amount):
    """Apply the sales tax to an amount."""
    return round(amount * (1 + TAX_RATE), 2)
''',
        "cart/checkout.py": '''\
from cart.pricing import taxed


def total(subtotal, coupon):
    """Compute the order total.

    The flat coupon amount is deducted from the subtotal before tax is
    applied. Tax applies only to what the customer actually pays for.
    """
    return round(taxed(subtotal) - coupon, 2)
''',
        "tests/__init__.py": "",
        "tests/test_checkout.py": '''\
import unittest

from cart.checkout import total


class TestCheckout(unittest.TestCase):
    def test_coupon_before_tax(self):
        self.assertEqual(total(100, 10), 99.0)

    def test_no_coupon(self):
        self.assertEqual(total(50, 0), 55.0)


if __name__ == "__main__":
    unittest.main()
''',
    },
    hidden={
        "test_hidden.py": '''\
import unittest

from cart.checkout import total


class TestCheckoutHidden(unittest.TestCase):
    def test_large_coupon(self):
        self.assertEqual(total(200, 50), 165.0)

    def test_coupon_equals_subtotal(self):
        self.assertEqual(total(20, 20), 0.0)


if __name__ == "__main__":
    unittest.main()
''',
    },
)

# ---------------------------------------------------------------- py-med-02
T["py-med-02"] = dict(
    meta=dict(
        language="python", complexity="medium", split="dev", pilot=False,
        objective="Add boolean support to config/parser.py: parse_value must map the "
                  "strings true/false/yes/no/on/off (case-insensitive) to Python bools. "
                  "Numeric strings keep their current behavior ('1' stays the int 1). "
                  "Unrecognized strings still pass through unchanged.",
        objective_vague="configuration parsing",
        misleading_hint="the integer branch",
        scope="config/parser.py only",
        allowed_paths=["config/parser.py"],
        criteria="parse_value('true') is True, parse_value('No') is False, "
                 "parse_value('1') == 1 (int), parse_value('tru') == 'tru'; every test "
                 "under tests/ passes",
        test_cmd="python3 -m unittest discover -s tests -t . -v",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "config/__init__.py": "",
        "config/parser.py": '''\
def parse_value(raw):
    """Parse a raw config string into int, float, or str."""
    if not isinstance(raw, str):
        return raw
    text = raw.strip()
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text
''',
        "tests/__init__.py": "",
        "tests/test_parser.py": '''\
import unittest

from config.parser import parse_value


class TestParser(unittest.TestCase):
    def test_true(self):
        self.assertIs(parse_value("true"), True)

    def test_no_mixed_case(self):
        self.assertIs(parse_value("No"), False)

    def test_int_stays_int(self):
        self.assertEqual(parse_value("1"), 1)
        self.assertIsInstance(parse_value("1"), int)


if __name__ == "__main__":
    unittest.main()
''',
    },
    hidden={
        "test_hidden.py": '''\
import unittest

from config.parser import parse_value


class TestParserHidden(unittest.TestCase):
    def test_yes_upper(self):
        self.assertIs(parse_value("YES"), True)

    def test_off(self):
        self.assertIs(parse_value("off"), False)

    def test_on(self):
        self.assertIs(parse_value("ON"), True)

    def test_unrecognized_passthrough(self):
        self.assertEqual(parse_value("tru"), "tru")

    def test_float_untouched(self):
        self.assertEqual(parse_value("2.5"), 2.5)


if __name__ == "__main__":
    unittest.main()
''',
    },
)

# ---------------------------------------------------------------- py-med-03 (holdout)
T["py-med-03"] = dict(
    meta=dict(
        language="python", complexity="medium", split="holdout", pilot=False,
        objective="Fix the serialization roundtrip in store/serialize.py: dump_record "
                  "encodes datetime values as {'__dt__': iso-string}, but load_record "
                  "does not revive them back into datetime objects. "
                  "load_record(dump_record(rec)) must equal rec, including datetimes "
                  "nested inside lists and dicts.",
        objective_vague="record storage",
        misleading_hint="the JSON encoder configuration",
        scope="store/serialize.py only",
        allowed_paths=["store/serialize.py"],
        criteria="roundtrip equality for flat and nested records with datetime values; "
                 "every test under tests/ passes",
        test_cmd="python3 -m unittest discover -s tests -t . -v",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "store/__init__.py": "",
        "store/serialize.py": '''\
import json
from datetime import datetime


def _encode(value):
    if isinstance(value, datetime):
        return {"__dt__": value.isoformat()}
    if isinstance(value, dict):
        return {k: _encode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_encode(v) for v in value]
    return value


def dump_record(rec):
    """Serialize a record (dict) to a JSON string."""
    return json.dumps(_encode(rec))


def load_record(text):
    """Deserialize a record produced by dump_record."""
    return json.loads(text)
''',
        "tests/__init__.py": "",
        "tests/test_serialize.py": '''\
import unittest
from datetime import datetime

from store.serialize import dump_record, load_record


class TestRoundtrip(unittest.TestCase):
    def test_flat_datetime(self):
        rec = {"name": "job", "at": datetime(2024, 1, 2, 3, 4, 5)}
        self.assertEqual(load_record(dump_record(rec)), rec)


if __name__ == "__main__":
    unittest.main()
''',
    },
    hidden={
        "test_hidden.py": '''\
import unittest
from datetime import datetime

from store.serialize import dump_record, load_record


class TestRoundtripHidden(unittest.TestCase):
    def test_microseconds(self):
        rec = {"at": datetime(2024, 6, 1, 12, 0, 0, 123456)}
        self.assertEqual(load_record(dump_record(rec)), rec)

    def test_nested(self):
        rec = {"events": [{"at": datetime(2023, 5, 5, 5, 5, 5)}, {"n": 1}],
               "meta": {"created": datetime(2022, 1, 1)}}
        self.assertEqual(load_record(dump_record(rec)), rec)

    def test_plain_dict_untouched(self):
        rec = {"a": 1, "b": [1, 2], "c": {"d": "x"}}
        self.assertEqual(load_record(dump_record(rec)), rec)


if __name__ == "__main__":
    unittest.main()
''',
    },
)

# ---------------------------------------------------------------- py-high-01
T["py-high-01"] = dict(
    meta=dict(
        language="python", complexity="high", split="dev", pilot=False,
        objective="Users are seeing each other's preferences. Diagnose the root cause "
                  "in the cachekit package and fix it: preferences stored for one user "
                  "must never appear for another user.",
        objective_vague="user preference storage",
        misleading_hint="the registry lookup logic in cachekit/registry.py",
        scope="the cachekit package (cachekit/)",
        allowed_paths=["cachekit/cache.py", "cachekit/registry.py"],
        criteria="preferences are isolated per user; every test under tests/ passes",
        test_cmd="python3 -m unittest discover -s tests -t . -v",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "cachekit/__init__.py": "",
        "cachekit/cache.py": '''\
class BucketCache:
    """A cache of named buckets. Each key gets its own bucket dict."""

    def __init__(self):
        self._store = {}

    def get_bucket(self, key, default={}):
        """Return the bucket for key, creating it from default if missing."""
        return self._store.setdefault(key, default)

    def keys(self):
        return list(self._store)
''',
        "cachekit/registry.py": '''\
from cachekit.cache import BucketCache


class PreferenceRegistry:
    """Per-user preference storage backed by BucketCache."""

    def __init__(self):
        self._cache = BucketCache()

    def set(self, user, key, value):
        self._cache.get_bucket(user)[key] = value

    def get(self, user, key):
        return self._cache.get_bucket(user).get(key)

    def users(self):
        return self._cache.keys()
''',
        "tests/__init__.py": "",
        "tests/test_registry.py": '''\
import unittest

from cachekit.registry import PreferenceRegistry


class TestIsolation(unittest.TestCase):
    def test_users_do_not_share_preferences(self):
        reg = PreferenceRegistry()
        reg.set("alice", "theme", "dark")
        self.assertIsNone(reg.get("bob", "theme"))

    def test_own_preference_persists(self):
        reg = PreferenceRegistry()
        reg.set("alice", "theme", "dark")
        self.assertEqual(reg.get("alice", "theme"), "dark")


if __name__ == "__main__":
    unittest.main()
''',
    },
    hidden={
        "test_hidden.py": '''\
import unittest

from cachekit.cache import BucketCache
from cachekit.registry import PreferenceRegistry


class TestIsolationHidden(unittest.TestCase):
    def test_three_users_independent(self):
        reg = PreferenceRegistry()
        for i, u in enumerate(["u1", "u2", "u3"]):
            reg.set(u, "lang", f"l{i}")
        self.assertEqual(reg.get("u1", "lang"), "l0")
        self.assertEqual(reg.get("u2", "lang"), "l1")
        self.assertEqual(reg.get("u3", "lang"), "l2")

    def test_cache_buckets_are_distinct_objects(self):
        c = BucketCache()
        a = c.get_bucket("a")
        b = c.get_bucket("b")
        self.assertIsNot(a, b)

    def test_existing_bucket_reused(self):
        c = BucketCache()
        a1 = c.get_bucket("a")
        a1["x"] = 1
        self.assertIs(c.get_bucket("a"), a1)


if __name__ == "__main__":
    unittest.main()
''',
    },
)

# ---------------------------------------------------------------- py-high-02
T["py-high-02"] = dict(
    meta=dict(
        language="python", complexity="high", split="dev", pilot=False,
        objective="Fix the event dispatcher bug in events/dispatcher.py: when a listener "
                  "unsubscribes itself during emit(), the next listener in order is "
                  "silently skipped. Every listener subscribed at the moment emit() "
                  "starts must be invoked exactly once for that event.",
        objective_vague="event delivery",
        misleading_hint="the unsubscribe bookkeeping in subscribe()",
        scope="events/dispatcher.py only",
        allowed_paths=["events/dispatcher.py"],
        criteria="self-unsubscribing listeners do not cause later listeners to be "
                 "skipped; every test under tests/ passes",
        test_cmd="python3 -m unittest discover -s tests -t . -v",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "events/__init__.py": "",
        "events/dispatcher.py": '''\
class Dispatcher:
    """A minimal synchronous event dispatcher."""

    def __init__(self):
        self._listeners = []

    def subscribe(self, fn):
        self._listeners.append(fn)
        return lambda: self.unsubscribe(fn)

    def unsubscribe(self, fn):
        if fn in self._listeners:
            self._listeners.remove(fn)

    def emit(self, event):
        for fn in self._listeners:
            fn(event)
''',
        "tests/__init__.py": "",
        "tests/test_dispatcher.py": '''\
import unittest

from events.dispatcher import Dispatcher


class TestDispatcher(unittest.TestCase):
    def test_self_unsubscribe_does_not_skip_next(self):
        d = Dispatcher()
        calls = []

        def one_shot(event):
            calls.append("one_shot")
            cancel()

        def steady(event):
            calls.append("steady")

        cancel = d.subscribe(one_shot)
        d.subscribe(steady)
        d.emit("e1")
        self.assertEqual(calls, ["one_shot", "steady"])


if __name__ == "__main__":
    unittest.main()
''',
    },
    hidden={
        "test_hidden.py": '''\
import unittest

from events.dispatcher import Dispatcher


class TestDispatcherHidden(unittest.TestCase):
    def test_two_one_shots_then_steady(self):
        d = Dispatcher()
        calls = []
        cancels = {}

        def make_one_shot(name):
            def fn(event):
                calls.append(name)
                cancels[name]()
            return fn

        for name in ("a", "b"):
            cancels[name] = d.subscribe(make_one_shot(name))
        d.subscribe(lambda e: calls.append("steady"))

        d.emit("e1")
        self.assertEqual(calls, ["a", "b", "steady"])

        calls.clear()
        d.emit("e2")
        self.assertEqual(calls, ["steady"])

    def test_unsubscribe_unknown_noop(self):
        d = Dispatcher()
        d.unsubscribe(lambda e: None)  # must not raise


if __name__ == "__main__":
    unittest.main()
''',
    },
)

# ---------------------------------------------------------------- py-high-03 (holdout)
T["py-high-03"] = dict(
    meta=dict(
        language="python", complexity="high", split="holdout", pilot=False,
        objective="The report pipeline drops data: totals come out short. Find the real "
                  "root cause in the pipeline package and fix it. The failing test is "
                  "tests/test_pipeline.py.",
        objective_vague="report totals",
        misleading_hint="the transform stage (pipeline/transform.py)",
        scope="the pipeline package (pipeline/)",
        allowed_paths=["pipeline/loader.py", "pipeline/transform.py", "pipeline/report.py"],
        criteria="totals include every data row exactly once; every test under tests/ "
                 "passes",
        test_cmd="python3 -m unittest discover -s tests -t . -v",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "pipeline/__init__.py": "",
        "pipeline/loader.py": '''\
def load_rows(text):
    """Parse CSV-ish text: first line is a header, the rest are value rows."""
    rows = [line.split(",") for line in text.strip().splitlines()]
    return rows[1:-1]
''',
        "pipeline/transform.py": '''\
# NOTE: the numeric coercion below has caused confusion before; if sums are
# wrong this stage is the usual suspect.
def to_amounts(rows):
    """Extract the numeric amount (second column) from each row."""
    amounts = []
    for row in rows:
        amounts.append(float(row[1]))
    return amounts
''',
        "pipeline/report.py": '''\
from pipeline.loader import load_rows
from pipeline.transform import to_amounts


def total_amount(text):
    return sum(to_amounts(load_rows(text)))
''',
        "tests/__init__.py": "",
        "tests/test_pipeline.py": '''\
import unittest

from pipeline.report import total_amount

SAMPLE = """name,amount
alpha,10.5
beta,2.5
gamma,7.0
"""


class TestPipeline(unittest.TestCase):
    def test_total_includes_all_rows(self):
        self.assertEqual(total_amount(SAMPLE), 20.0)


if __name__ == "__main__":
    unittest.main()
''',
    },
    hidden={
        "test_hidden.py": '''\
import unittest

from pipeline.loader import load_rows
from pipeline.report import total_amount


class TestPipelineHidden(unittest.TestCase):
    def test_single_data_row(self):
        self.assertEqual(total_amount("h,amount\\nonly,3.5\\n"), 3.5)

    def test_header_only(self):
        self.assertEqual(total_amount("h,amount\\n"), 0)

    def test_loader_keeps_last_row(self):
        rows = load_rows("h,v\\na,1\\nb,2\\n")
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
''',
    },
)


def write_all():
    for tid, spec in T.items():
        fixdir = FIX / tid
        for rel, content in spec["fixture"].items():
            p = fixdir / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        evdir = EVAL / tid
        evdir.mkdir(parents=True, exist_ok=True)
        for rel, content in spec["hidden"].items():
            (evdir / rel).write_text(content)
        (evdir / "eval.yaml").write_text(json.dumps({
            "hidden_copy": [{"src": name, "dst": f"tests_hidden/{name}"}
                            for name in spec["hidden"]] +
                           [{"src": "__init__.py", "dst": "tests_hidden/__init__.py"}],
            "hidden_cmd": "python3 -m unittest discover -s tests_hidden -t . -v",
        }, indent=1))
        (evdir / "__init__.py").write_text("")
        meta = dict(spec["meta"])
        meta["id"] = tid
        TASKS.mkdir(parents=True, exist_ok=True)
        (TASKS / f"{tid}.json").write_text(json.dumps(meta, indent=1))
    print(f"wrote {len(T)} python tasks")


if __name__ == "__main__":
    write_all()
