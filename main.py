import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import threading
import os
from dotenv import load_dotenv
from datetime import datetime
from PIL import Image, ImageTk

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
        "toggle_icon":    "sun",
        "toggle_tip":     "Switch to Light",
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
        "toggle_icon":    "moon",
        "toggle_tip":     "Switch to Dark",
    },
}

T = dict(THEMES["dracula"])

ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")

# Cache so we don't reload on every theme switch
_icon_cache: dict = {}


def load_icon(name: str, size: int = 20) -> ImageTk.PhotoImage | None:
    key = (name, size)
    if key in _icon_cache:
        return _icon_cache[key]
    path = os.path.join(ICON_DIR, f"{name}.png")
    if not os.path.exists(path):
        return None
    try:
        img = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        _icon_cache[key] = photo
        return photo
    except Exception:
        return None


def _rounded_points(x1, y1, x2, y2, r):
    return [
        x1+r, y1,  x2-r, y1,  x2, y1,  x2, y1+r,
        x2, y2-r,  x2, y2,    x2-r, y2, x1+r, y2,
        x1, y2,    x1, y2-r,  x1, y1+r, x1, y1,
    ]


# ---------------------------------------------------------------------------
# RoundedButton — supports optional icon
# ---------------------------------------------------------------------------
class RoundedButton(tk.Canvas):
    def __init__(self, master, text, command, color_key,
                 icon_name=None, fg="#FFFFFF", width=150, height=44, radius=12):
        super().__init__(master, width=width, height=height,
                         highlightthickness=0, cursor="arrow", bd=0)
        self._command   = command
        self._color_key = color_key
        self._fg        = fg
        self._enabled   = True
        self._icon_img  = None

        self._rect = self.create_polygon(
            _rounded_points(2, 2, width-2, height-2, radius),
            smooth=True, fill=T[color_key], outline=""
        )

        # icon + label layout
        if icon_name:
            self._icon_img = load_icon(icon_name, 18)

        if self._icon_img:
            self._icon_item = self.create_image(
                18, height/2, image=self._icon_img, anchor="center"
            )
            self._label = self.create_text(
                width/2 + 8, height/2, text=text,
                fill=fg, font=FONT_BTN, anchor="center"
            )
        else:
            self._icon_item = None
            self._label = self.create_text(
                width/2, height/2, text=text,
                fill=fg, font=FONT_BTN, anchor="center"
            )

        self.bind("<Enter>",    self._on_enter)
        self.bind("<Leave>",    self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self._sync_bg()

    def _sync_bg(self):
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
        self._sync_bg()
        if self._enabled:
            self.itemconfigure(self._rect,  fill=T[self._color_key])
            self.itemconfigure(self._label, fill=self._fg)
        else:
            self.itemconfigure(self._rect,  fill=T["btn_disabled"])
            self.itemconfigure(self._label, fill=T["btn_dis_fg"])


# ---------------------------------------------------------------------------
# IconLabel — a label that shows a PNG icon + optional text side by side
# ---------------------------------------------------------------------------
class IconLabel(tk.Frame):
    def __init__(self, master, icon_name, text="", icon_size=16,
                 font=FONT_HEADING, fg_key="text_primary", bg_key="bg_card", **kw):
        super().__init__(master, bg=T[bg_key], **kw)
        self._fg_key = fg_key
        self._bg_key = bg_key

        self._icon_img = load_icon(icon_name, icon_size)
        if self._icon_img:
            self._icon_lbl = tk.Label(self, image=self._icon_img,
                                      bg=T[bg_key], bd=0)
            self._icon_lbl.pack(side="left", padx=(0, 6))
        else:
            self._icon_lbl = None

        self._text_lbl = tk.Label(self, text=text, font=font,
                                  fg=T[fg_key], bg=T[bg_key])
        self._text_lbl.pack(side="left")

    def apply_theme(self):
        self.configure(bg=T[self._bg_key])
        if self._icon_lbl:
            self._icon_lbl.configure(bg=T[self._bg_key])
        self._text_lbl.configure(bg=T[self._bg_key], fg=T[self._fg_key])


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
        self.audio_capture   = None
        self.transcriber     = None
        self.note_generator  = None
        self.pdf_exporter    = PDFExporter()
        self.generated_notes = None
        self.db              = DBHandler()

        self._record_seconds = 0
        self._pulse_on       = False

        self._themed_widgets:  list              = []
        self._rounded_buttons: list[RoundedButton] = []
        self._icon_labels:     list[IconLabel]   = []

        self._build_gui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # -----------------------------------------------------------------------
    # GUI build
    # -----------------------------------------------------------------------
    def _build_gui(self):
        self.root.configure(bg=T["bg_app"])

        # ── header ──────────────────────────────────────────────────────────
        self._header = tk.Frame(self.root, bg=T["bg_app"])
        self._header.pack(fill="x", padx=24, pady=(20, 2))
        self._tw(self._header, "frame", "bg_app")

        # logo + title block
        logo_block = tk.Frame(self._header, bg=T["bg_app"])
        logo_block.pack(side="left")
        self._tw(logo_block, "frame", "bg_app")

        logo_row = tk.Frame(logo_block, bg=T["bg_app"])
        logo_row.pack(anchor="w")
        self._tw(logo_row, "frame", "bg_app")

        self._logo_img = load_icon("logo", 32)
        if self._logo_img:
            logo_lbl = tk.Label(logo_row, image=self._logo_img,
                                bg=T["bg_app"], bd=0)
            logo_lbl.pack(side="left", padx=(0, 8))
            self._tw(logo_lbl, "label", "bg_app", "bg_app")

        self._lbl_title = tk.Label(
            logo_row, text="TutorialToNotes",
            font=FONT_TITLE, fg=T["text_heading"], bg=T["bg_app"]
        )
        self._lbl_title.pack(side="left")
        self._tw(self._lbl_title, "label", "bg_app", "text_heading")

        self._lbl_sub = tk.Label(
            logo_block,
            text="Converts any online lecture or tutorial to clean, structured study notes.",
            font=FONT_SUBTITLE, fg=T["text_muted"], bg=T["bg_app"]
        )
        self._lbl_sub.pack(anchor="w", pady=(3, 0))
        self._tw(self._lbl_sub, "label", "bg_app", "text_muted")

        # theme toggle icon button (top-right)
        self._toggle_img = load_icon(T["toggle_icon"], 22)
        self._toggle_canvas = tk.Canvas(
            self._header, width=32, height=32,
            bg=T["bg_app"], bd=0, highlightthickness=0, cursor="hand2"
        )
        self._toggle_canvas.pack(side="right", anchor="n", pady=10, padx=(0, 4))
        self._tw(self._toggle_canvas, "canvas", "bg_app")
        self._toggle_icon_item = None
        if self._toggle_img:
            self._toggle_icon_item = self._toggle_canvas.create_image(
                16, 16, image=self._toggle_img, anchor="center"
            )
        self._toggle_canvas.bind("<Button-1>", lambda _e: self._toggle_theme())

        # status pill
        self._pill_canvas = tk.Canvas(
            self._header, width=152, height=36,
            bg=T["bg_app"], bd=0, highlightthickness=0
        )
        self._pill_canvas.pack(side="right", anchor="n", pady=8, padx=(0, 8))
        self._tw(self._pill_canvas, "canvas", "bg_app")

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

        # status detail
        self._lbl_status = tk.Label(
            self.root, text="Ready when you are.",
            font=FONT_SMALL, fg=T["text_muted"], bg=T["bg_app"]
        )
        self._lbl_status.pack(pady=(0, 6))
        self._tw(self._lbl_status, "label", "bg_app", "text_muted")

        # ── stat cards ──────────────────────────────────────────────────────
        self._stats_frame = tk.Frame(self.root, bg=T["bg_app"])
        self._stats_frame.pack(fill="x", padx=24, pady=4)
        self._tw(self._stats_frame, "frame", "bg_app")

        self.duration_value = self._stat_card(self._stats_frame, "timer",    "Session length", "00:00")
        self.saved_value    = self._stat_card(self._stats_frame, "database", "Saved sessions",  "—")
        self._refresh_saved_count()

        # ── transcript card ─────────────────────────────────────────────────
        self._tx_card = tk.Frame(
            self.root, bg=T["bg_card"],
            highlightbackground=T["border"], highlightthickness=1
        )
        self._tx_card.pack(fill="both", expand=True, padx=24, pady=8)
        self._tw(self._tx_card, "frame_border", "bg_card", "border")

        tx_head = tk.Frame(self._tx_card, bg=T["bg_card"])
        tx_head.pack(fill="x", padx=14, pady=(12, 0))
        self._tw(tx_head, "frame", "bg_card")

        tx_head_lbl = IconLabel(
            tx_head, "transcript", "Live Transcript",
            icon_size=16, font=FONT_HEADING,
            fg_key="text_primary", bg_key="bg_card"
        )
        tx_head_lbl.pack(side="left")
        self._icon_labels.append(tx_head_lbl)

        # REC badge — uses mic icon
        self._rec_img = load_icon("rec", 14)
        self.live_badge = tk.Label(
            tx_head,
            image=self._rec_img if self._rec_img else None,
            text="" if self._rec_img else "  REC  ",
            compound="left",
            font=FONT_BADGE, fg="#FFFFFF",
            bg=T["badge_bg"], padx=6, pady=2
        )

        self.transcript_box = scrolledtext.ScrolledText(
            self._tx_card, wrap=tk.WORD, font=FONT_BODY,
            bg=T["bg_input"], fg=T["text_primary"],
            insertbackground=T["text_primary"],
            selectbackground=T["select_bg"],
            relief="flat", bd=0, padx=12, pady=10, height=16
        )
        self.transcript_box.pack(padx=14, pady=10, fill="both", expand=True)
        self.transcript_box.config(state=tk.DISABLED)
        self._tw(self.transcript_box, "text", "bg_input", "text_primary")
        self._style_scrollbar(self.transcript_box)

        # ── control bar ─────────────────────────────────────────────────────
        self._ctrl = tk.Frame(self.root, bg=T["bg_app"])
        self._ctrl.pack(fill="x", padx=24, pady=(4, 4))
        self._tw(self._ctrl, "frame", "bg_app")

        self.start_button = self._make_btn(
            self._ctrl, "Start Session", self.start_session,
            "green", icon_name="start", width=176
        )
        self.stop_button = self._make_btn(
            self._ctrl, "Stop & Note", self.stop_session,
            "red", icon_name="stop", width=164
        )
        self.stop_button.config(state=tk.DISABLED)

        self.save_button = self._make_btn(
            self._ctrl, "Save PDF", self.save_pdf,
            "blue", icon_name="save", width=144
        )
        self.save_button.config(state=tk.DISABLED)

        self.history_button = self._make_btn(
            self._ctrl, "History", self.open_history,
            "purple", icon_name="history", width=132
        )

        for btn in (self.start_button, self.stop_button,
                    self.save_button, self.history_button):
            btn.pack(side="left", padx=5, expand=True)

        # ── footer ──────────────────────────────────────────────────────────
        self._lbl_footer = tk.Label(
            self.root,
            text="Listens on device  ·  AI-structured notes  ·  Persistent history",
            font=FONT_SMALL, fg=T["text_muted"], bg=T["bg_app"]
        )
        self._lbl_footer.pack(pady=(2, 14))
        self._tw(self._lbl_footer, "label", "bg_app", "text_muted")

    # -----------------------------------------------------------------------
    # Widget helpers
    # -----------------------------------------------------------------------
    def _tw(self, widget, kind, *keys):
        """Register a widget for theme repainting."""
        self._themed_widgets.append((widget, kind) + keys)

    def _make_btn(self, parent, text, command, color_key,
                  icon_name=None, width=150):
        btn = RoundedButton(parent, text, command, color_key,
                            icon_name=icon_name, width=width)
        self._rounded_buttons.append(btn)
        return btn

    def _stat_card(self, parent, icon_name, caption, initial):
        card = tk.Frame(
            parent, bg=T["bg_card"],
            highlightbackground=T["border"], highlightthickness=1
        )
        card.pack(side="left", fill="both", expand=True, padx=5)
        self._tw(card, "frame_border", "bg_card", "border")

        val_lbl = tk.Label(card, text=initial, font=FONT_STAT,
                           fg=T["text_primary"], bg=T["bg_card"])
        val_lbl.pack(pady=(10, 0))
        self._tw(val_lbl, "label", "bg_card", "text_primary")

        cap_row = IconLabel(card, icon_name, caption,
                            icon_size=14, font=FONT_SMALL,
                            fg_key="text_muted", bg_key="bg_card")
        cap_row.pack(pady=(2, 10))
        self._icon_labels.append(cap_row)

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

        # pill
        self._pill_canvas.itemconfigure(self._pill_bg,
                                        fill=T["pill_bg"], outline=T["border"])
        self._pill_canvas.itemconfigure(self._pill_text, fill=T["text_primary"])

        # title
        self._lbl_title.configure(fg=T["text_heading"])

        # theme toggle icon
        new_toggle_img = load_icon(T["toggle_icon"], 22)
        if new_toggle_img and self._toggle_icon_item:
            self._toggle_img = new_toggle_img
            self._toggle_canvas.itemconfigure(self._toggle_icon_item,
                                              image=self._toggle_img)
        self._toggle_canvas.configure(bg=T["bg_app"])

        # rounded buttons
        for btn in self._rounded_buttons:
            btn.apply_theme()

        # icon labels
        for il in self._icon_labels:
            il.apply_theme()

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
        fill = T["green"] if self._pulse_on else T["pill_bg"]
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
                "Gemini_Api_Key not found in .env.\n\nAdd this line:\nGemini_Api_Key=your_key_here"
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
        self._update_status("Listening: play your tutorial now.", "green")

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
            self._update_status("No audio captured: nothing to process.", "red")
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
        self._update_status("Notes ready: save as PDF or check History.", "blue")
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

        h_title = IconLabel(h_bar, "history", "Session History",
                            icon_size=20, font=(FONT_FAMILY, 15, "bold"),
                            fg_key="text_heading", bg_key="bg_app")
        h_title.pack(side="left")

        tk.Label(h_bar, text=f"  {len(sessions)} saved",
                 font=FONT_SMALL, fg=T["text_muted"],
                 bg=T["bg_app"]).pack(side="left", pady=(4, 0))

        # session list card
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

        # preview card
        prev_card = tk.Frame(hw, bg=T["bg_card"],
                             highlightbackground=T["border"], highlightthickness=1)
        prev_card.pack(fill="both", expand=True, padx=22, pady=4)

        prev_head = IconLabel(prev_card, "notes", "Notes Preview",
                              icon_size=16, font=FONT_HEADING,
                              fg_key="text_primary", bg_key="bg_card")
        prev_head.pack(anchor="w", padx=14, pady=(12, 0))

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

        # action buttons
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

        RoundedButton(btn_row, "Export PDF", export_selected,
                      "blue", icon_name="export", width=176
                      ).grid(row=0, column=0, padx=6)

        RoundedButton(btn_row, "Delete", delete_selected,
                      "red", icon_name="trash", width=144
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
    app  = TutorialToNotesApp(root)
    root.mainloop()