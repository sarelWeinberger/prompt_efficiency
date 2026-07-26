const test = require("node:test");
const assert = require("node:assert");
const { slugify } = require("../src/slugify");

test("trims outer whitespace", () => {
  assert.strictEqual(slugify("  Hello World  "), "hello-world");
});

test("simple phrase", () => {
  assert.strictEqual(slugify("a b"), "a-b");
});
