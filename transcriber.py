import whisper
import os
import threading
import queue

class Transcriber:
    def __init__(self, text_callback, model_size='base'):
        """
        text_callback: function called every time a chunk is transcribed,
                        receives the transcribed text as a string
        model_size: 'tiny', 'base', 'small', 'medium', or 'large'
        """
        self.text_callback = text_callback
        self.model = whisper.load_model(model_size)
        self.chunk_queue = queue.Queue()
        self.is_running = False
        self.thread = None
        self.full_transcript = []

    def start(self):
        """Start the background thread that processes queued chunks"""
        self.is_running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        print("Transcriber started...")

    def stop(self):
        """Stop processing"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=10)
        print("Transcriber stopped.")

    def queue_chunk(self, wav_path):
        """Called by audio_capture.py whenever a new chunk is ready"""
        self.chunk_queue.put(wav_path)

    def _process_loop(self):
        """Continuously pulls chunks off the queue and transcribes them"""
        while self.is_running or not self.chunk_queue.empty():
            try:
                wav_path = self.chunk_queue.get(timeout=1)
            except queue.Empty:
                continue

            text = self._transcribe(wav_path)

            if text:
                self.full_transcript.append(text)
                self.text_callback(text)

            # Clean up the temp wav file now that we're done with it
            try:
                os.remove(wav_path)
            except OSError:
                pass

    def _transcribe(self, wav_path):
        """Run Whisper on a single wav file"""
        try:
            result = self.model.transcribe(wav_path, fp16=False)
            return result['text'].strip()
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""

    def get_full_transcript(self):
        """Returns the entire transcript collected so far as one string"""
        return " ".join(self.full_transcript)