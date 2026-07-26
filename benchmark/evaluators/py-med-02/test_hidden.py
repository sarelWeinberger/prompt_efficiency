import unittest

from config.parser import parse_value


class TestParserHidden(unittest.TestCase):
    def test_yes_upper(self):
        self.assertIs(parse_value("YES"), True)

    def test_off(self):
        self.assertIs(parse_value("off"), False)

    def test_on(self):
        self.assertIs(parse_value("ON"), True)

    def test_unrecognized_passthrough(self):
        self.assertEqual(parse_value("tru"), "tru")

    def test_float_untouched(self):
        self.assertEqual(parse_value("2.5"), 2.5)


if __name__ == "__main__":
    unittest.main()
