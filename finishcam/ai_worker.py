import asyncio
import logging

import cv2 as cv
import numpy as np

import finishcam.pubsub


def is_available():
    import importlib.util
    return importlib.util.find_spec('perp_cnn') is not None


def create_task(hub):
    return asyncio.create_task(start(hub))


async def start(hub):
    logging.info("Downloading AI model...")
    await asyncio.to_thread(_download_model)
    logging.info("AI model downloaded")

    with finishcam.pubsub.Subscription(hub) as event:
        while not hub.data.get('ai_enabled', False):
            await event.wait()
            event.clear()

    logging.info("Loading AI model into RAM...")
    model = await asyncio.to_thread(_load_model)
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


def _download_model():
    from huggingface_hub import hf_hub_download
    from perp_cnn.model import HF_REPO_ID, HF_FILENAME
    hf_hub_download(repo_id=HF_REPO_ID, filename=HF_FILENAME)


def _load_model():
    from perp_cnn.model import load_model
    return load_model()


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
