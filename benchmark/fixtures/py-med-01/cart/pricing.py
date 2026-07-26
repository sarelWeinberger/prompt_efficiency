TAX_RATE = 0.10


def taxed(amount):
    """Apply the sales tax to an amount."""
    return round(amount * (1 + TAX_RATE), 2)
