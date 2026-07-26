def load_rows(text):
    """Parse CSV-ish text: first line is a header, the rest are value rows."""
    rows = [line.split(",") for line in text.strip().splitlines()]
    return rows[1:-1]
