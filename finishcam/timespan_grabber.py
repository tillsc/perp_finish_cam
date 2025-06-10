import numpy as np
import cv2 as cv
import time

class TimeSpanGrabber:
    """
    Captures and assembles a horizontal strip image over a fixed time span.

    This class collects narrow vertical slices from video frames at a defined frame rate 
    and stitches them into a single composite image over a fixed duration (`time_span`).
    It is designed to simulate a virtual slit camera by grabbing a central vertical section 
    from each frame and appending it horizontally to build up a full-width image.

    Attributes:
        grabber: Reference to the parent Grabber instance (provides camera access and config).
        time_start: Scheduled start time for capture (used to align timing precisely).
        index: Sequential index of the capture session (used for naming/metadata).
        img: The output image buffer to be filled over time.
        metadata: A dictionary describing the capture configuration and progress.
        done: Flag indicating the grabber has finished its run.
        exit_after: Flag used to signal whether capture should stop after this run.
    """
        
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
                try:
                    self._interrupted_sleep(time_to_wait)
                except InterruptedError:
                    self.done = True
                    return
                time_passed = time.time() - self.metadata["time_start"]

            src = self.grabber.capture_frame()
            left = round(time_passed * self.grabber.fps * self.grabber.slot_width)
            middle_left = self.grabber.src_middle_left

            self.grabber.update_ai_image(src[0:, middle_left : self.grabber.src_width], left, self.width)
           
            if self.metadata["frame_count"] == 0:
                middle_left -= left
                left = 0

            max_slot_width = self.width - left
            slot = src[
                0:,
                middle_left : min(self.grabber.src_width, middle_left + max_slot_width)
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

    def _interrupted_sleep(self, seconds, tick=0.2):
        """
        Sleeps in small intervals to allow interruption via shutdown_event.

        Instead of blocking for the full duration, this method sleeps in short chunks 
        and checks whether self.grabber.shutdown_event has been set. 
        If shutdown is requested, it raises InterruptedError immediately.
        """
        slept = 0.0
        while slept < seconds:
            if self.grabber.shutdown_event.is_set():
                raise InterruptedError("Sleep interrupted by shutdown_event")
            time_to_sleep = min(tick, seconds - slept)
            time.sleep(time_to_sleep)
            slept += time_to_sleep

    def __takeTestImage(self):
        self.img[:] = ((self.metadata["index"] * 11 % 360), 50, 255)
        self.img = cv.cvtColor(self.img, cv.COLOR_HLS2RGB)