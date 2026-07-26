import unittest

from pipeline.loader import load_rows
from pipeline.report import total_amount


class TestPipelineHidden(unittest.TestCase):
    def test_single_data_row(self):
        self.assertEqual(total_amount("h,amount\nonly,3.5\n"), 3.5)

    def test_header_only(self):
        self.assertEqual(total_amount("h,amount\n"), 0)

    def test_loader_keeps_last_row(self):
        rows = load_rows("h,v\na,1\nb,2\n")
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
