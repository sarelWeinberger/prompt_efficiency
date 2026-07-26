import unittest

from events.dispatcher import Dispatcher


class TestDispatcherHidden(unittest.TestCase):
    def test_two_one_shots_then_steady(self):
        d = Dispatcher()
        calls = []
        cancels = {}

        def make_one_shot(name):
            def fn(event):
                calls.append(name)
                cancels[name]()
            return fn

        for name in ("a", "b"):
            cancels[name] = d.subscribe(make_one_shot(name))
        d.subscribe(lambda e: calls.append("steady"))

        d.emit("e1")
        self.assertEqual(calls, ["a", "b", "steady"])

        calls.clear()
        d.emit("e2")
        self.assertEqual(calls, ["steady"])

    def test_unsubscribe_unknown_noop(self):
        d = Dispatcher()
        d.unsubscribe(lambda e: None)  # must not raise


if __name__ == "__main__":
    unittest.main()
