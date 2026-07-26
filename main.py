import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import threading
import os
from dotenv import load_dotenv
from datetime import datetime

from audio_capture import AudioCapture
from transcriber import Transcriber
from note_generator import NoteGenerator
from pdf_exporter import PDFExporter

# Load environment variables from .env (must be in the same folder as this file)
load_dotenv()
GEMINI_API_KEY = os.getenv("Gemini_Api_Key")


class TutorialToNotesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TutorialToNotes")
        self.root.geometry("700x600")

        self.is_session_active = False
        self.audio_capture = None
        self.transcriber = None
        self.note_generator = None
        self.pdf_exporter = PDFExporter()
        self.generated_notes = None

        self._build_gui()

    def _build_gui(self):
        title_label = tk.Label(self.root, text="TutorialToNotes", font=("Helvetica", 18, "bold"))
        title_label.pack(pady=10)

        self.status_label = tk.Label(self.root, text="Status: Idle", font=("Helvetica", 11), fg="gray")
        self.status_label.pack(pady=5)

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        self.start_button = tk.Button(
            button_frame, text="▶ Start", width=15, bg="#4CAF50", fg="white",
            font=("Helvetica", 11, "bold"), command=self.start_session
        )
        self.start_button.grid(row=0, column=0, padx=5)

        self.stop_button = tk.Button(
            button_frame, text="■ Stop", width=15, bg="#f44336", fg="white",
            font=("Helvetica", 11, "bold"), command=self.stop_session, state=tk.DISABLED
        )
        self.stop_button.grid(row=0, column=1, padx=5)

        self.save_button = tk.Button(
            button_frame, text="💾 Save PDF", width=15, bg="#2196F3", fg="white",
            font=("Helvetica", 11, "bold"), command=self.save_pdf, state=tk.DISABLED
        )
        self.save_button.grid(row=0, column=2, padx=5)

        transcript_label = tk.Label(self.root, text="Live Transcript:", font=("Helvetica", 11, "bold"))
        transcript_label.pack(anchor="w", padx=15, pady=(15, 0))

        self.transcript_box = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, height=20, font=("Helvetica", 10)
        )
        self.transcript_box.pack(padx=15, pady=5, fill="both", expand=True)
        self.transcript_box.config(state=tk.DISABLED)

    def _update_status(self, text, color="gray"):
        self.status_label.config(text=f"Status: {text}", fg=color)

    def _append_transcript(self, text):
        def update():
            self.transcript_box.config(state=tk.NORMAL)
            self.transcript_box.insert(tk.END, text + " ")
            self.transcript_box.see(tk.END)
            self.transcript_box.config(state=tk.DISABLED)
        self.root.after(0, update)

    # -----------------------------------------------------------------------
    # Title extraction
    # -----------------------------------------------------------------------
    def _extract_title(self, notes_markdown):
        """Extract the first # heading from Gemini's notes as the session title"""
        for line in notes_markdown.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return datetime.now().strftime("Tutorial Notes - %Y-%m-%d %H:%M")

    # -----------------------------------------------------------------------
    # Session flow
    # -----------------------------------------------------------------------
    def start_session(self):
        if not GEMINI_API_KEY:
            messagebox.showerror(
                "Missing API Key",
                "GEMINI_API_KEY not found.\n\nMake sure a .env file exists in this folder with:\nGEMINI_API_KEY=your_key_here"
            )
            return

        self.is_session_active = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.DISABLED)

        self.transcript_box.config(state=tk.NORMAL)
        self.transcript_box.delete(1.0, tk.END)
        self.transcript_box.config(state=tk.DISABLED)

        self._update_status("Loading Whisper model...", "orange")
        threading.Thread(target=self._init_and_start, daemon=True).start()

    def _init_and_start(self):
        self.transcriber = Transcriber(text_callback=self._append_transcript, model_size="base")
        self.transcriber.start()

        self.audio_capture = AudioCapture(chunk_callback=self.transcriber.queue_chunk)
        self.audio_capture.start()

        self._update_status("Listening...", "green")

    def stop_session(self):
        self.is_session_active = False
        self.stop_button.config(state=tk.DISABLED)
        self._update_status("Stopping and generating notes...", "orange")
        threading.Thread(target=self._stop_and_generate, daemon=True).start()

    def _stop_and_generate(self):
        if self.audio_capture:
            self.audio_capture.stop()
        if self.transcriber:
            self.transcriber.stop()

        full_transcript = self.transcriber.get_full_transcript() if self.transcriber else ""

        if not full_transcript.strip():
            self._update_status("No audio captured.", "red")
            self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
            return

        self._update_status("Generating structured notes with Gemini...", "orange")

        self.note_generator = NoteGenerator(api_key=GEMINI_API_KEY)
        self.generated_notes = self.note_generator.generate_notes(full_transcript)

        self._update_status("Notes ready! Click 'Save PDF'.", "blue")
        self.root.after(0, self._enable_save)

    def _enable_save(self):
        self.start_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.NORMAL)

    def save_pdf(self):
        if not self.generated_notes:
            messagebox.showwarning("No Notes", "No notes have been generated yet.")
            return

        title = self._extract_title(self.generated_notes)

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"{title}.pdf"
        )

        if file_path:
            self.pdf_exporter.export(self.generated_notes, file_path, title=title)
            self._update_status(f"Saved to {os.path.basename(file_path)}", "green")
            messagebox.showinfo("Saved", f"Notes saved successfully to:\n{file_path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = TutorialToNotesApp(root)
    root.mainloop()