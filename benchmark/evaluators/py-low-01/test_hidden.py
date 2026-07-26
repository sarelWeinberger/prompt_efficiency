import unittest

from shop.discount import apply_discount


class TestDiscountHidden(unittest.TestCase):
    def test_full_discount(self):
        self.assertEqual(apply_discount(100, 100), 0.0)

    def test_fractional(self):
        self.assertEqual(apply_discount(80, 25), 60.0)

    def test_range_low(self):
        with self.assertRaises(ValueError):
            apply_discount(10, -1)

    def test_range_high(self):
        with self.assertRaises(ValueError):
            apply_discount(10, 101)


if __name__ == "__main__":
    unittest.main()
