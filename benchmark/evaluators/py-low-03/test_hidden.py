import os
import unittest


class TestAnswerHidden(unittest.TestCase):
    def test_names_the_cause(self):
        self.assertTrue(os.path.exists("ANSWER.md"))
        body = open("ANSWER.md").read()
        self.assertIn("parse_size", body)
        self.assertIn("BINARY_BASE", body)
        self.assertIn("1024", body)


if __name__ == "__main__":
    unittest.main()
