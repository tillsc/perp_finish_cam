import asyncio
import cv2 as cv
import json
import logging
import math
import time

import finishcam.pubsub

STAMPS_COLOR = (100, 255, 100)


def create_task(hub, outdir, **kwargs):
    return asyncio.create_task(Postprocessor(outdir, **kwargs).start(hub))


class Postprocessor:
    def __init__(self, outdir, **kwargs):
        self.outdir = outdir
        self.webp_quality = kwargs.get("webp_quality", 90)
        self.stamp_options = {
            "time": kwargs.get("stamp_time", True),
            "fps": kwargs.get("stamp_fps", False),
            "ticks": kwargs.get("stamp_ticks", True),
            "tick-texts": kwargs.get("stamp_tick_texts", True),
        }

    async def start(self, hub):
        last_processed_index = None
        session_meta = None
        with finishcam.pubsub.Subscription(hub) as event:
            while True:
                await event.wait()
                event.clear()

                if "session_started" in hub.data:
                    session_meta = hub.data.pop("session_started")
                    self._write_metadata_jsons(session_meta)

                if "completed_scan" not in hub.data:
                    continue

                scan = hub.data["completed_scan"]
                if scan.index == last_processed_index:
                    continue
                last_processed_index = scan.index

                await asyncio.to_thread(self._process, hub, scan, session_meta)

    def _process(self, hub, scan, session_meta):
        target_fps = scan.px_per_second / scan.slot_width
        if scan.fps > target_fps * 1.10:
            logging.info("Real FPS (%.1f f/s) allows higher px_per_second", scan.fps)
        if scan.fps < target_fps * 0.90:
            logging.warning("Real FPS (%.1f f/s) is much lower than requested", scan.fps)

        img = self._stamp(scan.image, scan)
        hub.publish_threadsafe(image=img, metadata=scan.metadata)
        session_meta["last_index"] = scan.index
        basename = self._write(img, scan.metadata, session_meta)
        logging.info("Image taken %s", basename)

    def _stamp(self, img, scan):
        height = img.shape[0]

        if self.stamp_options.get("time"):
            cv.putText(img, time.ctime(scan.time_start), (4, height - 20),
                       cv.FONT_HERSHEY_SIMPLEX, 0.5, STAMPS_COLOR, 1, cv.LINE_AA)

        if self.stamp_options.get("fps"):
            cv.putText(img, f"{scan.fps:.2f} FPS", (4, 20),
                       cv.FONT_HERSHEY_SIMPLEX, 0.5, STAMPS_COLOR, 1, cv.LINE_AA)

        if self.stamp_options.get("ticks"):
            for ix in range(-1, scan.time_span):
                x = round((ix + 1 - (scan.time_start - math.floor(scan.time_start))) * scan.px_per_second)
                cv.line(img, (x, height - 10), (x, height), STAMPS_COLOR, 1)
                if self.stamp_options.get("tick-texts"):
                    tick_text = str(math.floor(scan.time_start + 1 + ix) % 60)
                    cv.putText(img, tick_text, (x + 3, height - 3),
                               cv.FONT_HERSHEY_SIMPLEX, 0.3, STAMPS_COLOR, 1, cv.LINE_AA)
        return img

    def _write(self, img, slot_metadata, session_meta):
        basename = f'{self.outdir}/{session_meta["session_name"]}/img{session_meta["last_index"]}'
        cv.imwrite(f"{basename}.webp", img, [cv.IMWRITE_WEBP_QUALITY, self.webp_quality])
        with open(f"{basename}.json", "w") as f:
            json.dump(slot_metadata, f, indent=4)
        self._write_metadata_jsons(session_meta)
        return basename

    def _write_metadata_jsons(self, session_meta):
        with open(f"{self.outdir}/{session_meta['session_name']}/index.json", "w") as f:
            json.dump(session_meta, f)

        global_meta_path = f"{self.outdir}/index.json"
        try:
            with open(global_meta_path, "r") as f:
                global_data = json.load(f)
        except FileNotFoundError:
            global_data = {}
        global_data[session_meta['session_name']] = session_meta
        with open(global_meta_path, "w") as f:
            json.dump(global_data, f)
