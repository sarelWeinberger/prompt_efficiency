class Dispatcher:
    """A minimal synchronous event dispatcher."""

    def __init__(self):
        self._listeners = []

    def subscribe(self, fn):
        self._listeners.append(fn)
        return lambda: self.unsubscribe(fn)

    def unsubscribe(self, fn):
        if fn in self._listeners:
            self._listeners.remove(fn)

    def emit(self, event):
        for fn in self._listeners:
            fn(event)
