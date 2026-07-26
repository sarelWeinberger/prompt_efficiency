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
