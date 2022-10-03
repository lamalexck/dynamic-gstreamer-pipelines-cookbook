import time
import datetime
import logging

log = logging.getLogger("tracking")

class ROI_RecordTracking:
    def __init__(self, start_cb, stop_cb, hysteresis=1):
        self.start_callback = start_cb
        self.stop_callback = stop_cb
        self.recording = False
        self.hysteresis = hysteresis
        self.last_stop_time = 0
        
    def observed(self):
        now = time.time()
        if not self.recording and now - self.last_stop_time > self.hysteresis:
            self.recording = True
            self.start_callback()
            self.last_start_time = now
        
    def not_observed(self):
        now = time.time()
        if self.recording and now - self.last_start_time > self.hysteresis:
            self.recording = False
            self.stop_callback()
            self.last_stop_time = now
