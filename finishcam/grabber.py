import cv2 as cv
import json
import numpy as np
import time
import os
import asyncio
import threading
import logging
import platform


def create_task(hub, session_name, outdir, time_span, fps, slot_width, left_to_right, shutdown_event, **kwargs):
    grabber = Grabber(hub, session_name, outdir, time_span, fps, slot_width, left_to_right, shutdown_event, **kwargs)
    return asyncio.create_task(grabber.start())


class VideoException(Exception):
    """Exception raised when video capture fails."""
    pass


class AbstractScanImage:
    """
    Base for objects that accumulate vertical frame strips into an image over time.

    Subclasses implement add_frame() and return self when complete, so the Grabber
    can publish the result and replace the instance. Both subclasses share height,
    px_per_second, and per-frame fps tracking.
    """

    def __init__(self, session_meta):
        self.session_meta = session_meta
        self.frame_count = 0
        self.fps = 0.0

    @property
    def height(self):
        return self.session_meta["height"]

    @property
    def px_per_second(self):
        return self.session_meta["px_per_second"]

    @property
    def time_span(self):
        return self.session_meta["time_span"]

    @property
    def slot_width(self):
        return self.session_meta["slot_width"]

    @property
    def scan_width(self):
        return self.time_span * self.px_per_second

    @property
    def session_start(self):
        return self.session_meta["time_start"]

    def _track_fps(self, left):
        self.frame_count += 1
        if left > 0:
            self.fps = self.frame_count / (left / self.px_per_second)

    def add_frame(self, strip: np.ndarray, left: int) -> 'AbstractScanImage | None':
        """Returns self when complete, None while still accumulating."""
        raise NotImplementedError



class ScanImage(AbstractScanImage):
    """Accumulates a time-bounded slit-camera image from per-frame strips."""

    def __init__(self, session_meta, index, first_frame, strip_left, left):
        super().__init__(session_meta)
        self.index = index

        self.image = np.full((self.height, self.scan_width, 3), (200, 200, 200), np.uint8)
        # back-fill: if the slot started mid-frame, read left of strip_left to fill from position 0
        read_strip = first_frame[:, max(0, strip_left - left):]
        self.add_frame(read_strip, max(0, left - strip_left))

    @property
    def time_start(self):
        return self.session_start + self.index * self.time_span

    @property
    def metadata(self):
        return {**self.session_meta, "time_start": self.time_start, "index": self.index, "frame_count": self.frame_count, "fps": self.fps}

    def add_frame(self, strip, left):
        if left >= self.scan_width:
            return self  # past scan boundary, signal completion

        width = min(strip.shape[1], self.scan_width - left)
        self.image[:, left:left + width] = strip[:, :width]

        self._track_fps(left)
        return None



class AiScanImage(AbstractScanImage):
    """
    Accumulates vertical strips into a rolling square AI input image.

    Operates continuously across ScanImage boundaries. add_frame() returns
    self once a full square is ready; the Grabber reads .square and
    .ai_time_start, then creates a new AiScanImage seeded with the overlap.
    """

    def __init__(self, session_meta, ai_overlap, previous=None, initial_left=0):
        super().__init__(session_meta)
        self._overlap = round(self.height * ai_overlap)  # x-axis pixels; height == square side length
        self.image = np.zeros((self.height, self.height * 3, 3), dtype=np.uint8)
        self.square = None
        self.ai_time_start = None

        if previous is not None:
            # seed with overlap portion from the end of the previous completed square
            self.image[:, :self._overlap] = previous.image[:, self.height - self._overlap:self.height]
            self._cursor = self._overlap
            self._last_left = previous._last_left
        else:
            self._cursor = 0
            self._last_left = initial_left

    def add_frame(self, strip, left):
        self._cursor += (left - self._last_left) % self.scan_width
        self._last_left = left

        end = min(self._cursor + strip.shape[1], self.image.shape[1])
        self.image[:, self._cursor:end] = strip[:, :end - self._cursor]

        self._track_fps(left)

        if self._cursor >= self.height:
            self.square = self.image[:, :self.height].copy()
            self.ai_time_start = time.time() - self._cursor / self.px_per_second
            return self  # signal completion

        return None


