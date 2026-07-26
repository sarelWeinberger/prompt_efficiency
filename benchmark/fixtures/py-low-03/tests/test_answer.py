import os
import unittest


class TestAnswerExists(unittest.TestCase):
    def test_answer_file(self):
        self.assertTrue(os.path.exists("ANSWER.md"), "ANSWER.md must be created")
        body = open("ANSWER.md").read()
        self.assertIn("1024", body)


if __name__ == "__main__":
    unittest.main()
