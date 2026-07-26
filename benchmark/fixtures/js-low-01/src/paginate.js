function totalPages(totalItems, perPage) {
  if (perPage <= 0) throw new Error("perPage must be positive");
  return Math.floor(totalItems / perPage);
}

function pageItems(items, page, perPage) {
  const start = (page - 1) * perPage;
  return items.slice(start, start + perPage);
}

module.exports = { totalPages, pageItems };
