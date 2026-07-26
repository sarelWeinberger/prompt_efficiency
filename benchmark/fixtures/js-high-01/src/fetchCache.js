class FetchCache {
  constructor(loader) {
    this.loader = loader;
    this.cache = new Map();
  }

  async get(key) {
    if (this.cache.has(key)) return this.cache.get(key);
    const value = await this.loader(key);
    this.cache.set(key, value);
    return value;
  }
}

module.exports = { FetchCache };
