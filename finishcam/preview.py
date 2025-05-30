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
            for (field_name, window_name) in {
                "live_raw_image": "Raw image",
                "live_image": "Live image",
               # "image": "Last image"
            }.items():
                if field_name in hub.data:
                    img = hub.data.get(field_name).copy()

                    if field_name == "live_raw_image":
                        # draw a semi-transparent green vertical line in the center
                        h, w = img.shape[:2]
                        overlay = img.copy()
                        center_x = w // 2
                        line_width = 2
                        cv.line(overlay, (center_x, 0), (center_x, h), (0, 255, 0), thickness=line_width)
                        alpha = 0.4  # transparency factor
                        cv.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)

                    cv.imshow(window_name, img)

            if cv.waitKey(10) == ord("q"):
                return

            event.clear()
