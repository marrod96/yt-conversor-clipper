"""
Main application GUI using customtkinter
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import sys
import shutil
from datetime import datetime
from PIL import Image, ImageDraw

from .config import APP_NAME, APP_VER, COLORS as C, THUMB_SIZE
from .utils import (
    hhmmss_to_sec, sec_to_hhmmss, validate_time,
    load_history, save_history, fetch_thumbnail, sanitize_filename
)
from .yt_dlp_handler import run_yt_dlp_info, build_format_string, download_video
from .ffmpeg_handler import trim_video
from .widgets import SectionFrame, LabeledEntry, StatusBar
from .vlc_player import VLCPlayer


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VER}")
        self.geometry("860x820")
        self.minsize(760, 700)
        self.configure(fg_color=C["bg"])

        self._job_thread: threading.Thread | None = None
        self._cancel_flag = threading.Event()
        self._history = load_history()
        self._info: dict = {}
        self._last_output_path: str | None = None

        self._build_ui()
        self._set_defaults()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C["panel"], height=56,
                           corner_radius=0, border_width=0)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text=f"✂  {APP_NAME}",
                     font=ctk.CTkFont("Helvetica", 18, "bold"),
                     text_color=C["accent"]).pack(side="left", padx=20)
        ctk.CTkLabel(hdr, text=f"v{APP_VER}",
                     font=ctk.CTkFont("Helvetica", 11),
                     text_color=C["muted"]).pack(side="left")

        # ── Scrollable body ───────────────────────────────────────────────────
        body = ctk.CTkScrollableFrame(self, fg_color=C["bg"],
                                      scrollbar_button_color=C["border"])
        body.pack(fill="both", expand=True)

        pad = {"padx": 16, "pady": 6}

        # ── URL section ───────────────────────────────────────────────────────
        url_sec = SectionFrame(body, title="URL DEL VIDEO")
        url_sec.pack(fill="x", **pad)

        url_row = ctk.CTkFrame(url_sec, fg_color="transparent")
        url_row.pack(fill="x", padx=16, pady=(4, 12))

        self.url_entry = ctk.CTkEntry(
            url_row,
            placeholder_text="https://www.youtube.com/watch?v=...",
            font=ctk.CTkFont("Helvetica", 13),
            height=38, corner_radius=8,
            border_color=C["border"], fg_color=C["bg"])
        self.url_entry.pack(side="left", fill="x", expand=True)

        self.fetch_btn = ctk.CTkButton(
            url_row, text="Obtener info",
            width=110, height=38,
            font=ctk.CTkFont("Helvetica", 13),
            fg_color=C["accent"], hover_color=C["accent2"],
            corner_radius=8,
            command=self._fetch_info_threaded)
        self.fetch_btn.pack(side="left", padx=(8, 0))

        self.reset_btn = ctk.CTkButton(
            url_row, text="Reset",
            width=80, height=38,
            font=ctk.CTkFont("Helvetica", 13),
            fg_color=C["bg"],
            hover_color=C["border"],
            text_color=C["text"],
            border_width=1,
            border_color=C["border"],
            corner_radius=8,
            command=self._reset_url)
        self.reset_btn.pack(side="left", padx=(8, 0))

        # ── Preview + Info row ────────────────────────────────────────────────
        pi_row = ctk.CTkFrame(body, fg_color="transparent")
        pi_row.pack(fill="x", **pad)

        # VLC Player (left column)
        self.vlc_player = VLCPlayer(pi_row)
        self.vlc_player.pack(side="left", fill="both")

        # Info panel (right column)
        info_frame = SectionFrame(pi_row, title="INFORMACIÓN")
        info_frame.pack(side="left", fill="both", expand=True, padx=(8, 0))

        self.info_rows = {}
        fields = [
            ("Título",       "title"),
            ("Duración",     "duration"),
            ("Resolución",   "resolution"),
            ("FPS",          "fps"),
            ("Fecha",        "upload_date"),
            ("Tamaño aprox", "filesize"),
            ("Formatos",     "formats"),
        ]
        for label, key in fields:
            row = ctk.CTkFrame(info_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(row, text=label + ":", width=100, anchor="w",
                         font=ctk.CTkFont("Helvetica", 12, "bold"),
                         text_color=C["sub"]).pack(side="left")
            val = ctk.CTkLabel(row, text="—", anchor="w", wraplength=340,
                               font=ctk.CTkFont("Helvetica", 12),
                               text_color=C["text"])
            val.pack(side="left", fill="x", expand=True)
            self.info_rows[key] = val
        ctk.CTkLabel(info_frame, text="").pack()  # bottom padding

        # ── Output settings ───────────────────────────────────────────────────
        self._build_output_section(body, pad)

        # ── Trim section ──────────────────────────────────────────────────────
        self._build_trim_section(body, pad)

        # ── Log ───────────────────────────────────────────────────────────────
        log_sec = SectionFrame(body, title="REGISTRO")
        log_sec.pack(fill="x", **pad)

        self.log_box = ctk.CTkTextbox(
            log_sec, height=110, state="disabled",
            font=ctk.CTkFont("Courier", 11),
            fg_color=C["bg"], border_width=0, corner_radius=0,
            text_color=C["sub"], wrap="word")
        self.log_box.pack(fill="x", padx=12, pady=(4, 12))

        # ── Progress ──────────────────────────────────────────────────────────
        prog_frame = ctk.CTkFrame(body, fg_color="transparent")
        prog_frame.pack(fill="x", padx=16, pady=(4, 0))

        self.progress = ctk.CTkProgressBar(
            prog_frame, height=8, corner_radius=4,
            fg_color=C["border"], progress_color=C["accent"])
        self.progress.pack(fill="x")
        self.progress.set(0)

        self.progress_label = ctk.CTkLabel(
            prog_frame, text="",
            font=ctk.CTkFont("Helvetica", 11),
            text_color=C["sub"])
        self.progress_label.pack(anchor="w", pady=(2, 0))

        # ── Action buttons ────────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(body, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(10, 16))

        self.run_btn = ctk.CTkButton(
            btn_frame, text="▶  Descargar y cortar",
            height=44, corner_radius=10,
            font=ctk.CTkFont("Helvetica", 15, "bold"),
            fg_color=C["accent"], hover_color=C["accent2"],
            command=self._run)
        self.run_btn.pack(side="left", fill="x", expand=True)

        self.cancel_btn = ctk.CTkButton(
            btn_frame, text="✕  Cancelar",
            height=44, width=130, corner_radius=10,
            font=ctk.CTkFont("Helvetica", 14),
            fg_color=C["bg"], hover_color="#FEE2E2",
            text_color=C["danger"],
            border_width=1, border_color=C["danger"],
            command=self._cancel, state="disabled")
        self.cancel_btn.pack(side="left", padx=(8, 0))

        self.open_btn = ctk.CTkButton(
            btn_frame, text="📂 Abrir carpeta",
            height=44, width=150, corner_radius=10,
            font=ctk.CTkFont("Helvetica", 13),
            fg_color=C["bg"], hover_color=C["border"],
            text_color=C["text"],
            border_width=1, border_color=C["border"],
            command=self._open_dest, state="disabled")
        self.open_btn.pack(side="left", padx=(8, 0))

        ctk.CTkLabel(body, text="").pack()  # bottom spacer

        # ── Status bar ────────────────────────────────────────────────────────
        self.status = StatusBar(self)
        self.status.pack(fill="x", side="bottom")

    def _build_output_section(self, body, pad):
        out_sec = SectionFrame(body, title="CONFIGURACIÓN DE SALIDA")
        out_sec.pack(fill="x", **pad)

        out_inner = ctk.CTkFrame(out_sec, fg_color="transparent")
        out_inner.pack(fill="x", padx=16, pady=(4, 12))

        # Dest folder
        dest_row = ctk.CTkFrame(out_inner, fg_color="transparent")
        dest_row.pack(fill="x", pady=3)
        ctk.CTkLabel(dest_row, text="Carpeta destino:", width=130, anchor="w",
                     font=ctk.CTkFont("Helvetica", 13),
                     text_color=C["text"]).pack(side="left")
        self.dest_entry = ctk.CTkEntry(
            dest_row, height=36, corner_radius=8,
            font=ctk.CTkFont("Helvetica", 13),
            border_color=C["border"], fg_color=C["bg"])
        self.dest_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dest_row, text="📁", width=40, height=36,
                      fg_color=C["bg"], hover_color=C["border"],
                      text_color=C["text"], corner_radius=8,
                      border_width=1, border_color=C["border"],
                      command=self._browse_dest).pack(side="left", padx=(6, 0))

        # Name
        name_row = ctk.CTkFrame(out_inner, fg_color="transparent")
        name_row.pack(fill="x", pady=3)
        ctk.CTkLabel(name_row, text="Nombre del clip:", width=130, anchor="w",
                     font=ctk.CTkFont("Helvetica", 13),
                     text_color=C["text"]).pack(side="left")
        self.name_entry = ctk.CTkEntry(
            name_row, height=36, corner_radius=8,
            font=ctk.CTkFont("Helvetica", 13),
            border_color=C["border"], fg_color=C["bg"],
            placeholder_text="MiClip")
        self.name_entry.pack(side="left", fill="x", expand=True)

        # Quality + Format
        qf_row = ctk.CTkFrame(out_inner, fg_color="transparent")
        qf_row.pack(fill="x", pady=3)

        ctk.CTkLabel(qf_row, text="Calidad:", width=130, anchor="w",
                     font=ctk.CTkFont("Helvetica", 13),
                     text_color=C["text"]).pack(side="left")
        self.quality_var = ctk.StringVar(value="Mejor disponible")
        self.quality_menu = ctk.CTkOptionMenu(
            qf_row, variable=self.quality_var, width=180, height=36,
            values=["Mejor disponible", "1080p", "720p", "480p", "360p", "Audio only"],
            fg_color=C["bg"], button_color=C["accent"],
            button_hover_color=C["accent2"], text_color=C["text"],
            corner_radius=8, font=ctk.CTkFont("Helvetica", 13))
        self.quality_menu.pack(side="left")

        ctk.CTkLabel(qf_row, text="Formato:", width=80, anchor="w",
                     font=ctk.CTkFont("Helvetica", 13),
                     text_color=C["text"]).pack(side="left", padx=(20, 0))
        self.format_var = ctk.StringVar(value="mp4")
        self.format_menu = ctk.CTkOptionMenu(
            qf_row, variable=self.format_var, width=110, height=36,
            values=["mp4", "mkv", "mov", "mp3", "m4a"],
            fg_color=C["bg"], button_color=C["accent"],
            button_hover_color=C["accent2"], text_color=C["text"],
            corner_radius=8, font=ctk.CTkFont("Helvetica", 13),
            command=self._on_format_change)
        self.format_menu.pack(side="left")

    def _build_trim_section(self, body, pad):
        trim_sec = SectionFrame(body, title="RECORTE  (opcional)")
        trim_sec.pack(fill="x", **pad)

        trim_inner = ctk.CTkFrame(trim_sec, fg_color="transparent")
        trim_inner.pack(fill="x", padx=16, pady=(4, 12))

        self.trim_var = ctk.BooleanVar(value=False)
        self.trim_check = ctk.CTkCheckBox(
            trim_inner, text="Activar recorte",
            variable=self.trim_var,
            font=ctk.CTkFont("Helvetica", 13),
            text_color=C["text"], fg_color=C["accent"],
            command=self._toggle_trim)
        self.trim_check.pack(anchor="w", pady=(0, 8))

        times_row = ctk.CTkFrame(trim_inner, fg_color="transparent")
        times_row.pack(fill="x")

        ctk.CTkLabel(times_row, text="Inicio (mm:ss):", width=190, anchor="w",
                     font=ctk.CTkFont("Helvetica", 13),
                     text_color=C["text"]).pack(side="left")
        self.start_entry = ctk.CTkEntry(
            times_row, width=90, height=36, corner_radius=8,
            placeholder_text="00:00",
            font=ctk.CTkFont("Helvetica", 13),
            border_color=C["border"], fg_color=C["bg"])
        self.start_entry.pack(side="left")

        ctk.CTkLabel(times_row, text="Fin (mm:ss):", width=190, anchor="w",
                     font=ctk.CTkFont("Helvetica", 13),
                     text_color=C["text"]).pack(side="left", padx=(20, 0))
        self.end_entry = ctk.CTkEntry(
            times_row, width=90, height=36, corner_radius=8,
            placeholder_text="03:00",
            font=ctk.CTkFont("Helvetica", 13),
            border_color=C["border"], fg_color=C["bg"])
        self.end_entry.pack(side="left")

        self.trim_duration_label = ctk.CTkLabel(
            times_row, text="",
            font=ctk.CTkFont("Helvetica", 12),
            text_color=C["success"])
        self.trim_duration_label.pack(side="left", padx=(16, 0))

        self.start_entry.bind("<KeyRelease>", self._update_trim_duration)
        self.end_entry.bind("<KeyRelease>",   self._update_trim_duration)
        self._toggle_trim()

    # ── Defaults ──────────────────────────────────────────────────────────────
    def _set_defaults(self):
        self.dest_entry.insert(0, r"D:\ESC\2026")
        self.name_entry.insert(0, "MiClip")

    # ── Events ────────────────────────────────────────────────────────────────
    def _browse_dest(self):
        d = filedialog.askdirectory()
        if d:
            self.dest_entry.delete(0, "end")
            self.dest_entry.insert(0, d)
            self.open_btn.configure(state="normal")

    def _toggle_trim(self):
        state = "normal" if self.trim_var.get() else "disabled"
        self.start_entry.configure(state=state)
        self.end_entry.configure(state=state)
        self._sync_trim_to_player()

    def _update_trim_duration(self, event=None):
        try:
            s = hhmmss_to_sec(self.start_entry.get() or "0")
            e = hhmmss_to_sec(self.end_entry.get() or "0")
            dur = e - s
            if dur > 0:
                self.trim_duration_label.configure(
                    text=f"→ {sec_to_hhmmss(dur)} de clip",
                    text_color=C["success"])
            else:
                self.trim_duration_label.configure(text="", text_color=C["danger"])
        except Exception:
            self.trim_duration_label.configure(text="")

        self._sync_trim_to_player()

    def _sync_trim_to_player(self):
        """Push current trim values (or None) into the VLC player widget."""
        if self.trim_var.get():
            try:
                s = hhmmss_to_sec(self.start_entry.get() or "0")
                e = hhmmss_to_sec(self.end_entry.get() or "0")
                if e > s:
                    self.vlc_player.set_trim(s, e)
                    return
            except Exception:
                pass
        self.vlc_player.set_trim(None, None)

    def _on_format_change(self, val):
        if val in ("mp3", "m4a"):
            self.quality_var.set("Audio only")
            self.quality_menu.configure(state="disabled")
        else:
            if self.quality_var.get() == "Audio only":
                self.quality_var.set("Mejor disponible")
            self.quality_menu.configure(state="normal")

    # ── Logging ───────────────────────────────────────────────────────────────
    def _log(self, msg: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _reset_url(self):
        """Clear URL and reset all related UI elements."""
        # Clear URL entry
        self.url_entry.delete(0, "end")
        
        # Stop VLC player
        self.vlc_player.stop()
        
        # Clear info rows
        for v in self.info_rows.values():
            v.configure(text="—")
        
        # Clear internal state
        self._info = {}
        self._last_output_path = None
        
        # Reset trim fields
        self.start_entry.delete(0, "end")
        self.end_entry.delete(0, "end")
        self.trim_duration_label.configure(text="")
        self.vlc_player._trim_start_ms = None
        self.vlc_player._trim_end_ms = None
        
        # Clear log
        self._clear_log()
        
        # Reset status
        self.status.set("Reset completado.", C["success"])

    # ── Fetch info ────────────────────────────────────────────────────────────
    def _fetch_info_threaded(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("URL vacía", "Introduce una URL de YouTube.")
            return
        self.fetch_btn.configure(state="disabled", text="Cargando...")
        self.status.set("Obteniendo información del video...", C["accent"])

        # Kick off VLC stream resolution immediately
        self.vlc_player.load(url)

        threading.Thread(target=self._fetch_info_worker, args=(url,),
                         daemon=True).start()

    def _fetch_info_worker(self, url: str):
        self._log(f"Obteniendo info: {url}")
        info = run_yt_dlp_info(url)
        self._info = info
        self.after(0, lambda: self._populate_info(info))
        self.after(0, lambda: self.fetch_btn.configure(state="normal",
                                                        text="Obtener info"))

    def _populate_info(self, info: dict):
        if not info:
            self.status.set("No se pudo obtener info del video.", C["warn"])
            for v in self.info_rows.values():
                v.configure(text="—")
            return

        dur_s    = info.get("duration", 0)
        title    = info.get("title", "—")[:80]
        date_raw = str(info.get("upload_date", ""))
        date     = (f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:]}"
                    if len(date_raw) == 8 else "—")

        best_h = best_fps = total_size = 0
        formats = []
        for fmt in info.get("formats", []):
            h   = fmt.get("height") or 0
            fps = fmt.get("fps") or 0
            fs  = fmt.get("filesize") or fmt.get("filesize_approx") or 0
            if h:
                formats.append(f"{h}p")
                if h > best_h:
                    best_h, best_fps = h, fps
            total_size = max(total_size, fs)

        res_str = f"{best_h}p" if best_h else "—"
        fps_str = f"{int(best_fps)} fps" if best_fps else "—"
        size_str = f"~{total_size/1024/1024:.1f} MB" if total_size else "—"
        fmt_set  = sorted(set(formats),
                          key=lambda x: int(x[:-1]) if x[:-1].isdigit() else 0,
                          reverse=True)
        fmt_str  = "  ".join(fmt_set[:6]) if fmt_set else "—"

        self.info_rows["title"].configure(text=title)
        self.info_rows["duration"].configure(text=sec_to_hhmmss(dur_s) if dur_s else "—")
        self.info_rows["resolution"].configure(text=res_str)
        self.info_rows["fps"].configure(text=fps_str)
        self.info_rows["upload_date"].configure(text=date)
        self.info_rows["filesize"].configure(text=size_str)
        self.info_rows["formats"].configure(text=fmt_str)

        safe = sanitize_filename(title)
        if safe:
            self.name_entry.delete(0, "end")
            self.name_entry.insert(0, safe)

        if dur_s and not self.end_entry.get():
            self.end_entry.delete(0, "end")
            self.end_entry.insert(0, sec_to_hhmmss(int(dur_s)))

        self.status.set(f"Info cargada: {title}", C["success"])
        self._log(f"Info OK — {title} ({sec_to_hhmmss(dur_s)})")

    # ── Run ───────────────────────────────────────────────────────────────────
    def _run(self):
        url  = self.url_entry.get().strip()
        dest = self.dest_entry.get().strip()
        name = self.name_entry.get().strip() or "MiClip"
        fmt  = self.format_var.get()

        if not url:
            messagebox.showwarning("Falta URL", "Introduce la URL del video.")
            return
        if not dest:
            messagebox.showwarning("Falta destino", "Selecciona la carpeta destino.")
            return
        if not os.path.isdir(dest):
            try:
                os.makedirs(dest, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"No se puede crear la carpeta:\n{e}")
                return

        trim_active = self.trim_var.get()
        start = end = None
        if trim_active:
            s_raw = self.start_entry.get().strip()
            e_raw = self.end_entry.get().strip()
            if not validate_time(s_raw) or not validate_time(e_raw):
                messagebox.showwarning("Tiempos inválidos",
                                       "Formato correcto: mm:ss  (ej. 01:30)")
                return
            start, end = s_raw, e_raw
            if hhmmss_to_sec(end) <= hhmmss_to_sec(start):
                messagebox.showwarning("Tiempos inválidos",
                                       "El tiempo de fin debe ser mayor al de inicio.")
                return

        # Stop preview while downloading (avoids network contention)
        self.vlc_player.stop()

        self._clear_log()
        self._cancel_flag.clear()
        self.run_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.open_btn.configure(state="disabled")
        self.progress.set(0)
        self.progress_label.configure(text="")

        fmt_str = build_format_string(self.quality_var.get(), fmt)
        params  = dict(url=url, dest=dest, name=name, fmt=fmt,
                       fmt_str=fmt_str, start=start, end=end, trim=trim_active)

        self._job_thread = threading.Thread(
            target=self._job_worker, args=(params,), daemon=True)
        self._job_thread.start()

    def _cancel(self):
        self._cancel_flag.set()
        self.status.set("Cancelando...", C["warn"])
        self._log("Cancelación solicitada.")

    # ── Worker ────────────────────────────────────────────────────────────────
    def _job_worker(self, p: dict):
        if p["fmt"] in ("mp3", "m4a"):
            temp_path = os.path.join(p["dest"], f"_ytclipper_temp.{p['fmt']}")
        else:
            temp_path = os.path.join(p["dest"], "_ytclipper_temp.mp4")
        out_path  = os.path.join(p["dest"], f"{p['name']}.{p['fmt']}")

        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)

            # Step 1 — Download
            self._update_progress(0.05, "Descargando video...")
            self._log("Iniciando descarga con yt-dlp...")

            audio_only = p["fmt"] in ("mp3", "m4a") or p["fmt_str"] == "bestaudio/best"

            def dl_cb(line, progress=None):
                self._log(line)
                if progress is not None:
                    self._update_progress(0.05 + progress * 0.55, "Descargando...")

            ok = download_video(p["url"], temp_path, p["fmt_str"],
                                callback=dl_cb, cancel_flag=self._cancel_flag,
                                file_format=p["fmt"])

            if not ok:
                if self._cancel_flag.is_set():
                    self._finish(cancelled=True); return
                
                # Build error message based on format
                if audio_only:
                    error_msg = ("Fallo en descarga/conversión a audio.\n\n"
                                "Verifica que esté instalado:\n"
                                "  • ffmpeg (y ffprobe)\n"
                                "  • yt-dlp (actualizado)\n\n"
                                "Revisa el REGISTRO para detalles específicos.")
                else:
                    error_msg = ("yt-dlp falló al descargar el video.\n\n"
                                "Posibles causas:\n"
                                "• URL inválida o vídeo restringido/privado\n"
                                "• Problema de conexión a internet\n"
                                "• yt-dlp desactualizado (ejecuta: yt-dlp -U)\n"
                                "• Contenido bloqueado geograficamente\n\n"
                                "Revisa el REGISTRO para más detalles.")
                self._finish(error=error_msg)
                return

            if audio_only:
                if os.path.exists(temp_path):
                    shutil.move(temp_path, out_path)
                self._log(f"✔ Audio guardado: {out_path}")
                self._add_history(p)
                self._finish(out_path=out_path)
                return

            # Step 2 — Trim
            if p["trim"] and p["start"] and p["end"]:
                self._update_progress(0.65, "Cortando clip con ffmpeg...")
                self._log(f"Recortando {p['start']} → {p['end']}...")

                ok = trim_video(temp_path, out_path, p["start"], p["end"],
                                cancel_flag=self._cancel_flag)
                if not ok:
                    if self._cancel_flag.is_set():
                        self._finish(cancelled=True); return
                    self._finish(error="ffmpeg falló al cortar el video.")
                    return
                self._log(f"✔ Clip creado: {out_path}")
            else:
                shutil.move(temp_path, out_path)
                temp_path = None
                self._log(f"✔ Video guardado: {out_path}")

        except FileNotFoundError as e:
            self._finish(error=str(e))
            return
        except Exception as e:
            self._finish(error=str(e))
            return
        finally:
            try:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

        self._add_history(p)
        self._finish(out_path=out_path)

    def _update_progress(self, val: float, label: str = ""):
        self.after(0, lambda: self.progress.set(val))
        if label:
            self.after(0, lambda: self.progress_label.configure(text=label))
            self.after(0, lambda: self.status.set(label, C["accent"]))

    def _finish(self, out_path=None, error=None, cancelled=False):
        def _ui():
            self.run_btn.configure(state="normal")
            self.cancel_btn.configure(state="disabled")
            self.progress.set(1 if out_path else 0)
            if cancelled:
                self.progress.set(0)
                self.progress_label.configure(text="Cancelado.")
                self.status.set("Operación cancelada.", C["warn"])
                self._log("— Cancelado por el usuario.")
            elif error:
                self.progress_label.configure(text="Error.")
                self.status.set(f"Error: {error}", C["danger"])
                self._log(f"❌ {error}")
                messagebox.showerror("Error", error)
            else:
                self.progress_label.configure(
                    text=f"✔ Listo: {os.path.basename(out_path)}")
                self.status.set("✔ Clip creado correctamente.", C["success"])
                self._log(f"✔ Finalizado: {out_path}")
                self.open_btn.configure(state="normal")
                self._last_output_path = out_path
        self.after(0, _ui)

    # ── History ───────────────────────────────────────────────────────────────
    def _add_history(self, p: dict):
        self._history.append({
            "url":  p["url"],
            "name": p["name"],
            "dest": p["dest"],
            "date": datetime.now().isoformat(timespec="seconds"),
        })
        save_history(self._history)

    def _open_dest(self):
        dest = self.dest_entry.get().strip()
        if dest and os.path.isdir(dest):
            if sys.platform == "win32":
                os.startfile(dest)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", dest])
            else:
                subprocess.Popen(["xdg-open", dest])
