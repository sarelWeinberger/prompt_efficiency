import unittest

from shop.discount import apply_discount


class TestDiscount(unittest.TestCase):
    def test_twenty_percent_off(self):
        self.assertEqual(apply_discount(100, 20), 80.0)

    def test_no_discount(self):
        self.assertEqual(apply_discount(50, 0), 50.0)


if __name__ == "__main__":
    unittest.main()
