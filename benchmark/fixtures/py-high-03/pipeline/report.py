from pipeline.loader import load_rows
from pipeline.transform import to_amounts


def total_amount(text):
    return sum(to_amounts(load_rows(text)))
