import asyncio
import threading

import pytest

from finishcam.pubsub import Hub, Subscription


async def test_threadsafe_publish_from_thread_wakes_subscriber():
    hub = Hub()
    with Subscription(hub) as event:
        threading.Thread(target=lambda: hub.publish_threadsafe(value=42), daemon=True).start()
        await asyncio.wait_for(event.wait(), timeout=1.0)
    assert hub.data["value"] == 42


async def test_all_subscribers_notified_on_publish():
    hub = Hub()
    with Subscription(hub) as e1, Subscription(hub) as e2:
        hub.publish(x=1)
    assert e1.is_set() and e2.is_set()


async def test_subscription_unregisters_on_exit():
    hub = Hub()
    with Subscription(hub) as event:
        assert event in hub.subscriptions
    assert event not in hub.subscriptions
