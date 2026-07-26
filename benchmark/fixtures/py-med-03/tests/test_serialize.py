import unittest
from datetime import datetime

from store.serialize import dump_record, load_record


class TestRoundtrip(unittest.TestCase):
    def test_flat_datetime(self):
        rec = {"name": "job", "at": datetime(2024, 1, 2, 3, 4, 5)}
        self.assertEqual(load_record(dump_record(rec)), rec)


if __name__ == "__main__":
    unittest.main()
