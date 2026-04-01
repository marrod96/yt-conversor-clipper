"""
ffmpeg integration for video processing and trimming
"""
import subprocess


def trim_video(input_path: str, output_path: str, start_time: str, end_time: str,
               callback=None, cancel_flag=None) -> bool:
    """Trim video using ffmpeg.
    
    Args:
        input_path: Path to input video
        output_path: Path to output video
        start_time: Start time (mm:ss or hh:mm:ss)
        end_time: End time (mm:ss or hh:mm:ss)
        callback: Function to call with progress updates
        cancel_flag: threading.Event to check for cancellation
    
    Returns:
        bool: True if successful, False otherwise
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ss", start_time,
        "-to", end_time,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)

        for line in proc.stdout:
            if cancel_flag and cancel_flag.is_set():
                proc.terminate()
                return False
            
            if callback:
                callback(line.strip())

        proc.wait()
        return proc.returncode == 0

    except FileNotFoundError:
        raise FileNotFoundError("ffmpeg not found. Is it installed and in PATH?")
    except Exception as e:
        raise Exception(f"Trim failed: {e}")


def convert_audio(input_path: str, output_path: str, audio_format: str,
                  callback=None) -> bool:
    """Convert audio using ffmpeg.
    
    Args:
        input_path: Path to input file
        output_path: Path to output audio
        audio_format: Audio format (mp3, m4a, etc.)
        callback: Function to call with progress updates
    
    Returns:
        bool: True if successful, False otherwise
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-q:a", "0",
        output_path
    ]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)

        for line in proc.stdout:
            if callback:
                callback(line.strip())

        proc.wait()
        return proc.returncode == 0

    except FileNotFoundError:
        raise FileNotFoundError("ffmpeg not found. Is it installed and in PATH?")
    except Exception as e:
        raise Exception(f"Conversion failed: {e}")
