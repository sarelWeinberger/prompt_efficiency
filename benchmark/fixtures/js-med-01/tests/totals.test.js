const test = require("node:test");
const assert = require("node:assert");
const { grandTotal } = require("../src/totals");

test("rounds once at the end", () => {
  const items = [
    { price: 0.125, qty: 1 },
    { price: 0.125, qty: 1 },
    { price: 0.125, qty: 1 },
  ];
  assert.strictEqual(grandTotal(items), 0.38);
});

test("single item", () => {
  assert.strictEqual(grandTotal([{ price: 2, qty: 3 }]), 6);
});
