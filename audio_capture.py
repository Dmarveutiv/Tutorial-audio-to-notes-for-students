import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import queue
import os
import tempfile

CHUNK_DURATION = 30      # seconds per chunk sent to Whisper
SAMPLE_RATE = 16000      # Whisper works best at 16kHz

class AudioCapture:
    def __init__(self, chunk_callback):
        """
        chunk_callback: a function that gets called every time
        a 30-second audio chunk is ready for transcription
        """
        self.chunk_callback = chunk_callback
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.thread = None

    def get_wasapi_loopback_device(self):
        """Find the WASAPI loopback device (system audio)"""
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0 and 'loopback' in device['name'].lower():
                return i
        # Fallback: find default WASAPI loopback
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0 and device['hostapi'] != 0:
                return i
        return None  # Will use default mic if no loopback found

    def start(self):
        """Start capturing audio in a background thread"""
        self.is_recording = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        print("Audio capture started...")

    def stop(self):
        """Stop capturing audio"""
        self.is_recording = False
        if self.thread:
            self.thread.join(timeout=5)
        print("Audio capture stopped.")

    def _capture_loop(self):
        """Main loop that captures audio in 30-second chunks"""
        device_index = self.get_wasapi_loopback_device()

        if device_index is None:
            print("Warning: No WASAPI loopback found, falling back to default microphone.")

        frames_per_chunk = CHUNK_DURATION * SAMPLE_RATE
        recorded_frames = []

        def audio_callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")
            # Store a copy of the incoming audio data
            recorded_frames.append(indata.copy())

        try:
            with sd.InputStream(
                device=device_index,
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype='float32',
                callback=audio_callback,
                blocksize=1024
            ):
                while self.is_recording:
                    # Wait until we have enough frames for a full chunk
                    total_frames = sum(len(f) for f in recorded_frames)

                    if total_frames >= frames_per_chunk:
                        # Combine all recorded frames into one array
                        audio_data = np.concatenate(recorded_frames, axis=0)
                        chunk = audio_data[:frames_per_chunk]

                        # Keep any leftover frames for the next chunk
                        leftover = audio_data[frames_per_chunk:]
                        recorded_frames.clear()
                        if len(leftover) > 0:
                            recorded_frames.append(leftover)

                        # Save chunk to a temp file and trigger transcription
                        self._save_and_dispatch(chunk)

                    sd.sleep(500)  # check every 500ms

            # Handle any remaining audio when stopped
            if recorded_frames:
                audio_data = np.concatenate(recorded_frames, axis=0)
                if len(audio_data) > SAMPLE_RATE * 3:  # only if > 3 seconds
                    self._save_and_dispatch(audio_data)

        except Exception as e:
            print(f"Audio capture error: {e}")

    def _save_and_dispatch(self, audio_chunk):
        """Save audio chunk to temp file and call the callback"""
        try:
            # Create a temporary wav file
            temp_file = tempfile.NamedTemporaryFile(
                suffix='.wav',
                delete=False
            )
            temp_path = temp_file.name
            temp_file.close()

            # Write audio data to the temp file
            sf.write(temp_path, audio_chunk, SAMPLE_RATE)

            # Call the callback with the path to the temp file
            self.chunk_callback(temp_path)

        except Exception as e:
            print(f"Error saving audio chunk: {e}")