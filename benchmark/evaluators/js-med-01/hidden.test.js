const test = require("node:test");
const assert = require("node:assert");
const { grandTotal } = require("../src/totals");

test("five eighth-cent items", () => {
  const items = Array.from({ length: 5 }, () => ({ price: 0.125, qty: 1 }));
  assert.strictEqual(grandTotal(items), 0.63);
});

test("empty cart", () => {
  assert.strictEqual(grandTotal([]), 0);
});
