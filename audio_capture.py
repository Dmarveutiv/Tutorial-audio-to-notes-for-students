import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import queue
import os
import tempfile

chunk_duration = 30  #seconds
sample_rate = 16000  #samples per second

class AudioCapture:
    def __init__(self, chunk_callback):
        self.chunk_callback = chunk_callback
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.thread = None
    
    def get_wasapi_loopback_device(self):  # Find WASAPI loopback device on Windows
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            print(i)
            if device['max_input_channels'] > 0 and 'loopback' in device['name'].lower():
                return i
            
        for i, device in enumerate(devices): #look for any input device if loopback is not found (e.g., on non-Windows platforms)
            if device['max_input_channels'] > 0 and device['hostapi'] != 0:
                return i
        return None
    
    def start(self):    #starts capturing audio with background thread
        self.is_recording = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        print('Audio capture started...')

    def stop(self):   #stops capturing audio and waits for the thread to finish
        self.is_recording = False
        if self.thread:
            self.thread.join(timeout=5)
        print("Audio capture stopped.")
        
    def _capture_loop(self):   #captures audio in chunks and saves to temporary files
        device_index = self.get_wasapi_loopback_device()
        if device_index is None:
            print('No suitable audio input device found.')
            return 0
        frames_per_chunk = int(sample_rate * chunk_duration)  #total number of audio sample per chunk
        recorded_frames = []