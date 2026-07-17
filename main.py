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
from db_handler import DBHandler

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
        self.db = DBHandler()

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

        self.history_button = tk.Button(
            button_frame, text="📋 History", width=15, bg="#9C27B0", fg="white",
            font=("Helvetica", 11, "bold"), command=self.open_history
        )
        self.history_button.grid(row=0, column=3, padx=5)

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

        # Auto-save session to MongoDB
        title = datetime.now().strftime("Tutorial Notes - %Y-%m-%d %H:%M")
        self.db.save_session(
            title=title,
            transcript=full_transcript,
            notes_markdown=self.generated_notes
        )

        self._update_status("Notes ready! Click 'Save PDF'.", "blue")
        self.root.after(0, self._enable_save)

    def _enable_save(self):
        self.start_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.NORMAL)

    def save_pdf(self):
        if not self.generated_notes:
            messagebox.showwarning("No Notes", "No notes have been generated yet.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="tutorial_notes.pdf"
        )

        if file_path:
            self.pdf_exporter.export(self.generated_notes, file_path, title="Tutorial Notes")
            self._update_status(f"Saved to {os.path.basename(file_path)}", "green")
            messagebox.showinfo("Saved", f"Notes saved successfully to:\n{file_path}")

    def open_history(self):
        sessions = self.db.get_all_sessions()

        if not sessions:
            messagebox.showinfo("History", "No saved sessions yet.")
            return

        # Create history window
        history_window = tk.Toplevel(self.root)
        history_window.title("Session History")
        history_window.geometry("800x600")

        # Top label
        tk.Label(
            history_window, text="Saved Sessions",
            font=("Helvetica", 14, "bold")
        ).pack(pady=10)

        # Frame to hold listbox + scrollbar
        list_frame = tk.Frame(history_window)
        list_frame.pack(padx=15, fill="both", expand=False)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        session_listbox = tk.Listbox(
            list_frame, font=("Helvetica", 11),
            height=8, yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE
        )
        session_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar.config(command=session_listbox.yview)

        # Populate listbox
        for session in sessions:
            session_listbox.insert(tk.END, session["title"])

        # Notes preview label
        tk.Label(
            history_window, text="Notes Preview:",
            font=("Helvetica", 11, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 0))

        # Notes preview box
        notes_box = scrolledtext.ScrolledText(
            history_window, wrap=tk.WORD,
            height=15, font=("Helvetica", 10)
        )
        notes_box.pack(padx=15, pady=5, fill="both", expand=True)
        notes_box.config(state=tk.DISABLED)

        # Buttons frame
        btn_frame = tk.Frame(history_window)
        btn_frame.pack(pady=10)

        def on_select(event):
            """Load selected session notes into preview box"""
            selection = session_listbox.curselection()
            if not selection:
                return
            selected_session = sessions[selection[0]]
            notes_box.config(state=tk.NORMAL)
            notes_box.delete(1.0, tk.END)
            notes_box.insert(tk.END, selected_session["notes_markdown"])
            notes_box.config(state=tk.DISABLED)

        def export_selected():
            """Export selected session notes to PDF"""
            selection = session_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a session first.")
                return

            selected_session = sessions[selection[0]]

            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=f"{selected_session['title']}.pdf"
            )

            if file_path:
                self.pdf_exporter.export(
                    selected_session["notes_markdown"],
                    file_path,
                    title=selected_session["title"]
                )
                messagebox.showinfo("Saved", f"PDF saved to:\n{file_path}")

        def delete_selected():
            """Delete selected session from MongoDB"""
            selection = session_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a session first.")
                return

            confirm = messagebox.askyesno(
                "Delete Session",
                "Are you sure you want to delete this session?"
            )
            if confirm:
                selected_session = sessions[selection[0]]
                self.db.delete_session(str(selected_session["_id"]))
                sessions.pop(selection[0])
                session_listbox.delete(selection[0])
                notes_box.config(state=tk.NORMAL)
                notes_box.delete(1.0, tk.END)
                notes_box.config(state=tk.DISABLED)

        session_listbox.bind("<<ListboxSelect>>", on_select)

        tk.Button(
            btn_frame, text="📄 Export PDF", width=15,
            bg="#2196F3", fg="white",
            font=("Helvetica", 11, "bold"),
            command=export_selected
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            btn_frame, text="🗑 Delete", width=15,
            bg="#f44336", fg="white",
            font=("Helvetica", 11, "bold"),
            command=delete_selected
        ).grid(row=0, column=1, padx=5)


if __name__ == "__main__":
    root = tk.Tk()
    app = TutorialToNotesApp(root)
    root.mainloop()