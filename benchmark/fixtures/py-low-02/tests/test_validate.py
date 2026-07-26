import unittest

from users.validate import is_valid_username


class TestValidate(unittest.TestCase):
    def test_three_chars_valid(self):
        self.assertTrue(is_valid_username("abc"))

    def test_two_chars_invalid(self):
        self.assertFalse(is_valid_username("ab"))

    def test_twenty_chars_valid(self):
        self.assertTrue(is_valid_username("a" * 20))


if __name__ == "__main__":
    unittest.main()
