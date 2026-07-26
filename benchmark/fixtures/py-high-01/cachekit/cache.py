class BucketCache:
    """A cache of named buckets. Each key gets its own bucket dict."""

    def __init__(self):
        self._store = {}

    def get_bucket(self, key, default={}):
        """Return the bucket for key, creating it from default if missing."""
        return self._store.setdefault(key, default)

    def keys(self):
        return list(self._store)
