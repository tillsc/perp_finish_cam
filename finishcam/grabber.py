import numpy as np
import cv2 as cv
import time
import math
import os
import json
import asyncio
import concurrent.futures
import logging

import finishcam.pubsub

class VideoException(Exception):
    "Exception raised on problems with video capture"
    pass

class TimeSpanGrabber():
    def __init__(self, grabber, time_start, index):

        self.grabber = grabber
        
        self.width = self.grabber.time_span * self.grabber.px_per_second
        self.height = self.grabber.src_height
        self.img = np.full((self.height, self.width, 3), (200, 200, 200), np.uint8)
        self.metadata = { 
            'session_name': self.grabber.session_name,
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
            src = self.grabber.capture_frame()
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

            self.grabber.hub.publish('live_image', self.img)
              
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

        self.session_name = time.strftime("%Y%m%d-%H%M%S")

        self.hub = finishcam.pubsub.Hub()

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
        
    def create_task(self):
        return asyncio.create_task(self.start())

    async def start(self):
        os.makedirs(f'{self.outdir}/{self.session_name}')

        self.__init_video()

        await self.start_capture()

        self.__stop_video()

    async def start_capture(self):
        time_first_start = time.time()
        i = 0
        current_capture = TimeSpanGrabber(self, time_first_start + (i * self.time_span), i)
        last_capture = None
        logging.debug('Enter capture loop')
        while not asyncio.current_task().done():
            capture = asyncio.to_thread(current_capture.run)
            
            # Running paralell now
            next_capture = TimeSpanGrabber(self, time_first_start + ((i + 1) * self.time_span), i + 1)

            if last_capture != None:
                img = last_capture.img

                img = self.__stamp_image(img, last_capture.metadata)

                self.last_img = img
                self.hub.publish('image', img)

                basename = self.__write_image_and_metadata(img, last_capture.metadata)
                print("Image taken", basename, last_capture.metadata)     
            
            try:
                await capture
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

        if self.flip_input:
            src = cv.flip(src, 1)
        return src

    def __stamp_image(self, img, metadata):
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

    def __write_index_json(self, metadata):
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

    def __write_image_and_metadata(self, img, metadata):
        basename = f'{self.outdir}/{metadata["session_name"]}/img{metadata["index"]}'    
        cv.imwrite(f'{basename}.webp', img, [cv.IMWRITE_WEBP_QUALITY, self.webp_quality])
        with open(f'{basename}.json', "w") as outfile:
            json.dump(metadata, outfile, indent=4)
        self.__write_index_json(metadata)
        return basename

    def __init_video(self):
        self.video_capture = cv.VideoCapture(0)
        if not self.video_capture.isOpened():
            raise VideoException("Cannot open camera")
        
        # Detect frame size
        src = self.capture_frame()

        self.src_height, self.src_width = src.shape[:2]
        self.src_middle_left = (self.src_width // 2)

    def __stop_video(self):
        if self.video_capture:
            self.video_capture.release()
        cv.destroyAllWindows()
       
    