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

load_dotenv()
GEMINI_API_KEY = os.getenv("Gemini_Api_Key")

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
FONT_FAMILY   = "Segoe UI"
FONT_TITLE    = (FONT_FAMILY, 18, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 9)
FONT_HEADING  = (FONT_FAMILY, 11, "bold")
FONT_BODY     = (FONT_FAMILY, 10)
FONT_SMALL    = (FONT_FAMILY, 9)
FONT_BTN      = (FONT_FAMILY, 10, "bold")
FONT_STAT     = (FONT_FAMILY, 15, "bold")
FONT_PILL     = (FONT_FAMILY, 10, "bold")
FONT_BADGE    = (FONT_FAMILY, 9,  "bold")

# ---------------------------------------------------------------------------
# Themes
# ---------------------------------------------------------------------------
THEMES = {
    "dracula": {
        "name":           "dracula",
        "bg_app":         "#282A36",
        "bg_card":        "#1E2029",
        "bg_input":       "#21222C",
        "border":         "#44475A",
        "text_primary":   "#F8F8F2",
        "text_muted":     "#6272A4",
        "text_heading":   "#BD93F9",
        "accent":         "#BD93F9",
        "green":          "#50FA7B",
        "green_hover":    "#69FF90",
        "red":            "#FF5555",
        "red_hover":      "#FF7070",
        "blue":           "#8BE9FD",
        "blue_hover":     "#A5EFFE",
        "purple":         "#FF79C6",
        "purple_hover":   "#FF9DD5",
        "amber":          "#FFB86C",
        "btn_disabled":   "#3A3C4E",
        "btn_dis_fg":     "#6272A4",
        "scrollbar":      "#44475A",
        "select_bg":      "#44475A",
        "pill_bg":        "#1E2029",
        "badge_bg":       "#FF5555",
        "toggle_label":   "☀  Light",
    },
    "light": {
        "name":           "light",
        "bg_app":         "#F5F6FA",
        "bg_card":        "#FFFFFF",
        "bg_input":       "#F0F1F5",
        "border":         "#D1D5DB",
        "text_primary":   "#111827",
        "text_muted":     "#6B7280",
        "text_heading":   "#1D4ED8",
        "accent":         "#4F46E5",
        "green":          "#16A34A",
        "green_hover":    "#15803D",
        "red":            "#DC2626",
        "red_hover":      "#B91C1C",
        "blue":           "#2563EB",
        "blue_hover":     "#1D4ED8",
        "purple":         "#7C3AED",
        "purple_hover":   "#6D28D9",
        "amber":          "#D97706",
        "btn_disabled":   "#E5E7EB",
        "btn_dis_fg":     "#9CA3AF",
        "scrollbar":      "#D1D5DB",
        "select_bg":      "#C7D2FE",
        "pill_bg":        "#FFFFFF",
        "badge_bg":       "#DC2626",
        "toggle_label":   "🌙  Dark",
    },
}

# Active theme — mutable dict updated on toggle
T = dict(THEMES["dracula"])


def _rounded_points(x1, y1, x2, y2, r):
    return [
        x1+r, y1,  x2-r, y1,  x2, y1,  x2, y1+r,
        x2, y2-r,  x2, y2,    x2-r, y2, x1+r, y2,
        x1, y2,    x1, y2-r,  x1, y1+r, x1, y1,
    ]


