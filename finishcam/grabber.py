import cv2 as cv
import time
import math
import os
import json
import asyncio
import threading
import logging
import platform

from finishcam.timespan_grabber import TimeSpanGrabber

def create_task(hub, session_name, outdir, time_span, fps, slot_width, left_to_right, shutdown_event, **kwargs):
    grabber = Grabber(
        hub, session_name, outdir,
        time_span, fps, slot_width, left_to_right, shutdown_event, **kwargs,
    )
    return asyncio.create_task(grabber.start())

class VideoException(Exception):
    """Exception raised when video capture fails."""
    pass

STAMPS_COLOR = (100, 255, 100)

class Grabber:
    def __init__(self, hub, session_name, outdir, time_span, fps, slot_width, left_to_right, shutdown_event: asyncio.Event, **kwargs):
        self.video_capture = None
        self.video_capture_lock = threading.Lock()  # needed because .read() runs in threads

        self.hub = hub
        self.session_name = session_name
        self.outdir = outdir
        self.time_span = time_span
        self.fps = fps
        self.slot_width = slot_width
        self.left_to_right = left_to_right
        self.shutdown_event = shutdown_event

        self.webp_quality = kwargs.get("webp_quality", 90)
        self.test_mode = kwargs.get("test_mode", 0)
        self.resolution = kwargs.get("resolution", "hd")
        self.video_capture_index = kwargs.get("video_capture_index", 0)
        self.stamp_options = {
            "time": kwargs.get("stamp_time", True),
            "fps": kwargs.get("stamp_fps", False),
            "ticks": kwargs.get("stamp_ticks", True),
            "tick-texts": kwargs.get("stamp_tick_texts", True),
        }

    async def start(self):
        os.makedirs(f"{self.outdir}/{self.session_name}", exist_ok=True)
        self.__init_video()

        try:
            await self.start_capture()
        finally:
            self.__stop_video()

    async def start_capture(self):
        self.time_first_start = time.time()
        i = 0

        # prime the first capture before entering loop
        current_capture = TimeSpanGrabber(self, self.time_first_start + i * self.time_span, i)
        wait_tasks = [asyncio.to_thread(current_capture.run)]
        last_capture = None

        self.__write_metadata_jsons(None)
        logging.debug("Enter capture loop")

        while not asyncio.current_task().done():
            next_capture = TimeSpanGrabber(self, self.time_first_start + (i + 1) * self.time_span, i + 1)
            next_capture_future = asyncio.to_thread(next_capture.run)

            if last_capture:
                # postprocess previous while next is running
                wait_tasks.append(asyncio.create_task(
                    asyncio.to_thread(self.__postprocess_capture, last_capture)
                ))

            try:
                await asyncio.gather(*wait_tasks)
            except asyncio.CancelledError:
                try:
                    # try to finish the next run even if not awaited
                    await next_capture_future
                except Exception:
                    pass
                break

            if current_capture.exit_after:
                break

            last_capture = current_capture
            current_capture = next_capture
            wait_tasks = [next_capture_future]
            i += 1

    def capture_frame(self):
        if self.video_capture is None or not self.video_capture.isOpened():
            raise VideoException("Video is closed")

        with self.video_capture_lock:  # ensure .read() is not interleaved
            ret, src = self.video_capture.read()
            if not ret:
                raise VideoException("Can't receive frame")

        return cv.flip(src, 1) if self.left_to_right else src

    def __postprocess_capture(self, last_capture):
        img = self.__stamp_image(last_capture.img, last_capture.metadata)
        self.hub.publish(image=img, metadata=last_capture.metadata)
        basename = self.__write_image_and_metadata(img, last_capture.metadata)
        logging.info("Image taken %s", basename)

    def __stamp_image(self, img, metadata):
        height, width = img.shape[:2]
        time_start = metadata.get("time_start")

        if self.stamp_options.get("time"):
            cv.putText(img, time.ctime(time_start), (4, height - 20),
                       cv.FONT_HERSHEY_SIMPLEX, 0.5, STAMPS_COLOR, 1, cv.LINE_AA)

        if self.stamp_options.get("fps"):
            cv.putText(img, f"{metadata.get('fps'):.2f} FPS", (4, 20),
                       cv.FONT_HERSHEY_SIMPLEX, 0.5, STAMPS_COLOR, 1, cv.LINE_AA)

        if self.stamp_options.get("ticks"):
            # draw vertical tick lines every second
            for ix in range(-1, self.time_span):
                x = round((ix + 1 - (time_start - math.floor(time_start))) * self.fps * self.slot_width)
                cv.line(img, (x, height - 10), (x, height), STAMPS_COLOR, 1)
                if self.stamp_options.get("tick-texts"):
                    tick_text = str((math.floor(time_start + 1 + ix) % 60))
                    cv.putText(img, tick_text, (x + 3, height - 3),
                               cv.FONT_HERSHEY_SIMPLEX, 0.3, STAMPS_COLOR, 1, cv.LINE_AA)
        return img

    def __write_metadata_jsons(self, last_index):
        # per-session metadata file
        session_meta_path = f"{self.outdir}/{self.session_name}/index.json"
        with open(session_meta_path, "w") as f:
            json.dump(self.__session_metadata(last_index), f)

        # shared metadata index across sessions
        global_meta_path = f"{self.outdir}/index.json"
        try:
            with open(global_meta_path, "r") as f:
                global_data = json.load(f)
        except FileNotFoundError:
            global_data = {}
        global_data[self.session_name] = self.__session_metadata(last_index)
        with open(global_meta_path, "w") as f:
            json.dump(global_data, f)

    def __write_image_and_metadata(self, img, metadata):
        basename = f'{self.outdir}/{self.session_name}/img{metadata["index"]}'
        cv.imwrite(f"{basename}.webp", img, [cv.IMWRITE_WEBP_QUALITY, self.webp_quality])
        with open(f"{basename}.json", "w") as f:
            json.dump(metadata, f, indent=4)
        self.__write_metadata_jsons(metadata["index"])
        return basename

    def __session_metadata(self, last_index):
        return {
            "session_name": self.session_name,
            "time_start": self.time_first_start,
            "time_span": self.time_span,
            "left_to_right": self.left_to_right,
            "px_per_second": self.fps * self.slot_width,
            "slot_width": self.slot_width,
            "last_index": last_index,
            "height": self.src_height,
        }

    def __init_video(self):
        # OpenCV backend choice depending on platform
        is_linux = platform.system() == "Linux"
        backend = cv.CAP_V4L2 if is_linux else cv.CAP_ANY
        self.video_capture = cv.VideoCapture(self.video_capture_index, backend)

        if is_linux:
            # Use MJPEG codec to improve frame rate stability (especially on Linux/V4L2)
            self.video_capture.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc(*'MJPG'))

        resolutions = {
            "qvga": (320, 240), "vga": (640, 480), "svga": (800, 600),
            "xga": (1024, 768), "wxga": (1280, 800), "hd": (1280, 720),
            "sxga": (1280, 1024), "uxga": (1600, 1200),
            "fullhd": (1920, 1080), "4k": (3840, 2160)
        }
        width, height = resolutions[self.resolution]
        self.video_capture.set(cv.CAP_PROP_FPS, self.fps)
        self.video_capture.set(cv.CAP_PROP_FRAME_WIDTH, width)
        self.video_capture.set(cv.CAP_PROP_FRAME_HEIGHT, height)

        if not self.video_capture.isOpened():
            raise VideoException("Cannot open camera")

        logging.info("Camera: %dx%d @ %.1f FPS",
                     self.video_capture.get(cv.CAP_PROP_FRAME_WIDTH),
                     self.video_capture.get(cv.CAP_PROP_FRAME_HEIGHT),
                     self.video_capture.get(cv.CAP_PROP_FPS))

        # read one frame to determine frame shape
        src = self.capture_frame()
        self.src_height, self.src_width = src.shape[:2]
        self.src_middle_left = self.src_width // 2

    def __stop_video(self):
        # release camera safely even if thread is reading
        if self.video_capture:
            with self.video_capture_lock:
                self.video_capture.release()
            self.video_capture = None
        cv.destroyAllWindows()
