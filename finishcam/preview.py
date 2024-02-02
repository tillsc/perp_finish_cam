import cv2 as cv

import asyncio
import logging

import finishcam.pubsub


def create_task(hub):
    return asyncio.create_task(start(hub))


async def start(hub):
    logging.debug("Enter preview loop")
    with finishcam.pubsub.Subscription(hub) as queue:
        while not asyncio.current_task().done():
            (msg, metadata, data) = await queue.get()
            logging.debug("Preview: %s", msg)
            match msg:
                case "live_image":
                    cv.imshow("Live", data)
                case "image":
                    cv.imshow("Last image", data)
                case "shutdown":
                    return
            if cv.waitKey(1) == ord("q"):
                return
