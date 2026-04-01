"""
Configuration and constants for YT Clipper
"""
import os
import customtkinter as ctk

# ── App config ────────────────────────────────────────────────────────────────
APP_NAME   = "YT Clipper"
APP_VER    = "1.1.0"
HISTORY_F  = os.path.join(os.path.expanduser("~"), ".ytclipper_history.json")
THUMB_SIZE = (320, 180)

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ── Color Palette ────────────────────────────────────────────────────────────
COLORS = {
    "bg":        "#F5F6FA",
    "panel":     "#FFFFFF",
    "border":    "#E2E5EC",
    "accent":    "#2563EB",
    "accent2":   "#1D4ED8",
    "success":   "#16A34A",
    "danger":    "#DC2626",
    "warn":      "#D97706",
    "text":      "#111827",
    "sub":       "#6B7280",
    "muted":     "#9CA3AF",
    "tag_bg":    "#EFF6FF",
    "tag_fg":    "#1D4ED8",
}
