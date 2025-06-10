import cv2 as cv
import asyncio
import logging

import finishcam.pubsub

# Defines all supported preview modes and their corresponding Hub keys and window titles
PREVIEW_MODES = {
    "raw": ("live_raw_image", "Raw image"),
    "live": ("live_image", "Live image"),
    "final": ("image", "Last image"),
    "ai_input_image": ("ai_input_image", "Image for AI prediction"),
    "raw_ai_input_image": ("raw_ai_input_image", "Raw image for AI prediction"),
    "ai_output_image": ("ai_output_image", "Image with AI prediction results")
}

def create_task(hub, modes):
    """Creates and starts the live preview task."""
    return asyncio.create_task(start(hub, modes))

async def start(hub, modes: set[str]):
    """
    Continuously displays live preview windows for raw and processed images.

    Uses pubsub events to detect new frames and displays them in OpenCV windows.
    Exits when the current asyncio task is cancelled or 'q' is pressed.
    """
    logging.debug("Enter preview loop")
    modes_to_show = {
        key: title for mode, (key, title) in PREVIEW_MODES.items() if mode in modes
    }
    
    with finishcam.pubsub.Subscription(hub) as event:
        while not asyncio.current_task().done():
            await event.wait()

            for field, window in modes_to_show.items():
                if field in hub.data:
                    img = hub.data[field].copy()

                    if field == "live_raw_image":
                        # Draw semi-transparent green center line
                        h, w = img.shape[:2]
                        overlay = img.copy()
                        center_x = w // 2
                        cv.line(overlay, (center_x, 0), (center_x, h), (0, 255, 0), 2)
                        cv.addWeighted(overlay, 0.4, img, 0.6, 0, img)

                    cv.imshow(window, img)

            if cv.waitKey(10) == ord("q"):
                return  # allow quitting preview with 'q'

            event.clear()
