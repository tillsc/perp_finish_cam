import asyncio

class Hub:
    def __init__(self):
        self.subscriptions = set()
        self.data = {}
        self._loop = asyncio.get_running_loop()

    def publish(self, data=None, **kwargs):
        for key, value in kwargs.items():
            self.data[key] = value
        if data != None:
            for key, value in data.items():
                self.data[key] = value
        for event in self.subscriptions:
            event.set()

    def publish_threadsafe(self, **kwargs):
        self._loop.call_soon_threadsafe(self.publish, kwargs)

class Subscription:
    def __init__(self, hub):
        self.hub = hub
        self.event = asyncio.Event()

    def __enter__(self):
        self.hub.subscriptions.add(self.event)
        return self.event

    def __exit__(self, type, value, traceback):
        self.hub.subscriptions.remove(self.event)
