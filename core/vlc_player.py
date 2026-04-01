"""
VLC-embedded player widget for YT Clipper.

Streams the video directly from the yt-dlp-resolved URL — no local file needed.
Requires: python-vlc  (pip install python-vlc)
          VLC media player installed on the system (https://www.videolan.org)
"""

import threading
import subprocess
import sys
import tkinter as tk
import customtkinter as ctk

try:
    import vlc
    VLC_AVAILABLE = True
except ImportError:
    VLC_AVAILABLE = False

from .config import COLORS as C


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_stream_url(youtube_url: str) -> list[str] | None:
    """Ask yt-dlp for one or more direct stream URLs (video and optional audio)."""
    for fmt in [
        "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/best",
        "best",
    ]:
        try:
            r = subprocess.run(
                ["yt-dlp", "-f", fmt, "--get-url", "--no-playlist", youtube_url],
                capture_output=True, text=True, timeout=30
            )
            urls = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
            if urls:
                # yt-dlp may return two lines (video + audio) for DASH.
                # Keep both so VLC can play audio+video with input-slave.
                return urls
        except Exception:
            continue
    return None


def _sec_to_display(ms: int) -> str:
    """Convert milliseconds to mm:ss or hh:mm:ss display."""
    seconds = max(0, ms // 1000)  # Convert to int seconds
    from .utils import sec_to_hhmmss
    return sec_to_hhmmss(seconds)


# ── Widget ────────────────────────────────────────────────────────────────────

class VLCPlayer(ctk.CTkFrame):
    """
    An embedded VLC player inside a customtkinter frame.

    Public API
    ----------
    load(youtube_url)           — resolve stream URL and prepare player
    set_trim(start_s, end_s)    — optional trim window (seconds); highlights region
    stop()                      — stop and release
    """

    PLAYER_W = 320
    PLAYER_H = 180

    def __init__(self, master, **kw):
        super().__init__(master,
                         fg_color=C["panel"],
                         corner_radius=12,
                         border_width=1,
                         border_color=C["border"],
                         **kw)

        self._instance: "vlc.Instance | None"  = None
        self._player:   "vlc.MediaPlayer | None" = None
        self._stream_url: str | list[str] | None = None
        self._duration_ms: int                   = 0
        self._trim_start_ms: int | None          = None
        self._trim_end_ms:   int | None          = None
        self._seeking    = False
        self._poll_id    = None
        self._loading    = False

        if VLC_AVAILABLE:
            # One VLC instance per player; --no-xlib avoids X11 crashes on Linux
            args = ["--no-xlib"] if sys.platform.startswith("linux") else []
            self._instance = vlc.Instance(*args)
            self._player   = self._instance.media_player_new()

        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Section title
        ctk.CTkLabel(self, text="VISTA PREVIA",
                     font=ctk.CTkFont("Helvetica", 12, "bold"),
                     text_color=C["sub"]).pack(anchor="w", padx=16, pady=(12, 0))

        # Video canvas — VLC renders into this native widget
        canvas_wrap = ctk.CTkFrame(self, fg_color="#000000",
                                    width=self.PLAYER_W, height=self.PLAYER_H,
                                   corner_radius=6)
        canvas_wrap.pack(padx=16, pady=(6, 0))
        canvas_wrap.pack_propagate(False)

        self._video_frame = tk.Frame(canvas_wrap, bg="#000000",
                                     width=self.PLAYER_W, height=self.PLAYER_H)
        self._video_frame.pack(fill="both", expand=True)
        self._video_frame.pack_propagate(False)

        # Overlay label (shown when VLC is unavailable or loading)
        self._overlay = ctk.CTkLabel(canvas_wrap, text="▶",
                                     font=ctk.CTkFont("Helvetica", 36),
                                     text_color="#444444",
                                     fg_color="#111111",
                                     width=self.PLAYER_W, height=self.PLAYER_H,
                                     corner_radius=6)
        self._overlay.place(x=0, y=0, relwidth=1, relheight=1)

        if not VLC_AVAILABLE:
            self._overlay.configure(
                text="VLC no encontrado\npip install python-vlc\n+ instalar VLC",
                font=ctk.CTkFont("Helvetica", 12))

        # Time label
        time_row = ctk.CTkFrame(self, fg_color="transparent")
        time_row.pack(fill="x", padx=16, pady=(4, 0))

        self._time_label = ctk.CTkLabel(time_row, text="00:00",
                                        font=ctk.CTkFont("Courier", 11),
                                        text_color=C["sub"])
        self._time_label.pack(side="left")

        self._dur_label = ctk.CTkLabel(time_row, text="/ 00:00",
                                       font=ctk.CTkFont("Courier", 11),
                                       text_color=C["muted"])
        self._dur_label.pack(side="left", padx=(4, 0))

        self._trim_label = ctk.CTkLabel(time_row, text="",
                                        font=ctk.CTkFont("Helvetica", 11),
                                        text_color=C["accent"])
        self._trim_label.pack(side="right")

        # Seek bar
        self._seek_var = tk.DoubleVar(value=0)
        self._seek_bar = ctk.CTkSlider(self, variable=self._seek_var,
                                       from_=0, to=1000,
                                       height=14,
                                       button_color=C["accent"],
                                       button_hover_color=C["accent2"],
                                       progress_color=C["accent"],
                                       fg_color=C["border"],
                                       corner_radius=4,
                                       command=self._on_seek_drag)
        self._seek_bar.pack(fill="x", padx=16, pady=(2, 4))
        self._seek_bar.bind("<ButtonPress-1>",   self._seek_start)
        self._seek_bar.bind("<ButtonRelease-1>", self._seek_end)

        # Trim region indicator (canvas-based overlay on seek bar)
        self._trim_canvas = tk.Canvas(self, height=6, bg=C["bg"],
                                      highlightthickness=0)
        self._trim_canvas.pack(fill="x", padx=16, pady=(0, 4))

        # Controls row
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=16, pady=(0, 12))

        self._play_btn = ctk.CTkButton(ctrl, text="▶  Reproducir",
                                       height=32, corner_radius=8,
                                       font=ctk.CTkFont("Helvetica", 13),
                                       fg_color=C["accent"],
                                       hover_color=C["accent2"],
                                       command=self._toggle_play,
                                       state="disabled")
        self._play_btn.pack(side="left", fill="x", expand=True)

        self._jump_btn = ctk.CTkButton(ctrl, text="⏮ Inicio recorte",
                                       height=32, width=130, corner_radius=8,
                                       font=ctk.CTkFont("Helvetica", 12),
                                       fg_color=C["bg"],
                                       hover_color=C["border"],
                                       text_color=C["text"],
                                       border_width=1,
                                       border_color=C["border"],
                                       command=self._jump_to_trim_start,
                                       state="disabled")
        self._jump_btn.pack(side="left", padx=(8, 0))

        # Loading spinner label
        self._status_label = ctk.CTkLabel(self, text="",
                                          font=ctk.CTkFont("Helvetica", 11),
                                          text_color=C["muted"])
        self._status_label.pack(pady=(0, 4))

    # ── Public API ────────────────────────────────────────────────────────────

    def load(self, youtube_url: str):
        """Resolve stream URL in background, then arm the player."""
        if not VLC_AVAILABLE:
            return
        if self._loading:
            return

        self._loading = True
        self._stop_poll()
        self._set_status("Obteniendo stream...", C["accent"])
        self._play_btn.configure(state="disabled", text="▶  Cargando...")
        self._overlay.configure(text="⏳", fg_color="#111111")
        self._overlay.lift()

        threading.Thread(target=self._load_worker,
                         args=(youtube_url,), daemon=True).start()

    def set_trim(self, start_s: int | None, end_s: int | None):
        """Set trim region in seconds (int). Pass None to clear."""
        self._trim_start_ms = int(start_s * 1000) if start_s is not None else None
        self._trim_end_ms   = int(end_s * 1000) if end_s is not None else None
        self._update_trim_ui()
        if self._trim_start_ms is not None:
            self._jump_btn.configure(state="normal")
        else:
            self._jump_btn.configure(state="disabled")

    def stop(self):
        """Stop playback and release resources."""
        self._stop_poll()
        if self._player:
            self._player.stop()
        self._stream_url   = None
        self._duration_ms  = 0
        self._trim_start_ms = None
        self._trim_end_ms = None
        self._play_btn.configure(state="disabled", text="▶  Reproducir")
        self._overlay.configure(text="▶", fg_color="#111111")
        self._overlay.lift()
        self._set_status("", None)

    # ── Internal: loading ─────────────────────────────────────────────────────

    def _load_worker(self, youtube_url: str):
        url = _get_stream_url(youtube_url)
        self.after(0, lambda: self._on_stream_ready(url))

    def _on_stream_ready(self, url: str | None):
        self._loading = False
        if not url:
            self._set_status("No se pudo obtener el stream.", C["danger"])
            self._overlay.configure(text="Sin stream\n¿URL válida?", fg_color="#1a0000")
            self._overlay.lift()
            self._play_btn.configure(state="disabled", text="▶  Reproducir")
            return

        self._stream_url = url
        media = self._instance.media_new(url[0] if isinstance(url, list) else url)

        # Support DASH adaptive streams: first URL is video, optional second is audio.
        if isinstance(url, list) and len(url) > 1:
            for slave_url in url[1:]:
                media.add_option(f":input-slave={slave_url}")

        self._player.set_media(media)

        # Attach VLC output to our canvas BEFORE playing
        self._attach_vlc_window()

        self._play_btn.configure(state="normal", text="▶  Reproducir")
        self._set_status("Stream listo. Pulsa Reproducir.", C["success"])
        self._overlay.configure(text="▶  Listo", fg_color="#0a1a0a")

    def _attach_vlc_window(self):
        """Tell VLC to render into our video frame widget."""
        win_id = self._video_frame.winfo_id()
        if sys.platform == "win32":
            self._player.set_hwnd(win_id)
        elif sys.platform == "darwin":
            self._player.set_nsobject(win_id)
        else:
            self._player.set_xwindow(win_id)

    # ── Internal: playback ────────────────────────────────────────────────────

    def _toggle_play(self):
        if not self._player or not self._stream_url:
            return

        state = self._player.get_state()
        if state in (vlc.State.Playing,):
            self._player.pause()
            self._play_btn.configure(text="▶  Reproducir")
        elif state in (vlc.State.Paused, vlc.State.Stopped, vlc.State.NothingSpecial):
            # If stopped and trim active, jump to start
            if state == vlc.State.Stopped and self._trim_start_ms is not None:
                self._player.play()
                # Wait briefly for player to start before seeking
                self.after(600, lambda: self._seek_to_ms(self._trim_start_ms))
            else:
                self._player.play()
            self._play_btn.configure(text="⏸  Pausar")
            self._overlay.lower()
            self._start_poll()
        elif state == vlc.State.Ended:
            # Restart
            if isinstance(self._stream_url, list):
                media = self._instance.media_new(self._stream_url[0])
                for slave_url in self._stream_url[1:]:
                    media.add_option(f":input-slave={slave_url}")
            else:
                media = self._instance.media_new(self._stream_url)

            self._player.set_media(media)
            self._attach_vlc_window()
            self._player.play()
            if self._trim_start_ms is not None:
                self.after(600, lambda: self._seek_to_ms(self._trim_start_ms))
            self._play_btn.configure(text="⏸  Pausar")
            self._overlay.lower()
            self._start_poll()
        else:
            self._player.play()
            self._play_btn.configure(text="⏸  Pausar")
            self._overlay.lower()
            self._start_poll()

    def _jump_to_trim_start(self):
        if self._player and self._trim_start_ms is not None:
            if self._player.get_state() not in (vlc.State.Playing, vlc.State.Paused):
                self._player.play()
                self._play_btn.configure(text="⏸  Pausar")
                self._overlay.lower()
                self._start_poll()
                self.after(600, lambda: self._seek_to_ms(self._trim_start_ms))
            else:
                self._seek_to_ms(self._trim_start_ms)

    def _seek_to_ms(self, ms: int):
        if self._player and self._duration_ms > 0:
            self._player.set_time(ms)

    # ── Internal: seek bar ────────────────────────────────────────────────────

    def _seek_start(self, event=None):
        self._seeking = True

    def _seek_end(self, event=None):
        if self._player and self._duration_ms > 0:
            pos = self._seek_var.get() / 1000.0
            self._player.set_position(pos)
        self._seeking = False

    def _on_seek_drag(self, value):
        if self._duration_ms > 0:
            ms = int(float(value) / 1000.0 * self._duration_ms)
            self._time_label.configure(text=_sec_to_display(ms))

    # ── Internal: poll loop ───────────────────────────────────────────────────

    def _start_poll(self):
        self._stop_poll()
        self._poll()

    def _stop_poll(self):
        if self._poll_id is not None:
            try:
                self.after_cancel(self._poll_id)
            except Exception:
                pass
            self._poll_id = None

    def _poll(self):
        """Update seek bar and time display at ~10 fps."""
        if not self._player:
            return

        state = self._player.get_state()

        # Update duration once we have it
        if self._duration_ms <= 0:
            d = self._player.get_length()
            if d > 0:
                self._duration_ms = d
                self._dur_label.configure(text=f"/ {_sec_to_display(d)}")
                self._update_trim_ui()

        # Update position
        if not self._seeking and self._duration_ms > 0:
            t = self._player.get_time()
            if t >= 0:
                self._time_label.configure(text=_sec_to_display(t))
                pos_scaled = (t / self._duration_ms) * 1000
                self._seek_var.set(pos_scaled)

            # Auto-stop at trim end
            if (self._trim_end_ms is not None
                    and t >= self._trim_end_ms
                    and state == vlc.State.Playing):
                self._player.pause()
                self._play_btn.configure(text="▶  Reproducir")
                return  # don't reschedule

        # Check for natural end
        if state == vlc.State.Ended:
            self._play_btn.configure(text="▶  Reiniciar")
            self._seek_var.set(1000)
            return

        # Reschedule
        self._poll_id = self.after(100, self._poll)

    # ── Internal: trim UI ─────────────────────────────────────────────────────

    def _update_trim_ui(self):
        """Draw trim region on the indicator canvas and update trim label."""
        c = self._trim_canvas
        c.delete("all")

        if self._duration_ms <= 0:
            return

        w = c.winfo_width()
        if w < 2:
            c.update_idletasks()
            w = c.winfo_width()
        if w < 2:
            return

        # Background track
        c.create_rectangle(0, 1, w, 5, fill=C["border"], outline="")

        if self._trim_start_ms is not None and self._trim_end_ms is not None:
            x0 = int((self._trim_start_ms / self._duration_ms) * w)
            x1 = int((self._trim_end_ms   / self._duration_ms) * w)
            x0 = max(0, min(x0, w))
            x1 = max(0, min(x1, w))
            c.create_rectangle(x0, 0, x1, 6, fill=C["accent"], outline="")

            dur_ms = self._trim_end_ms - self._trim_start_ms
            dur_s = dur_ms // 1000
            m, s  = divmod(dur_s, 60)
            self._trim_label.configure(
                text=f"✂ {m:02d}:{s:02d} seleccionado",
                text_color=C["accent"])
        else:
            self._trim_label.configure(text="")

        # Bind resize
        c.bind("<Configure>", lambda e: self._update_trim_ui())

    # ── Internal: helpers ─────────────────────────────────────────────────────

    def _set_status(self, msg: str, color: str | None):
        self._status_label.configure(
            text=msg,
            text_color=color if color else C["muted"])

    def destroy(self):
        """Clean up VLC resources on widget destruction."""
        self._stop_poll()
        if self._player:
            self._player.stop()
            self._player.release()
        if self._instance:
            self._instance.release()
        super().destroy()
