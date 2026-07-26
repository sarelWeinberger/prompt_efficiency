class SimpleCache {
  constructor(ttlSeconds, clock = Date.now) {
    this.ttlSeconds = ttlSeconds;
    this.clock = clock;
    this.store = new Map();
  }

  set(key, value) {
    this.store.set(key, { value, at: this.clock() });
  }

  get(key) {
    const entry = this.store.get(key);
    if (!entry) return undefined;
    if (this.clock() - entry.at > this.ttlSeconds) {
      this.store.delete(key);
      return undefined;
    }
    return entry.value;
  }
}

module.exports = { SimpleCache };
