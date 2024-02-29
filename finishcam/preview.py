import cv2 as cv

import asyncio
import logging

import finishcam.pubsub


def create_task(hub):
    return asyncio.create_task(start(hub))


async def start(hub):
    logging.debug("Enter preview loop")
    with finishcam.pubsub.Subscription(hub) as event:
        while not asyncio.current_task().done():
            await event.wait()
            for (field_name, window_name) in {"live_raw_image": "Raw image", "live_image": "Live image", "image": "Last image"}.items():
                if field_name in hub.data:
                    cv.imshow(window_name, hub.data.get(field_name))

            if cv.waitKey(10) == ord("q"):
                return
                
            event.clear()