class Grabber:
    """
    Controls the full image capture loop.

    Runs a single dedicated camera thread that reads frames continuously,
    feeds them to a ScanImage and an AiScanImage, and publishes results to the hub.
    Postprocessing (stamping, encoding, saving) is handled by a separate subscriber.
    """

    def __init__(self, hub, session_name, outdir, time_span, fps, slot_width, left_to_right, shutdown_event: asyncio.Event, **kwargs):
        self.video_capture = None
        self.video_capture_lock = threading.Lock()  # needed because __stop_video runs outside the camera thread

        self.hub = hub
        self.session_name = session_name
        self.outdir = outdir
        self.time_span = time_span
        self.fps = fps
        self.slot_width = slot_width
        self.left_to_right = left_to_right
        self.upside_down = kwargs.get("upside_down", False)
        self.shutdown_event = shutdown_event

        self.ai_overlap = kwargs.get("ai_overlap", 25) / 100
        self.resolution = kwargs.get("resolution", "hd")
        self.video_capture_index = kwargs.get("video_capture_index", 0)

    async def start(self):
        os.makedirs(f"{self.outdir}/{self.session_name}", exist_ok=True)
        self.__init_video()
        self.time_first_start = time.time()
        self.session_meta = {
            "session_name": self.session_name,
            "time_start": self.time_first_start,
            "time_span": self.time_span,
            "left_to_right": self.left_to_right,
            "upside_down": self.upside_down,
            "px_per_second": self.fps * self.slot_width,
            "slot_width": self.slot_width,
            "last_index": None,
            "height": self.src_height,
        }
        self.hub.publish(session_started=self.session_meta)
        logging.debug("Enter capture loop")

        try:
            await asyncio.to_thread(self._camera_loop)
        finally:
            self.__stop_video()

    def _camera_loop(self):
        """Single camera thread: feeds each frame into ScanImage and AiScanImage."""
        i = 0
        scan = None
        ai_scan = None

        consecutive_failures = 0
        while not self.shutdown_event.is_set():
            try:
                src = self.capture_frame()
                consecutive_failures = 0
            except VideoException as e:
                if self.video_capture is None or not self.video_capture.isOpened():
                    break  # camera released by shutdown, exit cleanly
                consecutive_failures += 1
                if consecutive_failures >= 5:
                    logging.error("Camera unrecoverable after %d consecutive failures: %s", consecutive_failures, e)
                    break
                logging.warning("Frame dropped (%d/5): %s", consecutive_failures, e)
                continue

            t = time.time()
            strip = src[:, self.strip_left:self.src_width]
            left = round((t - (scan.time_start if scan else self.time_first_start)) * self.fps * self.slot_width)

            completed = scan and scan.add_frame(strip, left)
            if completed:
                self.hub.publish_threadsafe(completed_scan=completed)
                i += 1
            if not scan or completed:
                new_left = left % (self.time_span * self.fps * self.slot_width) if completed else left
                scan = ScanImage(self.session_meta, i, src, self.strip_left, new_left)

            self.hub.publish_threadsafe(current_scan=scan, live_raw_image=src)

            if self.hub.data.get('ai_available') and self.hub.data.get('ai_enabled'):
                if not ai_scan:
                    ai_scan = AiScanImage(self.session_meta, self.ai_overlap, initial_left=left)
                if ai_scan.add_frame(strip, left):
                    self.hub.publish_threadsafe(ai_input_image=ai_scan.square, ai_input_image_time_start=ai_scan.ai_time_start)
                    ai_scan = AiScanImage(self.session_meta, self.ai_overlap, previous=ai_scan)
                    ai_scan.add_frame(strip, left)  # seed position _overlap with the triggering frame
                self.hub.publish_threadsafe(current_ai_scan=ai_scan)
            else:
                ai_scan = None

    def capture_frame(self):
        if self.video_capture is None or not self.video_capture.isOpened():
            raise VideoException("Video is closed")

        with self.video_capture_lock:  # ensure .read() is not interleaved with release()
            ret, src = self.video_capture.read()
            if not ret:
                raise VideoException("Can't receive frame")

        h_flip = self.left_to_right ^ self.upside_down
        v_flip = self.upside_down
        if h_flip and v_flip:
            return cv.flip(src, -1)
        elif h_flip:
            return cv.flip(src, 1)
        elif v_flip:
            return cv.flip(src, 0)
        return src

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
        self.strip_left = self.src_width // 2

    def __stop_video(self):
        # release camera safely even if the camera thread is mid-read
        if self.video_capture:
            with self.video_capture_lock:
                self.video_capture.release()
            self.video_capture = None
        cv.destroyAllWindows()
