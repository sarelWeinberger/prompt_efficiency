const test = require("node:test");
const assert = require("node:assert");
const { serializeUser } = require("../src/serializer");

test("uses camelCase userName", () => {
  const out = serializeUser({ name: "ada", email: "a@x.io", active: 1 });
  assert.strictEqual(out.userName, "ada");
});
