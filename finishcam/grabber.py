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

def create_task(
    hub, session_name, outdir,
    time_span, fps, slot_width, left_to_right, shutdown_event, **kwargs
    ):
    gr = Grabber(
        hub, session_name, outdir,
        time_span, fps, slot_width, left_to_right, shutdown_event, **kwargs,
    )
    return asyncio.create_task(gr.start())


class VideoException(Exception):
    "Exception raised on problems with video capture"
    pass

STAMPS_COLOR = (100, 255, 100)

class Grabber:
    def __init__(
        self, hub, session_name, outdir,
        time_span, fps, slot_width, left_to_right, shutdown_event: asyncio.Event, **kwargs,
    ):
        self.video_capture = None

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
        self.capture_lock = threading.Lock()
        self.video_capture_index = kwargs.get("video_capture_index", 0)
        self.stamp_options = {
            "time": kwargs.get("stamp_time", True),
            "fps": kwargs.get("stamp_fps", False),
            "ticks": kwargs.get("stamp_ticks", True),
            "tick-texts": kwargs.get("stamp_tick_texts", True),
        }

    async def start(self):
        os.makedirs(f"{self.outdir}/{self.session_name}")

        self.__init_video()

        try:
            await self.start_capture()
        finally:
            self.__stop_video()

    async def start_capture(self):
        self.time_first_start = time.time()
        i = 0

        # Start the first capture in advance
        current_capture = TimeSpanGrabber(
            self, self.time_first_start + (i * self.time_span), i
        )
        wait_tasks = [asyncio.to_thread(current_capture.run)]
        last_capture = None

        self.__write_metadata_jsons(None)

        logging.debug("Enter capture loop")
        while not asyncio.current_task().done():
            # Prepare and start the next capture
            next_capture = TimeSpanGrabber(
                self, self.time_first_start + ((i + 1) * self.time_span), i + 1
            )
            next_capture_future = asyncio.to_thread(next_capture.run)

            # Add postprocessing if this isn't the first round
            if last_capture:
                wait_tasks.append(asyncio.create_task(
                    asyncio.to_thread(self.__postprocess_capture, last_capture)
                ))

            try:
                await asyncio.gather(*wait_tasks)
            except asyncio.CancelledError:    
                try:
                    await next_capture_future
                except Exception:
                    pass  # ignore cleanup errors
                break

            if current_capture.exit_after:
                break

            # Rotate
            last_capture = current_capture
            current_capture = next_capture
            wait_tasks = [next_capture_future]
            i += 1

    def capture_frame(self):
        if self.video_capture is None or not self.video_capture.isOpened():
            raise VideoException("Video is closed")

        with self.capture_lock:
            ret, src = self.video_capture.read()
            if not ret:
                raise VideoException("Can't receive frame")

        if self.left_to_right:
            src = cv.flip(src, 1)
        return src

    def __postprocess_capture(self, last_capture):
        img = last_capture.img

        img = self.__stamp_image(img, last_capture.metadata)

        self.hub.publish(image=img, metadata=last_capture.metadata)

        basename = self.__write_image_and_metadata(img, last_capture.metadata)
        print("Image taken", basename, last_capture.metadata)

    def __stamp_image(self, img, metadata):
        height, width = img.shape[:2]
        time_start = metadata.get("time_start")
        if self.stamp_options.get("time"):
            img = cv.putText(img, time.ctime(time_start), (4, height - 20),
                cv.FONT_HERSHEY_SIMPLEX, 0.5, STAMPS_COLOR, 1, cv.LINE_AA
            )
        if self.stamp_options.get("fps"):
            img = cv.putText(img, str(metadata.get("fps")) + "FPS", (4, 20),
                cv.FONT_HERSHEY_SIMPLEX, 0.5, STAMPS_COLOR, 1, cv.LINE_AA
            )
        if self.stamp_options.get("ticks"):
            for ix in range(-1, self.time_span):
                x = round(
                    (ix + (1 - (time_start - math.floor(time_start)))) * self.fps * self.slot_width
                )
                img = cv.line(img, (x, height - 10), (x, height), STAMPS_COLOR, 1)
                if self.stamp_options.get("tick-texts"):
                    img = cv.putText(img, str((math.floor(time_start + 1 + ix) % 60)), (x + 3, height - 3),
                        cv.FONT_HERSHEY_SIMPLEX, 0.3, STAMPS_COLOR, 1, cv.LINE_AA
                    )
        return img

    def __write_metadata_jsons(self, last_index):
        # Session JSON
        filename = f'{self.outdir}/{self.session_name}/index.json'
        with open(filename, "w") as openfile:
            json.dump(self.__session_metadata(last_index), openfile)

        # Global JSON
        filename = f"{self.outdir}/index.json"
        try:
            with open(filename, "r") as openfile:
                index_data = json.load(openfile)
        except FileNotFoundError:
            index_data = {}
        index_data[self.session_name] = self.__session_metadata(last_index)
        with open(filename, "w") as openfile:
            json.dump(index_data, openfile)


    def __write_image_and_metadata(self, img, metadata):
        basename = f'{self.outdir}/{self.session_name}/img{metadata["index"]}'
        cv.imwrite(
            f"{basename}.webp", img, [cv.IMWRITE_WEBP_QUALITY, self.webp_quality]
        )
        with open(f"{basename}.json", "w") as outfile:
            json.dump(metadata, outfile, indent=4)
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
                "height": self.src_height
        }
            

    def __init_video(self):
        # Detect platform – use V4L2 with MJPEG on Linux, CAP_ANY elsewhere
        is_linux = platform.system() == "Linux"
        backend = cv.CAP_V4L2 if is_linux else cv.CAP_ANY
        self.video_capture = cv.VideoCapture(self.video_capture_index, backend)

        # Set MJPEG codec only on Linux (for higher FPS support)
        if is_linux:
            self.video_capture.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc(*'MJPG'))

        # Set resolution and desired FPS
        resolutions = {
            "qvga": (320, 240),
            "vga": (640, 480),
            "svga": (800, 600),
            "xga": (1024, 768),
            "wxga": (1280, 800),
            "hd": (1280, 720),
            "sxga": (1280, 1024),
            "uxga": (1600, 1200),
            "fullhd": (1920, 1080),
            "4k": (3840, 2160),
        }
        width, height = resolutions[self.resolution]
        self.video_capture.set(cv.CAP_PROP_FPS, self.fps)
        self.video_capture.set(cv.CAP_PROP_FRAME_WIDTH, width)
        self.video_capture.set(cv.CAP_PROP_FRAME_HEIGHT, height)

        if not self.video_capture.isOpened():
            raise VideoException("Cannot open camera")
    
        actual_width = self.video_capture.get(cv.CAP_PROP_FRAME_WIDTH)
        actual_height = self.video_capture.get(cv.CAP_PROP_FRAME_HEIGHT)
        actual_fps = self.video_capture.get(cv.CAP_PROP_FPS)
        print(f"Actual settings: {actual_width}x{actual_height} @ {actual_fps} FPS")

        # Detect frame size
        src = self.capture_frame()

        self.src_height, self.src_width = src.shape[:2]
        self.src_middle_left = self.src_width // 2

    def __stop_video(self):
        if self.video_capture:
            with self.capture_lock:
                self.video_capture.release()
            self.video_capture = None
        cv.destroyAllWindows()
