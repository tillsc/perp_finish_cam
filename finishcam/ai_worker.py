import asyncio
import logging

import cv2 as cv
import numpy as np

import finishcam.pubsub


def create_task(hub):
    return asyncio.create_task(start(hub))


async def start(hub):
    from perp_cnn.model import load_model

    logging.info("Loading AI model...")
    model = await asyncio.to_thread(load_model)
    logging.info("AI model ready")

    with finishcam.pubsub.Subscription(hub) as event:
        while True:
            await event.wait()
            event.clear()

            if "ai_input_image" not in hub.data:
                continue

            image = hub.data["ai_input_image"]
            try:
                result_image = await asyncio.to_thread(_run_inference, model, image)
                hub.publish(ai_output_image=result_image)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logging.warning("AI inference failed: %s", e)


def _run_inference(model, image: np.ndarray) -> np.ndarray:
    results = model.predict(image, verbose=False)
    out = image.copy()
    for box in results[0].boxes.xyxy.cpu().numpy().astype(int):
        cv.rectangle(out, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
    return out
