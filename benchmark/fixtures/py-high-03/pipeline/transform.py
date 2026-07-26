# NOTE: the numeric coercion below has caused confusion before; if sums are
# wrong this stage is the usual suspect.
def to_amounts(rows):
    """Extract the numeric amount (second column) from each row."""
    amounts = []
    for row in rows:
        amounts.append(float(row[1]))
    return amounts
