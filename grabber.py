import numpy as np
import cv2 as cv
import time
import math
import os
import json
import asyncio
import concurrent.futures

class Event_ts(asyncio.Event):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

    def set(self):
        self._loop.call_soon_threadsafe(super().set)

    def clear(self):
        super().clear()
        self._loop.call_soon_threadsafe(super().clear)

class VideoException(Exception):
    "Exception raised on problems with video capture"
    pass

class TimeSpanGrabber():
    def __init__(self, grabber, session_name, time_start, index):

        self.grabber = grabber
        
        self.width = self.grabber.time_span * self.grabber.px_per_second
        self.height = self.grabber.src_height
        self.img = np.full((self.height, self.width, 3), (200, 200, 200), np.uint8)
        self.metadata = { 
            'session_name': session_name,
            'time_start': time_start,
            'index': index, 
            'frame_count': 0, 
            'fps': 0
        }

        self.done = False
        self.exit_after = False

    def run(self):
        if self.grabber.test_mode != None:
            self.__takeTestImage()
            if (self.grabber.test_mode <= self.metadata['index']):
                self.exit_after = True
            self.done = True    
            return

        while (time_passed:= (time.time() - self.metadata['time_start'])) <  self.grabber.time_span:
            src = self.grabber.captureFrame()
            left = round(time_passed * self.grabber.px_per_second)

            max_slot_width = self.width - left
            middle_left = self.grabber.src_middle_left
            if self.metadata['frame_count'] == 0:
                middle_left -= left # left should be 0... Take the left side when it isn't
                left = 0
            
            slot = src[0:, middle_left:min(self.grabber.src_width, middle_left + max_slot_width)]

            self.img[0:, left:left + slot.shape[:2][1]] = slot

            self.metadata['frame_count'] += 1  
            self.metadata['fps'] = self.metadata['frame_count'] / time_passed

            self.grabber.capture_event.set()
              
        if self.metadata['fps'] > self.grabber.px_per_second:  
            print(f"Real FPS ({self.metadata['fps']}) allows higher resolution (>= {round(self.metadata['fps'])} px/sec - current is {self.grabber.px_per_second} px/sec)")
        
        self.done = True

    def __takeTestImage(self):
        self.img[:] = ((self.metadata['index'] * 11 % 360), 50, 255)
        self.img = cv.cvtColor(self.img, cv.COLOR_HLS2RGB)

STAMPS_COLOR = (100, 255, 100)

