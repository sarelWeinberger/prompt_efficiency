from cachekit.cache import BucketCache


class PreferenceRegistry:
    """Per-user preference storage backed by BucketCache."""

    def __init__(self):
        self._cache = BucketCache()

    def set(self, user, key, value):
        self._cache.get_bucket(user)[key] = value

    def get(self, user, key):
        return self._cache.get_bucket(user).get(key)

    def users(self):
        return self._cache.keys()
