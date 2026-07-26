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
