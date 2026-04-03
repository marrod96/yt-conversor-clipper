"""
yt-dlp integration and video download handling
"""
import subprocess
import json
import re
import shutil


def _check_tool_available(tool_name: str) -> bool:
    """Check if a tool is available in PATH."""
    return shutil.which(tool_name) is not None


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
                   cancel_flag=None, file_format: str = "") -> bool:
    """Download video using yt-dlp with progress tracking.
    
    Args:
        url: YouTube URL
        output_path: Output file path template
        format_str: yt-dlp format string
        callback: Progress callback function
        cancel_flag: Threading event to cancel download
        file_format: File format (mp3, m4a, mp4, etc.) for metadata handling
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Pre-flight checks for audio-only formats
    if file_format.lower() in ("mp3", "m4a"):
        if not _check_tool_available("ffmpeg"):
            raise FileNotFoundError(
                "ffmpeg not found in PATH. Required for audio conversion to MP3/M4A.\n"
                "Please install ffmpeg or ensure it's in your system PATH.")
        if not _check_tool_available("ffprobe"):
            raise FileNotFoundError(
                "ffprobe not found in PATH. Required for audio processing.\n"
                "Please install ffmpeg (includes ffprobe) or ensure it's in your system PATH.")
    
    cmd = [
        "yt-dlp",
        "-f", format_str,
        "--no-playlist",
        "--newline",
        "-o", output_path,
    ]

    # Convert audio-only formats to the requested destination codec
    if file_format.lower() in ("mp3", "m4a"):
        cmd.extend([
            "--extract-audio",
            "--audio-format", file_format.lower(),
            "--audio-quality", "0",
        ])

    # Add metadata embedding for audio formats (with graceful fallback)
    use_metadata = file_format.lower() in ("mp3", "m4a", "opus", "vorbis")
    if use_metadata:
        cmd.extend([
            "--embed-metadata",      # Embedea título, artista, descripción, fecha, etc.
            "--embed-thumbnail",     # Embedea la carátula en el archivo
        ])
    
    cmd.append(url)

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        
        # Collect stdout and stderr
        stdout_lines = []
        stderr_buffer = []
        
        # Read stdout in real time
        for line in proc.stdout:
            line = line.strip()
            if line:
                stdout_lines.append(line)
            
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
        
        # Collect stderr after process ends
        _, stderr_data = proc.communicate()
        if stderr_data:
            stderr_buffer = [l.strip() for l in stderr_data.strip().split('\n') if l.strip()]
        
        # Log stderr errors/warnings
        for err_line in stderr_buffer:
            lower_err = err_line.lower()
            if "error" in lower_err or "ffmpeg" in lower_err or "ffprobe" in lower_err:
                if callback:
                    callback(f"[ERROR] {err_line}")
            elif "warning" in lower_err:
                if callback:
                    callback(f"[WARNING] {err_line}")
        
        # If exit code is not 0, try without metadata embedding for audio files
        if proc.returncode != 0 and use_metadata:
            if callback:
                callback("[Reintentando descarga sin --embed-metadata/--embed-thumbnail...]")
            
            cmd_retry = [
                "yt-dlp",
                "-f", format_str,
                "--no-playlist",
                "--newline",
                "-o", output_path,
                url
            ]
            
            proc_retry = subprocess.Popen(cmd_retry, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, text=True)
            
            for line in proc_retry.stdout:
                line = line.strip()
                if line:
                    if "[download]" in line:
                        if callback:
                            callback(f"[Reintento] {line}")
                        m = re.search(r"(\d+(?:\.\d+)?)%", line)
                        if m:
                            pct = float(m.group(1)) / 100
            
            proc_retry.wait()
            
            # Check retry stderr
            _, retry_stderr = proc_retry.communicate()
            if retry_stderr and callback:
                for err_line in retry_stderr.split('\n'):
                    if err_line.strip() and ("error" in err_line.lower() or "ffmpeg" in err_line.lower()):
                        callback(f"[Reintento ERROR] {err_line.strip()}")
            
            return proc_retry.returncode == 0
        
        return proc.returncode == 0
        
    except FileNotFoundError as e:
        raise FileNotFoundError(str(e) if "ffmpeg" in str(e) or "ffprobe" in str(e) 
                               else f"yt-dlp not found. Is it installed and in PATH?")
    except Exception as e:
        raise Exception(f"Download failed: {e}")
