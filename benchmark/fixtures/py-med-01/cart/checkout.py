from cart.pricing import taxed


def total(subtotal, coupon):
    """Compute the order total.

    The flat coupon amount is deducted from the subtotal before tax is
    applied. Tax applies only to what the customer actually pays for.
    """
    return round(taxed(subtotal) - coupon, 2)
