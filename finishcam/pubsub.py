import asyncio
import logging


class Hub:
    def __init__(self):
        self.subscriptions = set()
        self._loop = asyncio.get_running_loop()

    def publish(self, message, metadata = {}, data=None):
        logging.debug("New Message: %s", message)
        for queue in self.subscriptions:
            queue.put_nowait((message, metadata, data))

    def publish_threadsafe(self, message, metadata = {}, data=None):
        self._loop.call_soon_threadsafe(self.publish, message, metadata, data)


class Subscription:
    def __init__(self, hub):
        self.hub = hub
        self.queue = asyncio.Queue()

    def __enter__(self):
        self.hub.subscriptions.add(self.queue)
        return self.queue

    def __exit__(self, type, value, traceback):
        self.hub.subscriptions.remove(self.queue)
