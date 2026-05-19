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

    last_processed_ts = None
    with finishcam.pubsub.Subscription(hub) as event:
        while True:
            await event.wait()
            event.clear()

            if "ai_input_image" not in hub.data:
                continue

            time_start = hub.data.get("ai_input_image_time_start", 0.0)
            if time_start == last_processed_ts:
                continue
            last_processed_ts = time_start

            image = hub.data["ai_input_image"]
            try:
                result_image, detections = await asyncio.to_thread(_run_inference, model, image, time_start)
                hub.publish(ai_output_image=result_image)
                if detections:
                    logging.info("AI detections: %s", detections)
                    hub.publish(ai_detections=detections)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logging.warning("AI inference failed: %s", e)


def _run_inference(model, image: np.ndarray, time_start: float) -> tuple:
    results = model.predict(image, verbose=False)
    out = image.copy()
    detections = []
    for box in results[0].boxes.xyxy.cpu().numpy().astype(int):
        cv.rectangle(out, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
        detections.append({
            "x": int((box[0] + box[2]) / 2),
            "y": int((box[1] + box[3]) / 2),
            "time_start": time_start,
        })
    return out, detections
