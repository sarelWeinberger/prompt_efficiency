import unittest

from cart.checkout import total


class TestCheckout(unittest.TestCase):
    def test_coupon_before_tax(self):
        self.assertEqual(total(100, 10), 99.0)

    def test_no_coupon(self):
        self.assertEqual(total(50, 0), 55.0)


if __name__ == "__main__":
    unittest.main()
