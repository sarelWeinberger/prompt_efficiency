import unittest
from datetime import datetime

from store.serialize import dump_record, load_record


class TestRoundtripHidden(unittest.TestCase):
    def test_microseconds(self):
        rec = {"at": datetime(2024, 6, 1, 12, 0, 0, 123456)}
        self.assertEqual(load_record(dump_record(rec)), rec)

    def test_nested(self):
        rec = {"events": [{"at": datetime(2023, 5, 5, 5, 5, 5)}, {"n": 1}],
               "meta": {"created": datetime(2022, 1, 1)}}
        self.assertEqual(load_record(dump_record(rec)), rec)

    def test_plain_dict_untouched(self):
        rec = {"a": 1, "b": [1, 2], "c": {"d": "x"}}
        self.assertEqual(load_record(dump_record(rec)), rec)


if __name__ == "__main__":
    unittest.main()
