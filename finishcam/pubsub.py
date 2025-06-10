import asyncio

class Hub:
    """Async pub/sub broker with shared data and event-based notification."""

    def __init__(self):
        self.subscriptions = set()
        self.data = {}
        self._loop = asyncio.get_running_loop()

    def publish(self, data=None, **kwargs):
        # Update shared data store with new values
        for key, value in kwargs.items():
            self.data[key] = value
        if data is not None:
            for key, value in data.items():
                self.data[key] = value
        # Wake up all subscribers
        for event in self.subscriptions:
            event.set()

    def publish_threadsafe(self, **kwargs):
        # Safe call from threads
        self._loop.call_soon_threadsafe(self.publish, kwargs)


class Subscription:
    """Context-managed subscriber to a Hub, using an asyncio.Event."""
    
    def __init__(self, hub):
        self.hub = hub
        self.event = asyncio.Event()

    def __enter__(self):
        # Register as subscriber
        self.hub.subscriptions.add(self.event)
        return self.event

    def __exit__(self, type, value, traceback):
        # Unregister on exit
        self.hub.subscriptions.remove(self.event)
