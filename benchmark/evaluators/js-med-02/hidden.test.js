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
