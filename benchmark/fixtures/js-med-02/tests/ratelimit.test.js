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
