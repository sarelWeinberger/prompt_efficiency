const test = require("node:test");
const assert = require("node:assert");
const { slugify } = require("../src/slugify");

test("collapses runs", () => {
  assert.strictEqual(slugify("a   b"), "a-b");
});

test("tabs and newlines", () => {
  assert.strictEqual(slugify("a\t b\n"), "a-b");
});