class Grabber:

    def __init__(self, outdir, time_span, px_per_second, preview, left_to_right, **kwargs):
        self.video_capture = False

        self.current_capture = None
        self.capture_event = Event_ts()
        self.processed_event = Event_ts()

        self.outdir = outdir
        self.time_span = time_span
        self.px_per_second = px_per_second
        self.preview = preview
        self.flip_input = not left_to_right
        self.webp_quality = kwargs.get('webp_quality', 90)   
        self.test_mode = kwargs.get('test_mode', 0)     
        self.stamp_options = { 
            'time':  kwargs.get('stamp_time', True),
            'fps':  kwargs.get('stamp_fps', False),
            'ticks': kwargs.get('stamp_ticks', True),
            'tick-texts': kwargs.get('stamp_tick_texts', True) 
        }
        
    async def start_preview(self):
        while True:
            await self.capture_event.wait()
            self.capture_event.clear()
            cv.imshow('Live', self.current_capture.img)
            if self.processed_event.is_set():
                self.processed_event.clear()
                cv.imshow('Last Image', self.last_img)
            if cv.waitKey(1) == ord('q'):
                break 
        print("END prev LOOP")

    async def start(self, session_name):
        os.makedirs(f'{self.outdir}/{session_name}')

        self.__initVideo()

        tasks = [asyncio.get_running_loop().create_task(self.do_capture(session_name))]
        if self.preview:
            tasks.append(asyncio.get_running_loop().create_task(self.start_preview()))
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED) 
        
        for task in tasks:
            task.cancel()

        self.__stopVideo()

    async def do_capture(self, session_name):
        time_first_start = time.time()
        i = 0
        self.current_capture = TimeSpanGrabber(self, session_name, time_first_start + (i * self.time_span), i)
        last_capture = None
        while True:
            capture = asyncio.to_thread(self.current_capture.run)
            
            # Running paralell now
            next_capture = TimeSpanGrabber(self, session_name, time_first_start + ((i + 1) * self.time_span), i + 1)

            if last_capture != None:
                img = last_capture.img

                img = self.__stampImage(img, last_capture.metadata)

                self.last_img = img
                self.processed_event.set()

                basename = self.__writeImageAndMetadata(img, last_capture.metadata)
                print("Image taken", basename, last_capture.metadata)     
            
            await capture

            if self.current_capture.exit_after:
                break
            last_capture = self.current_capture
            self.current_capture = next_capture
            i += 1

    def captureFrame(self):
        if not self.video_capture:
            raise VideoException("Video is closed")

        ret, src = self.video_capture.read()
        if not ret:
            raise VideoException("Can't receive frame")    

        if self.flip_input:
            src = cv.flip(src, 1)
        return src

    def __stampImage(self, img, metadata):
        height, width = img.shape[:2]
        time_start = metadata.get('time_start')
        if self.stamp_options.get('time'):
            img = cv.putText(img, time.ctime(time_start), (4, height - 20), cv.FONT_HERSHEY_SIMPLEX, 0.5, STAMPS_COLOR, 1, cv.LINE_AA)
        if self.stamp_options.get('fps'):
            img = cv.putText(img, str(metadata.get('fps')) + "FPS", (4, 20), cv.FONT_HERSHEY_SIMPLEX, 0.5, STAMPS_COLOR, 1, cv.LINE_AA)
        if self.stamp_options.get('ticks'):
            for ix in range(-1, self.time_span):
                x = ix * (width // self.time_span) + 1 
                x = round((ix + (time_start - math.floor(time_start))) * self.px_per_second) 
                img = cv.line(img, (x, height - 10), (x, height), STAMPS_COLOR, 1)
                if (self.stamp_options.get('tick-texts')):
                    img = cv.putText(img, str((math.floor(time_start + ix) % 60)), (x + 3, height - 3), cv.FONT_HERSHEY_SIMPLEX, 0.3, STAMPS_COLOR, 1, cv.LINE_AA)    
        return img                             

    def __writeIndexJson(self, metadata):
        filename = f'{self.outdir}/index.json'
        try:
            with open(filename, 'r') as openfile:
                index_data = json.load(openfile)
        except FileNotFoundError:
            index_data = {}
        data = index_data.get(metadata['session_name'],{  'time_start': metadata['time_start'] })
        data['last_index'] = metadata['index']
        index_data[metadata['session_name']] = data
        with open(filename, 'w') as openfile:
            json.dump(index_data, openfile)

    def __writeImageAndMetadata(self, img, metadata):
        basename = f'{self.outdir}/{metadata["session_name"]}/img{metadata["index"]}'    
        cv.imwrite(f'{basename}.webp', img, [cv.IMWRITE_WEBP_QUALITY, self.webp_quality])
        with open(f'{basename}.json', "w") as outfile:
            json.dump(metadata, outfile, indent=4)
        self.__writeIndexJson(metadata)
        return basename

    def __initVideo(self):
        self.video_capture = cv.VideoCapture(0)
        if not self.video_capture.isOpened():
            raise VideoException("Cannot open camera")
        
        # Detect frame size
        src = self.captureFrame()

        self.src_height, self.src_width = src.shape[:2]
        self.src_middle_left = (self.src_width // 2)

    def __stopVideo(self):
        if self.video_capture:
            self.video_capture.release()
        cv.destroyAllWindows()
       
    