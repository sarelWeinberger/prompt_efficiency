import unittest

from config.parser import parse_value


class TestParser(unittest.TestCase):
    def test_true(self):
        self.assertIs(parse_value("true"), True)

    def test_no_mixed_case(self):
        self.assertIs(parse_value("No"), False)

    def test_int_stays_int(self):
        self.assertEqual(parse_value("1"), 1)
        self.assertIsInstance(parse_value("1"), int)


if __name__ == "__main__":
    unittest.main()
