import unittest

from cachekit.registry import PreferenceRegistry


class TestIsolation(unittest.TestCase):
    def test_users_do_not_share_preferences(self):
        reg = PreferenceRegistry()
        reg.set("alice", "theme", "dark")
        self.assertIsNone(reg.get("bob", "theme"))

    def test_own_preference_persists(self):
        reg = PreferenceRegistry()
        reg.set("alice", "theme", "dark")
        self.assertEqual(reg.get("alice", "theme"), "dark")


if __name__ == "__main__":
    unittest.main()
