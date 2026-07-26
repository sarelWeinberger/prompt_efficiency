import unittest

from events.dispatcher import Dispatcher


class TestDispatcher(unittest.TestCase):
    def test_self_unsubscribe_does_not_skip_next(self):
        d = Dispatcher()
        calls = []

        def one_shot(event):
            calls.append("one_shot")
            cancel()

        def steady(event):
            calls.append("steady")

        cancel = d.subscribe(one_shot)
        d.subscribe(steady)
        d.emit("e1")
        self.assertEqual(calls, ["one_shot", "steady"])


if __name__ == "__main__":
    unittest.main()