# ---------------------------------------------------------------------------
# RoundedButton — theme-aware
# ---------------------------------------------------------------------------
class RoundedButton(tk.Canvas):
    def __init__(self, master, text, command, color_key,
                 fg="#FFFFFF", width=150, height=44, radius=12):
        super().__init__(master, width=width, height=height,
                         highlightthickness=0, cursor="arrow", bd=0)
        self._command   = command
        self._color_key = color_key   # e.g. "green" → T["green"]
        self._fg        = fg
        self._enabled   = True
        self._text      = text

        self._rect  = self.create_polygon(
            _rounded_points(2, 2, width-2, height-2, radius),
            smooth=True, fill=T[color_key], outline=""
        )
        self._label = self.create_text(
            width/2, height/2, text=text,
            fill=fg, font=FONT_BTN
        )
        self.bind("<Enter>",    self._on_enter)
        self.bind("<Leave>",    self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self._sync_canvas_bg()

    def _sync_canvas_bg(self):
        try:
            self.configure(bg=self.master.cget("bg"))
        except Exception:
            pass

    def _on_enter(self, _e):
        if self._enabled:
            self.itemconfigure(self._rect, fill=T[self._color_key + "_hover"])
            super().config(cursor="hand2")

    def _on_leave(self, _e):
        if self._enabled:
            self.itemconfigure(self._rect, fill=T[self._color_key])
            super().config(cursor="arrow")

    def _on_click(self, _e):
        if self._enabled and self._command:
            self._command()

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
            self.itemconfigure(self._rect,  fill=T[self._color_key])
            self.itemconfigure(self._label, fill=self._fg)
        else:
            self.itemconfigure(self._rect,  fill=T["btn_disabled"])
            self.itemconfigure(self._label, fill=T["btn_dis_fg"])
            super().config(cursor="arrow")

    def apply_theme(self):
        """Called when theme switches — repaint colours."""
        self._sync_canvas_bg()
        if self._enabled:
            self.itemconfigure(self._rect,  fill=T[self._color_key])
            self.itemconfigure(self._label, fill=self._fg)
        else:
            self.itemconfigure(self._rect,  fill=T["btn_disabled"])
            self.itemconfigure(self._label, fill=T["btn_dis_fg"])


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
class TutorialToNotesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TutorialToNotes")
        self.root.geometry("820x760")
        self.root.minsize(760, 700)

        self.is_session_active = False
        self.audio_capture  = None
        self.transcriber    = None
        self.note_generator = None
        self.pdf_exporter   = PDFExporter()
        self.generated_notes = None
        self.db = DBHandler()

        self._record_seconds = 0
        self._pulse_on       = False

        # collect every widget that needs repainting on theme switch
        self._themed_widgets: list = []
        self._rounded_buttons: list[RoundedButton] = []

        self._build_gui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # -----------------------------------------------------------------------
    # GUI build
    # -----------------------------------------------------------------------
    def _build_gui(self):
        self.root.configure(bg=T["bg_app"])

        # ── header bar ──────────────────────────────────────────────────────
        self._header = tk.Frame(self.root, bg=T["bg_app"])
        self._header.pack(fill="x", padx=24, pady=(20, 2))
        self._themed_widgets.append((self._header, "frame", "bg_app"))

        self._title_block = tk.Frame(self._header, bg=T["bg_app"])
        self._title_block.pack(side="left")
        self._themed_widgets.append((self._title_block, "frame", "bg_app"))

        self._lbl_title = tk.Label(
            self._title_block, text="🎓  TutorialToNotes",
            font=FONT_TITLE, fg=T["text_heading"], bg=T["bg_app"]
        )
        self._lbl_title.pack(anchor="w")
        self._themed_widgets.append((self._lbl_title, "label", "bg_app", "text_heading"))

        self._lbl_sub = tk.Label(
            self._title_block,
            text="Capture any lecture or tutorial — get clean, structured study notes.",
            font=FONT_SUBTITLE, fg=T["text_muted"], bg=T["bg_app"]
        )
        self._lbl_sub.pack(anchor="w", pady=(2, 0))
        self._themed_widgets.append((self._lbl_sub, "label", "bg_app", "text_muted"))

        # theme toggle (top-right)
        self._toggle_btn = tk.Label(
            self._header, text=T["toggle_label"],
            font=FONT_SMALL, fg=T["text_muted"], bg=T["bg_app"],
            cursor="hand2", padx=6, pady=4,
            relief="flat"
        )
        self._toggle_btn.pack(side="right", anchor="n", pady=6)
        self._toggle_btn.bind("<Button-1>", lambda _e: self._toggle_theme())
        self._themed_widgets.append((self._toggle_btn, "label", "bg_app", "text_muted"))

        # status pill
        self._pill_canvas = tk.Canvas(
            self._header, width=152, height=36,
            bg=T["bg_app"], bd=0, highlightthickness=0
        )
        self._pill_canvas.pack(side="right", anchor="n", pady=8, padx=(0, 10))
        self._themed_widgets.append((self._pill_canvas, "canvas", "bg_app"))

        self._pill_bg = self._pill_canvas.create_polygon(
            _rounded_points(1, 1, 151, 35, 17),
            smooth=True, fill=T["pill_bg"], outline=T["border"]
        )
        self._pill_dot = self._pill_canvas.create_oval(
            14, 13, 26, 25, fill=T["text_muted"], outline=""
        )
        self._pill_text = self._pill_canvas.create_text(
            36, 18, anchor="w", text="Idle",
            fill=T["text_primary"], font=FONT_PILL
        )

        # status detail line
        self._lbl_status = tk.Label(
            self.root, text="Ready when you are.",
            font=FONT_SMALL, fg=T["text_muted"], bg=T["bg_app"]
        )
        self._lbl_status.pack(pady=(0, 6))
        self._themed_widgets.append((self._lbl_status, "label", "bg_app", "text_muted"))

        # ── stat cards ──────────────────────────────────────────────────────
        self._stats_frame = tk.Frame(self.root, bg=T["bg_app"])
        self._stats_frame.pack(fill="x", padx=24, pady=4)
        self._themed_widgets.append((self._stats_frame, "frame", "bg_app"))

        self.duration_value = self._stat_card(self._stats_frame, "⏱", "Session length", "00:00")
        self.saved_value    = self._stat_card(self._stats_frame, "💾", "Saved sessions",  "—")
        self._refresh_saved_count()

        # ── transcript card ─────────────────────────────────────────────────
        self._tx_card = tk.Frame(
            self.root, bg=T["bg_card"],
            highlightbackground=T["border"], highlightthickness=1
        )
        self._tx_card.pack(fill="both", expand=True, padx=24, pady=8)
        self._themed_widgets.append((self._tx_card, "frame_border", "bg_card", "border"))

        tx_head = tk.Frame(self._tx_card, bg=T["bg_card"])
        tx_head.pack(fill="x", padx=14, pady=(12, 0))
        self._themed_widgets.append((tx_head, "frame", "bg_card"))

        self._lbl_tx_head = tk.Label(
            tx_head, text="🎧  Live Transcript",
            font=FONT_HEADING, fg=T["text_primary"], bg=T["bg_card"]
        )
        self._lbl_tx_head.pack(side="left")
        self._themed_widgets.append((self._lbl_tx_head, "label", "bg_card", "text_primary"))

        self.live_badge = tk.Label(
            tx_head, text="  ● REC  ",
            font=FONT_BADGE, fg="#FFFFFF",
            bg=T["badge_bg"], pady=2
        )
        # packed/unpacked dynamically

        self.transcript_box = scrolledtext.ScrolledText(
            self._tx_card, wrap=tk.WORD, font=FONT_BODY,
            bg=T["bg_input"], fg=T["text_primary"],
            insertbackground=T["text_primary"],
            selectbackground=T["select_bg"],
            relief="flat", bd=0, padx=12, pady=10, height=16
        )
        self.transcript_box.pack(padx=14, pady=10, fill="both", expand=True)
        self.transcript_box.config(state=tk.DISABLED)
        self._themed_widgets.append((self.transcript_box, "text", "bg_input", "text_primary"))
        self._style_scrollbar(self.transcript_box)

        # ── control bar ─────────────────────────────────────────────────────
        self._ctrl = tk.Frame(self.root, bg=T["bg_app"])
        self._ctrl.pack(fill="x", padx=24, pady=(4, 4))
        self._themed_widgets.append((self._ctrl, "frame", "bg_app"))

        self.start_button = self._make_btn(
            self._ctrl, "▶   Start Session", self.start_session, "green", width=176
        )
        self.stop_button = self._make_btn(
            self._ctrl, "■   Stop & Notes", self.stop_session, "red", width=164
        )
        self.stop_button.config(state=tk.DISABLED)

        self.save_button = self._make_btn(
            self._ctrl, "💾   Save PDF", self.save_pdf, "blue", width=144
        )
        self.save_button.config(state=tk.DISABLED)

        self.history_button = self._make_btn(
            self._ctrl, "📚   History", self.open_history, "purple", width=132
        )

        for btn in (self.start_button, self.stop_button,
                    self.save_button, self.history_button):
            btn.pack(side="left", padx=5, expand=True)

        # ── footer ──────────────────────────────────────────────────────────
        self._lbl_footer = tk.Label(
            self.root,
            text="🎙  Listens on-device   ·   🤖  AI-structured notes   ·   🗄  Persistent history",
            font=FONT_SMALL, fg=T["text_muted"], bg=T["bg_app"]
        )
        self._lbl_footer.pack(pady=(2, 14))
        self._themed_widgets.append((self._lbl_footer, "label", "bg_app", "text_muted"))

    # -----------------------------------------------------------------------
    # Widget helpers
    # -----------------------------------------------------------------------
    def _make_btn(self, parent, text, command, color_key, width=150):
        btn = RoundedButton(parent, text, command, color_key, width=width)
        self._rounded_buttons.append(btn)
        return btn

    def _stat_card(self, parent, icon, caption, initial):
        card = tk.Frame(
            parent, bg=T["bg_card"],
            highlightbackground=T["border"], highlightthickness=1
        )
        card.pack(side="left", fill="both", expand=True, padx=5)
        self._themed_widgets.append((card, "frame_border", "bg_card", "border"))

        val_lbl = tk.Label(card, text=initial, font=FONT_STAT,
                           fg=T["text_primary"], bg=T["bg_card"])
        val_lbl.pack(pady=(10, 0))
        self._themed_widgets.append((val_lbl, "label", "bg_card", "text_primary"))

        cap_lbl = tk.Label(card, text=f"{icon}  {caption}", font=FONT_SMALL,
                           fg=T["text_muted"], bg=T["bg_card"])
        cap_lbl.pack(pady=(0, 10))
        self._themed_widgets.append((cap_lbl, "label", "bg_card", "text_muted"))

        return val_lbl

    def _style_scrollbar(self, widget):
        try:
            widget.vbar.config(
                troughcolor=T["bg_card"], bg=T["scrollbar"],
                activebackground=T["accent"], relief="flat", bd=0
            )
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Theme switch
    # -----------------------------------------------------------------------
    def _toggle_theme(self):
        next_name = "light" if T["name"] == "dracula" else "dracula"
        T.clear()
        T.update(THEMES[next_name])
        self._apply_theme()

    def _apply_theme(self):
        self.root.configure(bg=T["bg_app"])

        for entry in self._themed_widgets:
            widget, kind = entry[0], entry[1]
            try:
                if kind == "frame":
                    widget.configure(bg=T[entry[2]])
                elif kind == "frame_border":
                    widget.configure(bg=T[entry[2]],
                                     highlightbackground=T[entry[3]])
                elif kind == "label":
                    widget.configure(bg=T[entry[2]], fg=T[entry[3]])
                elif kind == "canvas":
                    widget.configure(bg=T[entry[2]])
                elif kind == "text":
                    widget.configure(
                        bg=T[entry[2]], fg=T[entry[3]],
                        insertbackground=T[entry[3]],
                        selectbackground=T["select_bg"]
                    )
            except Exception:
                pass

        # repaint pill
        self._pill_canvas.itemconfigure(self._pill_bg,
                                        fill=T["pill_bg"], outline=T["border"])
        self._pill_canvas.itemconfigure(self._pill_text, fill=T["text_primary"])

        # repaint title colour
        self._lbl_title.configure(fg=T["text_heading"])

        # repaint toggle label
        self._toggle_btn.configure(text=T["toggle_label"])

        # repaint rounded buttons
        for btn in self._rounded_buttons:
            btn.apply_theme()

        # style scrollbar
        self._style_scrollbar(self.transcript_box)

    # -----------------------------------------------------------------------
    # Status helpers
    # -----------------------------------------------------------------------
    STATUS_COLORS = {
        "gray":   "text_muted",
        "orange": "amber",
        "green":  "green",
        "blue":   "blue",
        "red":    "red",
        "violet": "accent",
    }
    STATUS_SHORT = {
        "gray":   "Idle",
        "orange": "Working…",
        "green":  "Listening",
        "blue":   "Ready",
        "red":    "Error",
        "violet": "Busy",
    }

    def _update_status(self, text, color="gray"):
        def apply():
            color_key = self.STATUS_COLORS.get(color, "text_muted")
            dot_color = T[color_key]
            self._pill_canvas.itemconfigure(self._pill_dot, fill=dot_color)
            self._pill_canvas.itemconfigure(
                self._pill_text, text=self.STATUS_SHORT.get(color, "…")
            )
            fg = dot_color if color in ("orange", "blue", "red") else T["text_muted"]
            self._lbl_status.configure(text=text, fg=fg)
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
            self.live_badge.pack(side="left", padx=12)
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
        self.duration_value.config(
            text=f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        )
        self.root.after(1000, self._tick)

    def _start_pulse(self):
        self._pulse_on = False
        self._pulse()

    def _pulse(self):
        if not self.is_session_active:
            return
        self._pulse_on = not self._pulse_on
        color_key = self.STATUS_COLORS.get("green", "green")
        fill = T[color_key] if self._pulse_on else T["pill_bg"]
        self._pill_canvas.itemconfigure(self._pill_dot, fill=fill)
        self.root.after(600, self._pulse)

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
                "Gemini_Api_Key not found in .env.\n\nAdd this line to your .env file:\nGemini_Api_Key=your_key_here"
            )
            return

        self.is_session_active = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.DISABLED)

        self.transcript_box.config(state=tk.NORMAL)
        self.transcript_box.delete(1.0, tk.END)
        self.transcript_box.config(state=tk.DISABLED)

        self._set_live(True)
        self._start_timer()
        self._start_pulse()
        self._update_status("Loading Whisper model…", "orange")
        threading.Thread(target=self._init_and_start, daemon=True).start()

    def _init_and_start(self):
        self.transcriber = Transcriber(
            text_callback=self._append_transcript, model_size="base"
        )
        self.transcriber.start()
        self.audio_capture = AudioCapture(chunk_callback=self.transcriber.queue_chunk)
        self.audio_capture.start()
        self._update_status("Listening — play your tutorial now.", "green")

    def stop_session(self):
        self.is_session_active = False
        self.stop_button.config(state=tk.DISABLED)
        self._set_live(False)
        self._update_status("Stopping and generating notes…", "orange")
        threading.Thread(target=self._stop_and_generate, daemon=True).start()

    def _stop_and_generate(self):
        if self.audio_capture:
            self.audio_capture.stop()
        if self.transcriber:
            self.transcriber.stop()

        full_transcript = self.transcriber.get_full_transcript() if self.transcriber else ""

        if not full_transcript.strip():
            self._update_status("No audio captured — nothing to process.", "red")
            self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
            return

        self._update_status("Generating structured notes with Gemini…", "orange")
        self.note_generator  = NoteGenerator(api_key=GEMINI_API_KEY)
        self.generated_notes = self.note_generator.generate_notes(full_transcript)

        title = self._extract_title(self.generated_notes)
        self.db.save_session(
            title=title,
            transcript=full_transcript,
            notes_markdown=self.generated_notes
        )
        self._refresh_saved_count()
        self._update_status("Notes ready — save as PDF or check History.", "blue")
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
            self._update_status(f"Saved — {os.path.basename(file_path)}", "green")
            messagebox.showinfo("Saved", f"PDF saved to:\n{file_path}")

    # -----------------------------------------------------------------------
    # History window
    # -----------------------------------------------------------------------
    def open_history(self):
        try:
            sessions = self.db.get_all_sessions()
        except Exception as exc:
            messagebox.showerror(
                "Database Error",
                f"Could not reach MongoDB.\n\n{exc}\n\nMake sure 'docker compose up' is running."
            )
            return

        if not sessions:
            messagebox.showinfo("History", "No saved sessions yet.")
            return

        hw = tk.Toplevel(self.root)
        hw.title("Session History")
        hw.geometry("860x660")
        hw.minsize(740, 540)
        hw.configure(bg=T["bg_app"])
        hw.transient(self.root)

        # header
        h_bar = tk.Frame(hw, bg=T["bg_app"])
        h_bar.pack(fill="x", padx=22, pady=(18, 6))

        tk.Label(h_bar, text="📚  Session History",
                 font=(FONT_FAMILY, 15, "bold"),
                 fg=T["text_heading"], bg=T["bg_app"]).pack(side="left")
        tk.Label(h_bar, text=f"{len(sessions)} sessions saved",
                 font=FONT_SMALL, fg=T["text_muted"],
                 bg=T["bg_app"]).pack(side="left", padx=12, pady=(4, 0))

        # session list
        list_card = tk.Frame(hw, bg=T["bg_card"],
                             highlightbackground=T["border"], highlightthickness=1)
        list_card.pack(fill="x", padx=22, pady=4)

        list_inner = tk.Frame(list_card, bg=T["bg_card"])
        list_inner.pack(padx=10, pady=10, fill="both", expand=True)

        sb = tk.Scrollbar(list_inner, troughcolor=T["bg_card"],
                          bg=T["scrollbar"], activebackground=T["accent"],
                          relief="flat", bd=0)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(
            list_inner, font=FONT_BODY, height=7,
            bg=T["bg_input"], fg=T["text_primary"],
            selectbackground=T["select_bg"], selectforeground=T["text_primary"],
            highlightthickness=0, relief="flat", bd=0,
            activestyle="none", yscrollcommand=sb.set, selectmode=tk.SINGLE
        )
        listbox.pack(side=tk.LEFT, fill="both", expand=True)
        sb.config(command=listbox.yview)

        for s in sessions:
            listbox.insert(tk.END, "  " + s["title"])

        # preview
        prev_card = tk.Frame(hw, bg=T["bg_card"],
                             highlightbackground=T["border"], highlightthickness=1)
        prev_card.pack(fill="both", expand=True, padx=22, pady=4)

        tk.Label(prev_card, text="📝  Notes Preview",
                 font=FONT_HEADING, fg=T["text_primary"],
                 bg=T["bg_card"]).pack(anchor="w", padx=14, pady=(12, 0))

        notes_box = scrolledtext.ScrolledText(
            prev_card, wrap=tk.WORD, font=FONT_BODY,
            bg=T["bg_input"], fg=T["text_primary"],
            insertbackground=T["text_primary"],
            selectbackground=T["select_bg"],
            relief="flat", bd=0, padx=12, pady=10, height=14
        )
        notes_box.pack(padx=14, pady=10, fill="both", expand=True)
        notes_box.config(state=tk.DISABLED)
        self._style_scrollbar(notes_box)

        # buttons
        btn_row = tk.Frame(hw, bg=T["bg_app"])
        btn_row.pack(pady=(6, 18))

        def on_select(_e):
            sel = listbox.curselection()
            if not sel:
                return
            notes_box.config(state=tk.NORMAL)
            notes_box.delete(1.0, tk.END)
            notes_box.insert(tk.END, sessions[sel[0]]["notes_markdown"])
            notes_box.config(state=tk.DISABLED)

        def export_selected():
            sel = listbox.curselection()
            if not sel:
                messagebox.showwarning("Nothing selected", "Please click a session first.")
                return
            s    = sessions[sel[0]]
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=f"{s['title']}.pdf"
            )
            if path:
                self.pdf_exporter.export(s["notes_markdown"], path, title=s["title"])
                messagebox.showinfo("Saved", f"PDF saved to:\n{path}")

        def delete_selected():
            sel = listbox.curselection()
            if not sel:
                messagebox.showwarning("Nothing selected", "Please click a session first.")
                return
            if messagebox.askyesno("Delete", "Permanently delete this session?"):
                self.db.delete_session(str(sessions[sel[0]]["_id"]))
                sessions.pop(sel[0])
                listbox.delete(sel[0])
                notes_box.config(state=tk.NORMAL)
                notes_box.delete(1.0, tk.END)
                notes_box.config(state=tk.DISABLED)
                self._refresh_saved_count()

        listbox.bind("<<ListboxSelect>>", on_select)

        export_btn = RoundedButton(btn_row, "📄   Export PDF",
                                   export_selected, "blue", width=176)
        export_btn.grid(row=0, column=0, padx=6)

        delete_btn = RoundedButton(btn_row, "🗑   Delete",
                                   delete_selected, "red", width=144)
        delete_btn.grid(row=0, column=1, padx=6)

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
    app  = TutorialToNotesApp(root)
    root.mainloop()