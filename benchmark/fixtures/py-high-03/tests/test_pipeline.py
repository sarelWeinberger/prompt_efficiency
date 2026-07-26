import unittest

from pipeline.report import total_amount

SAMPLE = """name,amount
alpha,10.5
beta,2.5
gamma,7.0
"""


class TestPipeline(unittest.TestCase):
    def test_total_includes_all_rows(self):
        self.assertEqual(total_amount(SAMPLE), 20.0)


if __name__ == "__main__":
    unittest.main()
