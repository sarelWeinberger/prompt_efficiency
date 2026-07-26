const test = require("node:test");
const assert = require("node:assert");
const { serializeUser } = require("../src/serializer");

test("old key removed, others intact", () => {
  const out = serializeUser({ name: "ada", email: "a@x.io", active: 0 });
  assert.ok(!("user_name" in out));
  assert.strictEqual(out.email, "a@x.io");
  assert.strictEqual(out.active, false);
});
