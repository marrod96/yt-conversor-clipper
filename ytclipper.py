#!/usr/bin/env python3
"""
YT Clipper — YouTube video downloader and clip extractor

Requires: customtkinter, pillow, requests, yt-dlp, ffmpeg (in PATH)

Main entry point for the application.
The core functionality has been modularized for better maintainability.
"""
from core.app import App


if __name__ == "__main__":
    app = App()
    app.mainloop()