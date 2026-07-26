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
