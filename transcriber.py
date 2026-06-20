import whisper
import os
import threading
import queue


class Transcriber:
    def __init__(self, text_callback, model_size='base'):
        self.text_callback = text_callback
        self.model = whisper.load_model(model_size)
        self.chunk_queue = queue.Queue()
        self.is_running = False
        self.thread = None
        self.full_transcript = []

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        print("Transcriber started.")

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=10)
        print("Transcriber stopped.")

    def queue_chunk(self, wav_path):
        self.chunk_queue.put(wav_path)

    def _process_loop(self):
        while self.is_running or not self.chunk_queue.empty():
            try:
                wav_path = self.chunk_queue.get(timeout=1)
            except queue.Empty:
                continue

            text = self._transcribe(wav_path)

            if text:
                self.full_transcript.append(text)
                self.text_callback(text)

            try:
                os.remove(wav_path)
            except OSError as e:
                print(f"Could not delete temp file {wav_path}: {e}")

    def _transcribe(self, wav_path):
        try:
            result = self.model.transcribe(wav_path, fp16=False)
            return result['text'].strip()
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""

    def get_full_transcript(self):
        return " ".join(self.full_transcript)