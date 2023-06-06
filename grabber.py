import numpy as np
import cv2 as cv
import time
import math
import os

class VideoException(Exception):
    "Exception raised on problems with video capture"
    pass

class Grabber:

    def __init__(self, outdir, time_span, px_per_second, preview, left_to_right, **kwargs):
        self.video_capture = False

        self.outdir = outdir
        self.time_span = time_span
        self.px_per_second = px_per_second
        self.preview = preview
        self.flip_input = not left_to_right
        self.webp_quality = kwargs.get('webp_quality', 90)        
        self.stamp_options = { 
            'time':  kwargs.get('stamp_time', True),
            'fps':  kwargs.get('stamp_fps', False)
        }

    def start(self, session_name):
        os.makedirs(f'{self.outdir}/{session_name}')

        self.__initVideo()
        
        time_first_start = time.time()
        i = 0
        while True:
            img, metadata = self.__captureOneTimeSpan(time_first_start + (i * self.time_span))
            if self.stamp_options.get('time'):
                img = cv.putText(img, time.ctime(metadata.get('time_start')), (4, self.src_height - 20), cv.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1, cv.LINE_AA)
            if self.stamp_options.get('fps'):
                img = cv.putText(img, str(metadata.get('fps')) + "FPS", (4, 20), cv.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1, cv.LINE_AA)
            if self.preview:
                cv.imshow('Last Image', img)
            filename = f'{self.outdir}/{session_name}/img{i}.webp'    
            cv.imwrite(filename, img, [cv.IMWRITE_WEBP_QUALITY, self.webp_quality])
            print("Image taken", filename, metadata) 
            i += 1

    def __captureOneTimeSpan(self, time_start):
        dest_width = self.time_span * self.px_per_second

        dest = np.zeros((self.src_height, dest_width, 3), np.uint8)
        #dest[:,:] = (200, 200, 200)

        i = 0
        while (time_now:= time.time()) < time_start + self.time_span:
            src = self.__captureFrame()
            dest_left = round((time_now - time_start) * self.px_per_second)

            max_slot_width = dest_width - dest_left
            middle_left = self.src_middle_left
            if i == 0:
                middle_left -= dest_left # dest_left should be 0... Take the left side when it isn't
                dest_left = 0
            
            slot = src[0:, middle_left:min(self.src_width, middle_left + max_slot_width)]

            dest[0:, dest_left:dest_left + slot.shape[:2][1]] = slot
        
            if self.preview:
                cv.imshow('Live', dest)
                if cv.waitKey(1) == ord('q'):
                    exit(0)

            i += 1  
            
        fps =  i / self.time_span  
        if fps > self.px_per_second:  
            print(f"Real FPS ({fps}) allows higher resolution (>= {round(fps)} px/sec - current is {self.px_per_second} px/sec)")
        return dest, {
            'time_start': time_start, 
            'frame_count': i, 'fps': fps
            }

    def __initVideo(self):
        self.video_capture = cv.VideoCapture(0)
        if not self.video_capture.isOpened():
            raise VideoException("Cannot open camera")
        
        # Detect frame size
        src = self.__captureFrame()

        self.src_height, self.src_width = src.shape[:2]
        self.src_middle_left = (self.src_width // 2)

    def __stopVideo(self):
        if self.video_capture:
            self.video_capture.release()
        cv.destroyAllWindows()
    

    def __captureFrame(self):
        if not self.video_capture:
            raise VideoException("Video is closed")

        ret, src = self.video_capture.read()
        if not ret:
            raise VideoException("Can't receive frame")    

        if self.flip_input:
            src = cv.flip(src, 1)
        return src


        
    