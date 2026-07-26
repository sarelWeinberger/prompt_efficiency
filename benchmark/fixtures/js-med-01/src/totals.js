// Line totals must be summed at full precision and rounded once, at the end.
const { lineTotal, round2 } = require("./cart");

function grandTotal(items) {
  return round2(items.map(lineTotal).reduce((a, b) => a + b, 0));
}

module.exports = { grandTotal };
