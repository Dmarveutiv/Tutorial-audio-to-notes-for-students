import pyaudiowpatch as pyaudio
import soundfile as sf
import numpy as np
import threading
import tempfile
from scipy.signal import resample

CHUNK_DURATION = 30
TARGET_SAMPLE_RATE = 16000
FRAMES_PER_BUFFER = 1024


class AudioCapture:
    def __init__(self, chunk_callback):
        self.chunk_callback = chunk_callback
        self.is_recording = False
        self.thread = None
        self.native_sample_rate = None
        self.channels = None

    def _get_loopback_device(self, p):
        """Find the default WASAPI loopback device (system output capture)"""
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

        if not default_speakers.get("isLoopbackDevice", False):
            for loopback in p.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    return loopback
            raise RuntimeError("Could not find loopback device matching default speakers.")

        return default_speakers

    def start(self):
        self.is_recording = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        print("Audio capture started.")

    def stop(self):
        self.is_recording = False
        if self.thread:
            self.thread.join(timeout=5)
        print("Audio capture stopped.")

    def _capture_loop(self):
        p = pyaudio.PyAudio()

        try:
            device = self._get_loopback_device(p)
            self.native_sample_rate = int(device["defaultSampleRate"])
            self.channels = device["maxInputChannels"]

            print(f"Listening via: {device['name']}")

            frames_per_chunk = CHUNK_DURATION * self.native_sample_rate
            recorded_frames = []
            frames_collected = 0

            stream = p.open(
                format=pyaudio.paFloat32,
                channels=self.channels,
                rate=self.native_sample_rate,
                input=True,
                input_device_index=device["index"],
                frames_per_buffer=FRAMES_PER_BUFFER
            )

            while self.is_recording:
                data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                audio_block = np.frombuffer(data, dtype=np.float32)

                if self.channels > 1:
                    audio_block = audio_block.reshape(-1, self.channels)
                    audio_block = audio_block.mean(axis=1)

                recorded_frames.append(audio_block)
                frames_collected += len(audio_block)

                if frames_collected >= frames_per_chunk:
                    full_audio = np.concatenate(recorded_frames)
                    chunk = full_audio[:frames_per_chunk]
                    leftover = full_audio[frames_per_chunk:]

                    recorded_frames = [leftover] if len(leftover) > 0 else []
                    frames_collected = len(leftover)

                    self._save_and_dispatch(chunk)

            if recorded_frames:
                full_audio = np.concatenate(recorded_frames)
                if len(full_audio) > self.native_sample_rate * 3:
                    self._save_and_dispatch(full_audio)

            stream.stop_stream()
            stream.close()

        except Exception as e:
            print(f"Audio capture error: {e}")
        finally:
            p.terminate()

    def _save_and_dispatch(self, audio_chunk):
        try:
            if self.native_sample_rate != TARGET_SAMPLE_RATE:
                num_samples = int(len(audio_chunk) * TARGET_SAMPLE_RATE / self.native_sample_rate)
                audio_chunk = resample(audio_chunk, num_samples)
                audio_chunk = audio_chunk.astype(np.float32)

            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_path = temp_file.name
            temp_file.close()

            sf.write(temp_path, audio_chunk, TARGET_SAMPLE_RATE)
            self.chunk_callback(temp_path)

        except Exception as e:
            print(f"Error saving audio chunk: {e}")