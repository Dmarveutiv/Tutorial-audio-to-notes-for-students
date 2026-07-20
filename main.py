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


# ---------------------------------------------------------------------------
# Dark theme palette
# ---------------------------------------------------------------------------
FONT = "Segoe UI"

BG_APP       = "#0B0E14"   # main window background
BG_CARD      = "#131926"   # card background
BG_SOFT      = "#18202F"   # inner widgets (text boxes, listbox)
BORDER       = "#232D3F"   # subtle card borders
TEXT_PRIMARY = "#E9EEF7"
TEXT_MUTED   = "#8B98AB"

ACCENT       = "#7C5CFF"   # brand violet
GREEN        = "#22C55E"
GREEN_HOVER  = "#34D273"
RED          = "#EF4444"
RED_HOVER    = "#F55C5C"
BLUE         = "#3B82F6"
BLUE_HOVER   = "#5897F8"
PURPLE       = "#A855F7"
PURPLE_HOVER = "#BC71F9"
AMBER        = "#F59E0B"

BTN_DISABLED    = "#242D3C"
BTN_DISABLED_FG = "#5C6B7F"

STATUS_COLORS = {
    "gray":   TEXT_MUTED,
    "orange": AMBER,
    "green":  GREEN,
    "blue":   BLUE,
    "red":    RED,
    "violet": ACCENT,
}

STATUS_SHORT = {
    "gray":   "Idle",
    "orange": "Working…",
    "green":  "Listening",
    "blue":   "Ready",
    "red":    "Error",
    "violet": "Busy",
}


def _rounded_points(x1, y1, x2, y2, r):
    """Point list for a smoothed rounded rectangle on a Canvas."""
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]


class RoundedButton(tk.Canvas):
    """Modern rounded-corner button with hover / disabled states.

    Exposes a minimal tk.Button-compatible interface (config(state=...),
    config(text=...)) so it can drop into the existing app logic.
    """

    def __init__(self, master, text, command, bg, hover_bg,
                 fg="#FFFFFF", width=150, height=46, radius=14,
                 font=(FONT, 10, "bold")):
        super().__init__(master, width=width, height=height,
                         bg=master.cget("bg"), bd=0,
                         highlightthickness=0, cursor="arrow")
        self._command = command
        self._bg = bg
        self._hover_bg = hover_bg
        self._fg = fg
        self._enabled = True

        self._rect = self.create_polygon(
            _rounded_points(2, 2, width - 2, height - 2, radius),
            smooth=True, fill=bg, outline=""
        )
        self._label = self.create_text(width / 2, height / 2, text=text,
                                       fill=fg, font=font)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    # -- events -------------------------------------------------------------
    def _on_enter(self, _event):
        if self._enabled:
            self.itemconfigure(self._rect, fill=self._hover_bg)
            super().config(cursor="hand2")

    def _on_leave(self, _event):
        if self._enabled:
            self.itemconfigure(self._rect, fill=self._bg)
            super().config(cursor="arrow")

    def _on_click(self, _event):
        if self._enabled and self._command:
            self._command()

    # -- tk.Button-compatible bits ------------------------------------------
    def config(self, cnf=None, **kw):
        if "state" in kw:
            self._set_enabled(kw.pop("state") != tk.DISABLED)
        if "text" in kw:
            self.itemconfigure(self._label, text=kw.pop("text"))
        if kw or cnf:
            return super().config(cnf, **kw)
        return None

    configure = config

    def _set_enabled(self, enabled):
        self._enabled = enabled
        if enabled:
            self.itemconfigure(self._rect, fill=self._bg)
            self.itemconfigure(self._label, fill=self._fg)
        else:
            self.itemconfigure(self._rect, fill=BTN_DISABLED)
            self.itemconfigure(self._label, fill=BTN_DISABLED_FG)
            super().config(cursor="arrow")


class TutorialToNotesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TutorialToNotes")
        self.root.geometry("800x740")
        self.root.minsize(740, 680)
        self.root.configure(bg=BG_APP)

        self.is_session_active = False
        self.audio_capture = None
        self.transcriber = None
        self.note_generator = None
        self.pdf_exporter = PDFExporter()
        self.generated_notes = None
        self.db = DBHandler()

        self._record_seconds = 0
        self._word_count = 0
        self._status_color = TEXT_MUTED
        self._pulse_on = False

        self._build_gui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # -----------------------------------------------------------------------
    # GUI construction
    # -----------------------------------------------------------------------
    def _build_gui(self):
        # ---- header --------------------------------------------------------
        header = tk.Frame(self.root, bg=BG_APP)
        header.pack(fill="x", padx=22, pady=(18, 4))

        title_block = tk.Frame(header, bg=BG_APP)
        title_block.pack(side="left")
        tk.Label(title_block, text="🎓 TutorialToNotes",
                 font=(FONT, 20, "bold"), fg=TEXT_PRIMARY,
                 bg=BG_APP).pack(anchor="w")
        tk.Label(title_block, text="Turn any online Lecture/Tutorial into summarized, structured notes ✨",
                 font=(FONT, 10), fg=TEXT_MUTED, bg=BG_APP).pack(anchor="w")

        # status pill (right side of header)
        self.status_pill = tk.Canvas(header, width=150, height=36, bg=BG_APP,
                                     bd=0, highlightthickness=0)
        self.status_pill.pack(side="right", anchor="n", pady=8)
        self.status_pill.create_polygon(
            _rounded_points(1, 1, 149, 35, 17),
            smooth=True, fill=BG_CARD, outline=BORDER
        )
        self._pill_dot = self.status_pill.create_oval(
            14, 13, 26, 25, fill=TEXT_MUTED, outline=""
        )
        self._pill_text = self.status_pill.create_text(
            36, 18, anchor="w", text="Idle",
            fill=TEXT_PRIMARY, font=(FONT, 10, "bold")
        )

        # detailed status line under the header
        self.status_detail = tk.Label(self.root, text="Ready when you are.",
                                      font=(FONT, 9), fg=TEXT_MUTED, bg=BG_APP)
        self.status_detail.pack(pady=(0, 4))

        # ---- stats row -----------------------------------------------------
        stats = tk.Frame(self.root, bg=BG_APP)
        stats.pack(fill="x", padx=22, pady=6)

        self.duration_value, _ = self._stat_card(stats, "⏱", "Session length", "00:00")
        self.words_value, _ = self._stat_card(stats, "📝", "Words captured", "0")
        self.saved_value, _ = self._stat_card(stats, "💾", "Saved sessions", "—")
        self._refresh_saved_count()

        # ---- transcript card ------------------------------------------------
        transcript_card = tk.Frame(self.root, bg=BG_CARD,
                                   highlightbackground=BORDER,
                                   highlightthickness=1)
        transcript_card.pack(fill="both", expand=True, padx=22, pady=8)

        t_head = tk.Frame(transcript_card, bg=BG_CARD)
        t_head.pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(t_head, text="🎧 Live Transcript",
                 font=(FONT, 11, "bold"), fg=TEXT_PRIMARY,
                 bg=BG_CARD).pack(side="left")

        self.live_badge = tk.Label(t_head, text="● REC",
                                   font=(FONT, 9, "bold"),
                                   fg="#FFFFFF", bg=RED, padx=8, pady=1)
        # (packed only while recording — see _set_live)

        self.transcript_box = scrolledtext.ScrolledText(
            transcript_card, wrap=tk.WORD, font=(FONT, 10),
            bg=BG_SOFT, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, selectbackground=ACCENT,
            relief="flat", bd=0, padx=10, pady=8, height=16
        )
        self.transcript_box.pack(padx=12, pady=10, fill="both", expand=True)
        self.transcript_box.config(state=tk.DISABLED)
        try:
            self.transcript_box.vbar.config(troughcolor=BG_CARD, bg=BORDER,
                                            activebackground=ACCENT,
                                            relief="flat", bd=0)
        except Exception:
            pass

        # ---- control bar ----------------------------------------------------
        controls = tk.Frame(self.root, bg=BG_APP)
        controls.pack(fill="x", padx=22, pady=(6, 4))

        self.start_button = RoundedButton(
            controls, "▶  Start Session", self.start_session,
            GREEN, GREEN_HOVER, width=170
        )
        self.start_button.pack(side="left", padx=5, expand=True)

        self.stop_button = RoundedButton(
            controls, "■  Stop & Notes", self.stop_session,
            RED, RED_HOVER, width=160
        )
        self.stop_button.pack(side="left", padx=5, expand=True)
        self.stop_button.config(state=tk.DISABLED)

        self.save_button = RoundedButton(
            controls, "💾  Save PDF", self.save_pdf,
            BLUE, BLUE_HOVER, width=140
        )
        self.save_button.pack(side="left", padx=5, expand=True)
        self.save_button.config(state=tk.DISABLED)

        self.history_button = RoundedButton(
            controls, "📚  History", self.open_history,
            PURPLE, PURPLE_HOVER, width=130
        )
        self.history_button.pack(side="left", padx=5, expand=True)

        # ---- footer ----------------------------------------------------------
        tk.Label(
            self.root,
            text="🎙️ Listens on-device   ·   🤖 Writes your notes   ·   🍃 Keeps note history",
            font=(FONT, 9), fg=TEXT_MUTED, bg=BG_APP
        ).pack(pady=(0, 12))

    def _stat_card(self, parent, icon, caption, initial):
        card = tk.Frame(parent, bg=BG_CARD,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(side="left", fill="both", expand=True, padx=4)
        value = tk.Label(card, text=initial, font=(FONT, 15, "bold"),
                         fg=TEXT_PRIMARY, bg=BG_CARD)
        value.pack(pady=(10, 0))
        tk.Label(card, text=f"{icon}  {caption}", font=(FONT, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).pack(pady=(0, 10))
        return value, card

    # -----------------------------------------------------------------------
    # Status / stats helpers
    # -----------------------------------------------------------------------
    def _update_status(self, text, color="gray"):
        """Thread-safe status update (safe to call from worker threads)."""
        def apply():
            c = STATUS_COLORS.get(color, TEXT_MUTED)
            self._status_color = c
            self.status_pill.itemconfigure(self._pill_text,
                                           text=STATUS_SHORT.get(color, "Status"))
            self.status_pill.itemconfigure(self._pill_dot, fill=c)
            detail_color = c if color in ("orange", "blue", "red") else TEXT_MUTED
            self.status_detail.config(text=text, fg=detail_color)
        self.root.after(0, apply)

    def _refresh_saved_count(self):
        def apply():
            try:
                count = len(self.db.get_all_sessions())
                self.saved_value.config(text=str(count))
            except Exception:
                self.saved_value.config(text="—")
        self.root.after(0, apply)

    def _set_live(self, visible):
        if visible:
            self.live_badge.pack(side="left", padx=10)
        else:
            self.live_badge.pack_forget()

    def _start_timer(self):
        self._record_seconds = 0
        self.duration_value.config(text="00:00")
        self._tick()

    def _tick(self):
        if not self.is_session_active:
            return
        self._record_seconds += 1
        m, s = divmod(self._record_seconds, 60)
        h, m = divmod(m, 60)
        text = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        self.duration_value.config(text=text)
        self.root.after(1000, self._tick)

    def _start_pulse(self):
        self._pulse_on = False
        self._pulse()

    def _pulse(self):
        if not self.is_session_active:
            return
        self._pulse_on = not self._pulse_on
        fill = self._status_color if self._pulse_on else BG_CARD
        self.status_pill.itemconfigure(self._pill_dot, fill=fill)
        self.root.after(550, self._pulse)

    def _append_transcript(self, text):
        def update():
            self.transcript_box.config(state=tk.NORMAL)
            self.transcript_box.insert(tk.END, text + " ")
            self.transcript_box.see(tk.END)
            self.transcript_box.config(state=tk.DISABLED)
            self._word_count += len(text.split())
            self.words_value.config(text=str(self._word_count))
        self.root.after(0, update)

    # -----------------------------------------------------------------------
    # Session flow (logic unchanged from the original app)
    # -----------------------------------------------------------------------
    def start_session(self):
        if not GEMINI_API_KEY:
            messagebox.showerror(
                "Missing API Key",
                "Gemini_Api_Key not found.\n\nMake sure a .env file exists in this folder with:\nGemini_Api_Key=your_key_here"
            )
            return

        self.is_session_active = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.DISABLED)

        self.transcript_box.config(state=tk.NORMAL)
        self.transcript_box.delete(1.0, tk.END)
        self.transcript_box.config(state=tk.DISABLED)

        self._word_count = 0
        self.words_value.config(text="0")
        self._set_live(True)
        self._start_timer()
        self._start_pulse()

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
        self._set_live(False)
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
        self._refresh_saved_count()

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

    # -----------------------------------------------------------------------
    # History window
    # -----------------------------------------------------------------------
    def open_history(self):
        try:
            sessions = self.db.get_all_sessions()
        except Exception as exc:
            messagebox.showerror(
                "Database Error",
                f"Could not load sessions from MongoDB.\n\n{exc}\n\nIs 'docker compose up' running?"
            )
            return

        if not sessions:
            messagebox.showinfo("History", "No saved sessions yet.")
            return

        history_window = tk.Toplevel(self.root)
        history_window.title("Session History")
        history_window.geometry("840x640")
        history_window.minsize(720, 520)
        history_window.configure(bg=BG_APP)
        history_window.transient(self.root)

        # header
        header = tk.Frame(history_window, bg=BG_APP)
        header.pack(fill="x", padx=20, pady=(16, 8))
        tk.Label(header, text="📚 Session History",
                 font=(FONT, 16, "bold"), fg=TEXT_PRIMARY,
                 bg=BG_APP).pack(side="left")
        tk.Label(header, text=f"{len(sessions)} saved",
                 font=(FONT, 10), fg=TEXT_MUTED,
                 bg=BG_APP).pack(side="left", padx=10, pady=(4, 0))

        # session list card
        list_card = tk.Frame(history_window, bg=BG_CARD,
                             highlightbackground=BORDER, highlightthickness=1)
        list_card.pack(fill="x", padx=20, pady=6)

        list_frame = tk.Frame(list_card, bg=BG_CARD)
        list_frame.pack(padx=10, pady=10, fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame, troughcolor=BG_CARD, bg=BORDER,
                                 activebackground=ACCENT, relief="flat", bd=0)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        session_listbox = tk.Listbox(
            list_frame, font=(FONT, 11), height=7,
            bg=BG_SOFT, fg=TEXT_PRIMARY,
            selectbackground=ACCENT, selectforeground="#FFFFFF",
            highlightthickness=0, relief="flat", bd=0,
            activestyle="none",
            yscrollcommand=scrollbar.set, selectmode=tk.SINGLE
        )
        session_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar.config(command=session_listbox.yview)

        for session in sessions:
            session_listbox.insert(tk.END, "  " + session["title"])

        # notes preview card
        preview_card = tk.Frame(history_window, bg=BG_CARD,
                                highlightbackground=BORDER, highlightthickness=1)
        preview_card.pack(fill="both", expand=True, padx=20, pady=6)
        tk.Label(preview_card, text="📝 Notes Preview",
                 font=(FONT, 11, "bold"), fg=TEXT_PRIMARY,
                 bg=BG_CARD).pack(anchor="w", padx=12, pady=(10, 0))

        notes_box = scrolledtext.ScrolledText(
            preview_card, wrap=tk.WORD, font=(FONT, 10),
            bg=BG_SOFT, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, selectbackground=ACCENT,
            relief="flat", bd=0, padx=10, pady=8, height=14
        )
        notes_box.pack(padx=12, pady=10, fill="both", expand=True)
        notes_box.config(state=tk.DISABLED)
        try:
            notes_box.vbar.config(troughcolor=BG_CARD, bg=BORDER,
                                  activebackground=ACCENT, relief="flat", bd=0)
        except Exception:
            pass

        # buttons
        btn_frame = tk.Frame(history_window, bg=BG_APP)
        btn_frame.pack(pady=(6, 16))

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
                self._refresh_saved_count()

        session_listbox.bind("<<ListboxSelect>>", on_select)

        RoundedButton(
            btn_frame, "📄  Export PDF", export_selected,
            BLUE, BLUE_HOVER, width=170
        ).grid(row=0, column=0, padx=6)

        RoundedButton(
            btn_frame, "🗑  Delete", delete_selected,
            RED, RED_HOVER, width=140
        ).grid(row=0, column=1, padx=6)

    # -----------------------------------------------------------------------
    # Shutdown
    # -----------------------------------------------------------------------
    def _on_close(self):
        try:
            if self.audio_capture:
                self.audio_capture.stop()
            if self.transcriber:
                self.transcriber.stop()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = TutorialToNotesApp(root)
    root.mainloop()
