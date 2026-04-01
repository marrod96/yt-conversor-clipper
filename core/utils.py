"""
Utility functions for YT Clipper
"""
import re
import json
import os
import io
import urllib.request
from PIL import Image
from .config import HISTORY_F, THUMB_SIZE


def hhmmss_to_sec(t: str) -> int:
    """Convert mm:ss or hh:mm:ss to seconds (int)."""
    parts = [int(p.strip()) for p in t.strip().split(":") if p.strip()]
    if not parts:
        raise ValueError("Empty time string")
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    else:
        raise ValueError("Unsupported time format")


def sec_to_hhmmss(s: int) -> str:
    """Convert seconds (int) to mm:ss or hh:mm:ss format."""
    s = max(0, s)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{sec:02d}"
    else:
        return f"{m:02d}:{sec:02d}"


def validate_time(t: str) -> bool:
    """Validate time format mm:ss or hh:mm:ss."""
    return bool(re.fullmatch(r"\d{1,2}(?::\d{2}){1,2}", t.strip()))


def load_history() -> list:
    """Load download history from file."""
    if os.path.exists(HISTORY_F):
        try:
            with open(HISTORY_F) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_history(items: list) -> None:
    """Save download history to file."""
    try:
        with open(HISTORY_F, "w") as f:
            json.dump(items[-30:], f, indent=2)
    except Exception:
        pass


def fetch_thumbnail(url: str) -> Image.Image | None:
    """Download YouTube thumbnail as PIL Image."""
    vid_id = None
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    if m:
        vid_id = m.group(1)
    if not vid_id:
        return None

    for quality in ["maxresdefault", "hqdefault", "mqdefault"]:
        thumb_url = f"https://img.youtube.com/vi/{vid_id}/{quality}.jpg"
        try:
            with urllib.request.urlopen(thumb_url, timeout=6) as r:
                data = r.read()
            img = Image.open(io.BytesIO(data)).convert("RGB")
            img = img.resize(THUMB_SIZE, Image.LANCZOS)
            return img
        except Exception:
            continue

    return None


def sanitize_filename(text: str, max_len: int = 40) -> str:
    """Sanitize filename by removing invalid characters."""
    safe = re.sub(r'[\\/:*?"<>|]', "_", text)[:max_len].strip()
    return safe
