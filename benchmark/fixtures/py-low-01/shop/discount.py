def apply_discount(price, pct):
    """Return the price after applying a pct-percent discount.

    pct must be between 0 and 100 inclusive.
    """
    if pct < 0 or pct > 100:
        raise ValueError("pct out of range")
    return price * pct / 100
