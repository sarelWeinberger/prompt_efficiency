function round2(x) {
  return Math.round(x * 100) / 100;
}

function lineTotal(item) {
  return round2(item.price * item.qty);
}

module.exports = { lineTotal, round2 };
