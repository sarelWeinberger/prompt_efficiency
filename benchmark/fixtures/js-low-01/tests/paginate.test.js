const test = require("node:test");
const assert = require("node:assert");
const { totalPages, pageItems } = require("../src/paginate");

test("partial final page counts", () => {
  assert.strictEqual(totalPages(10, 3), 4);
});

test("exact division", () => {
  assert.strictEqual(totalPages(9, 3), 3);
});

test("pageItems basic", () => {
  assert.deepStrictEqual(pageItems([1, 2, 3, 4, 5], 2, 2), [3, 4]);
});
