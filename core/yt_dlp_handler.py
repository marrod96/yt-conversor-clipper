"""
yt-dlp integration and video download handling
"""
import subprocess
import json
import re


def run_yt_dlp_info(url: str) -> dict:
    """Get video metadata via yt-dlp --dump-json."""
    try:
        cmd = ["yt-dlp", "--dump-json", "--no-playlist", url]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return json.loads(r.stdout)
    except Exception:
        pass
    return {}


def build_format_string(quality: str, fmt: str) -> str:
    """Build yt-dlp format string based on quality and format selection."""
    if fmt in ("mp3", "m4a"):
        return "bestaudio/best"

    q_map = {
        "Mejor disponible": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "1080p":  "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",
        "720p":   "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",
        "480p":   "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]",
        "360p":   "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]",
        "Audio only": "bestaudio/best",
    }
    return q_map.get(quality, "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4")


def download_video(url: str, output_path: str, format_str: str, callback=None, 
                   cancel_flag=None) -> bool:
    """Download video using yt-dlp with progress tracking.
    
    Returns:
        bool: True if successful, False otherwise
    """
    cmd = [
        "yt-dlp",
        "-f", format_str,
        "--no-playlist",
        "--newline",
        "-o", output_path,
        url
    ]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        
        for line in proc.stdout:
            line = line.strip()
            
            # Check for cancellation
            if cancel_flag and cancel_flag.is_set():
                proc.terminate()
                return False
            
            # Parse progress
            if "[download]" in line:
                if callback:
                    callback(line)
                m = re.search(r"(\d+(?:\.\d+)?)%", line)
                if m:
                    pct = float(m.group(1)) / 100
                    if callback:
                        callback(line, pct)
        
        proc.wait()
        return proc.returncode == 0
        
    except FileNotFoundError:
        raise FileNotFoundError("yt-dlp not found. Is it installed and in PATH?")
    except Exception as e:
        raise Exception(f"Download failed: {e}")
