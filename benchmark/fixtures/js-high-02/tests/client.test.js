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
