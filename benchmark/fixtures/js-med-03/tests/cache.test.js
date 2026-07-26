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
