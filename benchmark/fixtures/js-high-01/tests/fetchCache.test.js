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
