const test = require("node:test");
const assert = require("node:assert");
const { totalPages } = require("../src/paginate");

test("zero items", () => {
  assert.strictEqual(totalPages(0, 3), 0);
});

test("one item", () => {
  assert.strictEqual(totalPages(1, 3), 1);
});

test("perPage validation kept", () => {
  assert.throws(() => totalPages(5, 0));
});
