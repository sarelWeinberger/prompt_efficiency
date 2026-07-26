import unittest

from cart.checkout import total


class TestCheckoutHidden(unittest.TestCase):
    def test_large_coupon(self):
        self.assertEqual(total(200, 50), 165.0)

    def test_coupon_equals_subtotal(self):
        self.assertEqual(total(20, 20), 0.0)


if __name__ == "__main__":
    unittest.main()
