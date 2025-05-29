import numpy as np
import cv2 as cv
import time
import math
import os
import json
import asyncio
import concurrent.futures
import logging
import platform

def create_task(
    hub, session_name, outdir,
    time_span, fps, slot_width, left_to_right, **kwargs
    ):
    gr = Grabber(
        hub, session_name, outdir,
        time_span, fps, slot_width, left_to_right, **kwargs,
    )
    return asyncio.create_task(gr.start())


class VideoException(Exception):
    "Exception raised on problems with video capture"
    pass


class TimeSpanGrabber:
    def __init__(self, grabber, time_start, index):
        self.grabber = grabber

        self.width = self.grabber.time_span * self.grabber.fps * self.grabber.slot_width
        self.height = self.grabber.src_height
        self.img = np.full((self.height, self.width, 3), (200, 200, 200), np.uint8)
        self.metadata = {
            "session_name": self.grabber.session_name,
            "time_start": time_start,
            "time_span": self.grabber.time_span,
            "index": index,
            "height": self.height,
            "frame_count": 0,
            "fps": 0,
        }

        self.done = False
        self.exit_after = False

    def run(self):
        if self.grabber.test_mode != None:
            self.__takeTestImage()
            if self.grabber.test_mode <= self.metadata["index"]:
                self.exit_after = True
            self.done = True
            return

        while (time_passed := (time.time() - self.metadata["time_start"])) < self.grabber.time_span:
            time_expected_next_grab = self.metadata["frame_count"] / self.grabber.fps
            time_to_wait = time_expected_next_grab - time_passed
            if time_to_wait > 0:
                time.sleep(time_to_wait)
                time_passed = time.time() - self.metadata["time_start"]

            src = self.grabber.capture_frame()
            left = round(time_passed * self.grabber.fps * self.grabber.slot_width)

            max_slot_width = self.width - left
            middle_left = self.grabber.src_middle_left
            if self.metadata["frame_count"] == 0:
                middle_left -= left
                left = 0

            slot = src[
                0:,
                middle_left : min(self.grabber.src_width, middle_left + max_slot_width),
            ]

            self.img[0:, left : left + slot.shape[:2][1]] = slot

            self.metadata["frame_count"] += 1
            self.metadata["fps"] = self.metadata["frame_count"] / time_passed

            self.grabber.hub.publish_threadsafe(
                live_image=self.img, live_raw_image=src, live_metadata=self.metadata
            )

        if self.metadata["fps"] > self.grabber.fps * 1.10:
            print(f"Real FPS ({self.metadata['fps']} f/s) allows higher requested FPS (current is {self.grabber.fps} f/s)")
        if self.metadata["fps"] < self.grabber.fps * 0.90:
            print(f"Real FPS ({self.metadata['fps']} f/s) is much lower then requested FPS ({self.grabber.fps} f/s)")

        self.done = True

    def __takeTestImage(self):
        self.img[:] = ((self.metadata["index"] * 11 % 360), 50, 255)
        self.img = cv.cvtColor(self.img, cv.COLOR_HLS2RGB)


STAMPS_COLOR = (100, 255, 100)


class Grabber:
    def __init__(
        self, hub, session_name, outdir,
        time_span, fps, slot_width, left_to_right, **kwargs,
    ):
        self.video_capture = False

        self.hub = hub
        self.session_name = session_name
        self.outdir = outdir
        self.time_span = time_span
        self.fps = fps
        self.slot_width = slot_width
        self.left_to_right = left_to_right
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
        os.makedirs(f"{self.outdir}/{self.session_name}")

        self.__init_video()

        await self.start_capture()

        self.__stop_video()

    async def start_capture(self):
        self.time_first_start = time.time()
        i = 0
        current_capture = TimeSpanGrabber(
            self, self.time_first_start + (i * self.time_span), i
        )
        last_capture = None
        self.__write_metadata_jsons(None)
        
        logging.debug("Enter capture loop")
        while not asyncio.current_task().done():
            capture_future = asyncio.to_thread(current_capture.run)

            # Running paralell now
            next_capture = TimeSpanGrabber(
                self, self.time_first_start + ((i + 1) * self.time_span), i + 1
            )

            if last_capture != None:
                await asyncio.to_thread(self.__postprocess_capture, last_capture)

            try:
                await capture_future
            except asyncio.CancelledError:
                break

            if current_capture.exit_after:
                break
            last_capture = current_capture
            current_capture = next_capture
            i += 1

    def capture_frame(self):
        if not self.video_capture:
            raise VideoException("Video is closed")

        ret, src = self.video_capture.read()
        if not ret:
            raise VideoException("Can't receive frame")

        if not self.left_to_right:
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
            self.video_capture.release()
        cv.destroyAllWindows()
