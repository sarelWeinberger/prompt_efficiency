#!/usr/bin/env python3
"""Materialize the 9 JavaScript benchmark tasks (node:test, CommonJS, zero deps)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIX = ROOT / "fixtures"
TASKS = ROOT / "tasks"
EVAL = ROOT / "evaluators"

T = {}

# ---------------------------------------------------------------- js-low-01
T["js-low-01"] = dict(
    meta=dict(
        language="javascript", complexity="low", split="dev", pilot=False,
        objective="Fix the pagination bug in src/paginate.js: totalPages must round UP "
                  "(a partial final page counts as a page).",
        objective_vague="pagination",
        misleading_hint="the slice bounds in pageItems",
        scope="src/paginate.js only",
        allowed_paths=["src/paginate.js"],
        criteria="totalPages(10, 3) === 4; every test under tests/ passes",
        test_cmd="node --test tests/*.test.js",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "src/paginate.js": '''\
function totalPages(totalItems, perPage) {
  if (perPage <= 0) throw new Error("perPage must be positive");
  return Math.floor(totalItems / perPage);
}

function pageItems(items, page, perPage) {
  const start = (page - 1) * perPage;
  return items.slice(start, start + perPage);
}

module.exports = { totalPages, pageItems };
''',
        "tests/paginate.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { totalPages, pageItems } = require("../src/paginate");

test("partial final page counts", () => {
  assert.strictEqual(totalPages(10, 3), 4);
});

test("exact division", () => {
  assert.strictEqual(totalPages(9, 3), 3);
});

test("pageItems basic", () => {
  assert.deepStrictEqual(pageItems([1, 2, 3, 4, 5], 2, 2), [3, 4]);
});
''',
    },
    hidden={
        "hidden.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { totalPages } = require("../src/paginate");

test("zero items", () => {
  assert.strictEqual(totalPages(0, 3), 0);
});

test("one item", () => {
  assert.strictEqual(totalPages(1, 3), 1);
});

test("perPage validation kept", () => {
  assert.throws(() => totalPages(5, 0));
});
''',
    },
)

# ---------------------------------------------------------------- js-low-02 (holdout)
T["js-low-02"] = dict(
    meta=dict(
        language="javascript", complexity="low", split="holdout", pilot=False,
        objective="Adjust one API field in src/serializer.js: the serialized user object "
                  "must expose the name under the key userName (camelCase) instead of "
                  "user_name. All other fields stay exactly as they are.",
        objective_vague="API response fields",
        misleading_hint="a consumer-side mapping",
        scope="src/serializer.js only",
        allowed_paths=["src/serializer.js"],
        criteria="serializeUser output has userName and no user_name; email unchanged; "
                 "every test under tests/ passes",
        test_cmd="node --test tests/*.test.js",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "src/serializer.js": '''\
function serializeUser(user) {
  return {
    user_name: user.name,
    email: user.email,
    active: Boolean(user.active),
  };
}

module.exports = { serializeUser };
''',
        "tests/serializer.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { serializeUser } = require("../src/serializer");

test("uses camelCase userName", () => {
  const out = serializeUser({ name: "ada", email: "a@x.io", active: 1 });
  assert.strictEqual(out.userName, "ada");
});
''',
    },
    hidden={
        "hidden.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { serializeUser } = require("../src/serializer");

test("old key removed, others intact", () => {
  const out = serializeUser({ name: "ada", email: "a@x.io", active: 0 });
  assert.ok(!("user_name" in out));
  assert.strictEqual(out.email, "a@x.io");
  assert.strictEqual(out.active, false);
});
''',
    },
)

# ---------------------------------------------------------------- js-low-03
T["js-low-03"] = dict(
    meta=dict(
        language="javascript", complexity="low", split="dev", pilot=False,
        objective="Repair the failing unit test for src/slugify.js by fixing the code "
                  "(the test is correct): slugify must trim leading/trailing whitespace "
                  "and collapse internal whitespace runs into single hyphens.",
        objective_vague="URL slug generation",
        misleading_hint="the test expectations",
        scope="src/slugify.js only",
        allowed_paths=["src/slugify.js"],
        criteria='slugify("  Hello World  ") === "hello-world"; internal runs collapse; '
                 "every test under tests/ passes",
        test_cmd="node --test tests/*.test.js",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "src/slugify.js": '''\
function slugify(text) {
  return text.toLowerCase().replace(/ /g, "-");
}

module.exports = { slugify };
''',
        "tests/slugify.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { slugify } = require("../src/slugify");

test("trims outer whitespace", () => {
  assert.strictEqual(slugify("  Hello World  "), "hello-world");
});

test("simple phrase", () => {
  assert.strictEqual(slugify("a b"), "a-b");
});
''',
    },
    hidden={
        "hidden.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { slugify } = require("../src/slugify");

test("collapses runs", () => {
  assert.strictEqual(slugify("a   b"), "a-b");
});

test("tabs and newlines", () => {
  assert.strictEqual(slugify("a\\t b\\n"), "a-b");
});
''',
    },
)

# ---------------------------------------------------------------- js-med-01
T["js-med-01"] = dict(
    meta=dict(
        language="javascript", complexity="medium", split="dev", pilot=False,
        objective="Fix the rounding drift across src/cart.js and src/totals.js: line "
                  "totals must be summed at full precision and rounded ONCE at the end "
                  "(see the note in src/totals.js). Currently each line is rounded "
                  "before summing, which drifts the grand total.",
        objective_vague="cart totals",
        misleading_hint="floating point comparison in the tests",
        scope="src/cart.js and src/totals.js",
        allowed_paths=["src/cart.js", "src/totals.js"],
        criteria="grandTotal of three {price: 0.125, qty: 1} items === 0.38; every test "
                 "under tests/ passes",
        test_cmd="node --test tests/*.test.js",
        stop="Stop when the tests pass.",
        expected_scope_files=2,
    ),
    fixture={
        "src/cart.js": '''\
function round2(x) {
  return Math.round(x * 100) / 100;
}

function lineTotal(item) {
  return round2(item.price * item.qty);
}

module.exports = { lineTotal, round2 };
''',
        "src/totals.js": '''\
// Line totals must be summed at full precision and rounded once, at the end.
const { lineTotal, round2 } = require("./cart");

function grandTotal(items) {
  return round2(items.map(lineTotal).reduce((a, b) => a + b, 0));
}

module.exports = { grandTotal };
''',
        "tests/totals.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { grandTotal } = require("../src/totals");

test("rounds once at the end", () => {
  const items = [
    { price: 0.125, qty: 1 },
    { price: 0.125, qty: 1 },
    { price: 0.125, qty: 1 },
  ];
  assert.strictEqual(grandTotal(items), 0.38);
});

test("single item", () => {
  assert.strictEqual(grandTotal([{ price: 2, qty: 3 }]), 6);
});
''',
    },
    hidden={
        "hidden.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { grandTotal } = require("../src/totals");

test("five eighth-cent items", () => {
  const items = Array.from({ length: 5 }, () => ({ price: 0.125, qty: 1 }));
  assert.strictEqual(grandTotal(items), 0.63);
});

test("empty cart", () => {
  assert.strictEqual(grandTotal([]), 0);
});
''',
    },
)

# ---------------------------------------------------------------- js-med-02
T["js-med-02"] = dict(
    meta=dict(
        language="javascript", complexity="medium", split="dev", pilot=False,
        objective="Add a burst allowance to src/ratelimit.js: the constructor must "
                  "accept an options object as third argument, new RateLimiter(limit, "
                  "windowMs, {burst: n}), permitting at most limit+n requests per "
                  "window (default burst 0, existing behavior unchanged). Also add a "
                  "remaining() method returning how many requests are still allowed in "
                  "the current window.",
        objective_vague="request throttling",
        misleading_hint="the timestamp pruning loop",
        scope="src/ratelimit.js only",
        allowed_paths=["src/ratelimit.js"],
        criteria="limit 2 + burst 1 permits exactly 3 requests per window; remaining() "
                 "reports correctly; every test under tests/ passes",
        test_cmd="node --test tests/*.test.js",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "src/ratelimit.js": '''\
class RateLimiter {
  constructor(limit, windowMs, clock = Date.now) {
    this.limit = limit;
    this.windowMs = windowMs;
    this.clock = clock;
    this.hits = [];
  }

  allow() {
    const now = this.clock();
    this.hits = this.hits.filter((t) => now - t < this.windowMs);
    if (this.hits.length >= this.limit) return false;
    this.hits.push(now);
    return true;
  }
}

module.exports = { RateLimiter };
''',
        "tests/ratelimit.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { RateLimiter } = require("../src/ratelimit");

function fakeClock(start = 0) {
  let t = start;
  const fn = () => t;
  fn.advance = (ms) => { t += ms; };
  return fn;
}

test("burst extends the window capacity", () => {
  const clock = fakeClock();
  const rl = new RateLimiter(2, 1000, { burst: 1, clock });
  assert.strictEqual(rl.allow(), true);
  assert.strictEqual(rl.allow(), true);
  assert.strictEqual(rl.allow(), true);
  assert.strictEqual(rl.allow(), false);
});

test("remaining counts down", () => {
  const clock = fakeClock();
  const rl = new RateLimiter(2, 1000, { burst: 0, clock });
  assert.strictEqual(rl.remaining(), 2);
  rl.allow();
  assert.strictEqual(rl.remaining(), 1);
});
''',
    },
    hidden={
        "hidden.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { RateLimiter } = require("../src/ratelimit");

function fakeClock(start = 0) {
  let t = start;
  const fn = () => t;
  fn.advance = (ms) => { t += ms; };
  return fn;
}

test("window slides and resets capacity", () => {
  const clock = fakeClock();
  const rl = new RateLimiter(1, 1000, { burst: 1, clock });
  assert.strictEqual(rl.allow(), true);
  assert.strictEqual(rl.allow(), true);
  assert.strictEqual(rl.allow(), false);
  clock.advance(1001);
  assert.strictEqual(rl.allow(), true);
});

test("default burst is zero", () => {
  const clock = fakeClock();
  const rl = new RateLimiter(1, 1000, { clock });
  assert.strictEqual(rl.allow(), true);
  assert.strictEqual(rl.allow(), false);
});
''',
    },
)

# ---------------------------------------------------------------- js-med-03
T["js-med-03"] = dict(
    meta=dict(
        language="javascript", complexity="medium", split="dev", pilot=True,
        objective="Fix the cache-expiration bug in src/cache.js: ttl is given in "
                  "SECONDS but the expiry check compares it against elapsed "
                  "MILLISECONDS, so entries expire ~1000x too early. An entry must "
                  "expire strictly after ttl seconds (at exactly ttl seconds it is "
                  "still valid).",
        objective_vague="cache expiry",
        misleading_hint="the Map iteration order",
        scope="src/cache.js only",
        allowed_paths=["src/cache.js"],
        criteria="entry with ttl 5 still present after 2000ms and gone after 6000ms; "
                 "boundary at exactly 5000ms still valid; every test under tests/ passes",
        test_cmd="node --test tests/*.test.js",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "src/cache.js": '''\
class SimpleCache {
  constructor(ttlSeconds, clock = Date.now) {
    this.ttlSeconds = ttlSeconds;
    this.clock = clock;
    this.store = new Map();
  }

  set(key, value) {
    this.store.set(key, { value, at: this.clock() });
  }

  get(key) {
    const entry = this.store.get(key);
    if (!entry) return undefined;
    if (this.clock() - entry.at > this.ttlSeconds) {
      this.store.delete(key);
      return undefined;
    }
    return entry.value;
  }
}

module.exports = { SimpleCache };
''',
        "tests/cache.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { SimpleCache } = require("../src/cache");

function fakeClock(start = 0) {
  let t = start;
  const fn = () => t;
  fn.advance = (ms) => { t += ms; };
  return fn;
}

test("entry survives within ttl", () => {
  const clock = fakeClock();
  const c = new SimpleCache(5, clock);
  c.set("k", "v");
  clock.advance(2000);
  assert.strictEqual(c.get("k"), "v");
});

test("entry expires after ttl", () => {
  const clock = fakeClock();
  const c = new SimpleCache(5, clock);
  c.set("k", "v");
  clock.advance(6000);
  assert.strictEqual(c.get("k"), undefined);
});
''',
    },
    hidden={
        "hidden.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { SimpleCache } = require("../src/cache");

function fakeClock(start = 0) {
  let t = start;
  const fn = () => t;
  fn.advance = (ms) => { t += ms; };
  return fn;
}

test("boundary: exactly ttl seconds is still valid", () => {
  const clock = fakeClock();
  const c = new SimpleCache(5, clock);
  c.set("k", "v");
  clock.advance(5000);
  assert.strictEqual(c.get("k"), "v");
});

test("expired entry is evicted from the store", () => {
  const clock = fakeClock();
  const c = new SimpleCache(1, clock);
  c.set("k", "v");
  clock.advance(1500);
  c.get("k");
  assert.strictEqual(c.store.has("k"), false);
});
''',
    },
)

# ---------------------------------------------------------------- js-high-01
T["js-high-01"] = dict(
    meta=dict(
        language="javascript", complexity="high", split="dev", pilot=True,
        objective="Fix two related defects in src/fetchCache.js: (1) concurrent get() "
                  "calls for the same key must trigger the loader only once (in-flight "
                  "deduplication); (2) a loader failure must NOT be cached — the next "
                  "get() for that key must retry the loader.",
        objective_vague="data fetching layer",
        misleading_hint="the Map key comparison",
        scope="src/fetchCache.js only",
        allowed_paths=["src/fetchCache.js"],
        criteria="two concurrent gets for one key call the loader once; a rejected load "
                 "is retried on the next get; every test under tests/ passes",
        test_cmd="node --test tests/*.test.js",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "src/fetchCache.js": '''\
class FetchCache {
  constructor(loader) {
    this.loader = loader;
    this.cache = new Map();
  }

  async get(key) {
    if (this.cache.has(key)) return this.cache.get(key);
    const value = await this.loader(key);
    this.cache.set(key, value);
    return value;
  }
}

module.exports = { FetchCache };
''',
        "tests/fetchCache.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { FetchCache } = require("../src/fetchCache");

test("concurrent gets dedupe the loader call", async () => {
  let calls = 0;
  const cache = new FetchCache(async (key) => {
    calls += 1;
    await new Promise((r) => setImmediate(r));
    return key.toUpperCase();
  });
  const [a, b] = await Promise.all([cache.get("x"), cache.get("x")]);
  assert.strictEqual(a, "X");
  assert.strictEqual(b, "X");
  assert.strictEqual(calls, 1);
});

test("sequential gets use the cache", async () => {
  let calls = 0;
  const cache = new FetchCache(async () => { calls += 1; return 1; });
  await cache.get("k");
  await cache.get("k");
  assert.strictEqual(calls, 1);
});
''',
    },
    hidden={
        "hidden.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { FetchCache } = require("../src/fetchCache");

test("rejection is not cached; next get retries", async () => {
  let calls = 0;
  const cache = new FetchCache(async () => {
    calls += 1;
    if (calls === 1) throw new Error("boom");
    return "ok";
  });
  await assert.rejects(() => cache.get("k"));
  assert.strictEqual(await cache.get("k"), "ok");
  assert.strictEqual(calls, 2);
});

test("different keys load independently", async () => {
  let calls = 0;
  const cache = new FetchCache(async (k) => { calls += 1; return k; });
  await Promise.all([cache.get("a"), cache.get("b")]);
  assert.strictEqual(calls, 2);
});
''',
    },
)

# ---------------------------------------------------------------- js-high-02
T["js-high-02"] = dict(
    meta=dict(
        language="javascript", complexity="high", split="dev", pilot=False,
        objective="Perform a scoped, backward-compatible refactor of src/client.js: "
                  "getUser(id, callback) must additionally support promise style — "
                  "when no callback is given it returns a Promise resolving to the "
                  "user (or rejecting on error). Callback style must keep working "
                  "exactly as before (including error-first callback semantics).",
        objective_vague="client API style",
        misleading_hint="the user lookup table",
        scope="src/client.js only",
        allowed_paths=["src/client.js"],
        criteria="both styles work for success and error paths; every test under "
                 "tests/ passes",
        test_cmd="node --test tests/*.test.js",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "src/client.js": '''\
const USERS = { 1: { id: 1, name: "ada" }, 2: { id: 2, name: "lin" } };

function getUser(id, callback) {
  setImmediate(() => {
    const user = USERS[id];
    if (!user) return callback(new Error("not found"));
    callback(null, user);
  });
}

module.exports = { getUser };
''',
        "tests/client.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { getUser } = require("../src/client");

test("callback style still works", (t, done) => {
  getUser(1, (err, user) => {
    assert.ifError(err);
    assert.strictEqual(user.name, "ada");
    done();
  });
});

test("promise style resolves", async () => {
  const user = await getUser(2);
  assert.strictEqual(user.name, "lin");
});
''',
    },
    hidden={
        "hidden.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { getUser } = require("../src/client");

test("promise style rejects on missing user", async () => {
  await assert.rejects(() => getUser(99), /not found/);
});

test("callback style error-first on missing user", (t, done) => {
  getUser(99, (err, user) => {
    assert.ok(err instanceof Error);
    assert.strictEqual(user, undefined);
    done();
  });
});
''',
    },
)

# ---------------------------------------------------------------- js-high-03 (holdout)
T["js-high-03"] = dict(
    meta=dict(
        language="javascript", complexity="high", split="holdout", pilot=False,
        objective="Jobs are being processed more than once. Find the real root cause "
                  "across src/ and fix it: each job pushed onto the queue must be "
                  "handled exactly once.",
        objective_vague="job processing counts",
        misleading_hint="the queue implementation (src/queue.js)",
        scope="the src/ directory",
        allowed_paths=["src/queue.js", "src/worker.js", "src/index.js"],
        criteria="each job handled exactly once across multiple poll ticks; every test "
                 "under tests/ passes",
        test_cmd="node --test tests/*.test.js",
        stop="Stop when the tests pass.",
        expected_scope_files=1,
    ),
    fixture={
        "src/queue.js": '''\
class JobQueue {
  constructor() {
    this.jobs = [];
    this.handlers = [];
  }

  on(event, fn) {
    if (event === "job") this.handlers.push(fn);
  }

  push(job) {
    this.jobs.push(job);
  }

  drain() {
    const pending = this.jobs.splice(0);
    for (const job of pending) {
      for (const fn of this.handlers) fn(job);
    }
  }
}

module.exports = { JobQueue };
''',
        "src/worker.js": '''\
class Worker {
  constructor(queue, handler) {
    this.queue = queue;
    this.handler = handler;
  }

  poll() {
    this.queue.on("job", this.handler);
    this.queue.drain();
  }
}

module.exports = { Worker };
''',
        "src/index.js": '''\
// NOTE: duplicate processing has been reported; the queue implementation in
// queue.js is the prime suspect according to the previous maintainer.
const { JobQueue } = require("./queue");
const { Worker } = require("./worker");

function makePipeline(handler) {
  const queue = new JobQueue();
  const worker = new Worker(queue, handler);
  return { queue, worker };
}

module.exports = { makePipeline };
''',
        "tests/pipeline.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { makePipeline } = require("../src/index");

test("each job handled exactly once across ticks", () => {
  const handled = [];
  const { queue, worker } = makePipeline((job) => handled.push(job));
  queue.push("j1");
  worker.poll();
  queue.push("j2");
  worker.poll();
  assert.deepStrictEqual(handled, ["j1", "j2"]);
});
''',
    },
    hidden={
        "hidden.test.js": '''\
const test = require("node:test");
const assert = require("node:assert");
const { makePipeline } = require("../src/index");

test("three ticks, three jobs, three handlings", () => {
  const handled = [];
  const { queue, worker } = makePipeline((job) => handled.push(job));
  for (const j of ["a", "b", "c"]) {
    queue.push(j);
    worker.poll();
  }
  assert.deepStrictEqual(handled, ["a", "b", "c"]);
});
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
                            for name in spec["hidden"]],
            "hidden_cmd": "node --test tests_hidden/*.test.js",
        }, indent=1))
        meta = dict(spec["meta"])
        meta["id"] = tid
        TASKS.mkdir(parents=True, exist_ok=True)
        (TASKS / f"{tid}.json").write_text(json.dumps(meta, indent=1))
    print(f"wrote {len(T)} javascript tasks")


if __name__ == "__main__":
    write_all()
