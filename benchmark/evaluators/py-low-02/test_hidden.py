import unittest

from users.validate import is_valid_username


class TestValidateHidden(unittest.TestCase):
    def test_twenty_one_invalid(self):
        self.assertFalse(is_valid_username("a" * 21))

    def test_uppercase_invalid(self):
        self.assertFalse(is_valid_username("Abc"))

    def test_underscore_digit_valid(self):
        self.assertTrue(is_valid_username("user_1"))

    def test_non_string(self):
        self.assertFalse(is_valid_username(123))


if __name__ == "__main__":
    unittest.main()
