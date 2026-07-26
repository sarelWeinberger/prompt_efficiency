import unittest

from cachekit.cache import BucketCache
from cachekit.registry import PreferenceRegistry


class TestIsolationHidden(unittest.TestCase):
    def test_three_users_independent(self):
        reg = PreferenceRegistry()
        for i, u in enumerate(["u1", "u2", "u3"]):
            reg.set(u, "lang", f"l{i}")
        self.assertEqual(reg.get("u1", "lang"), "l0")
        self.assertEqual(reg.get("u2", "lang"), "l1")
        self.assertEqual(reg.get("u3", "lang"), "l2")

    def test_cache_buckets_are_distinct_objects(self):
        c = BucketCache()
        a = c.get_bucket("a")
        b = c.get_bucket("b")
        self.assertIsNot(a, b)

    def test_existing_bucket_reused(self):
        c = BucketCache()
        a1 = c.get_bucket("a")
        a1["x"] = 1
        self.assertIs(c.get_bucket("a"), a1)


if __name__ == "__main__":
    unittest.main()
