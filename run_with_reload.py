import subprocess
import time
import os
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.start_app()
    
    def start_app(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
        print("\n🔄 Reiniciando aplicación...\n")
        self.process = subprocess.Popen(
            [sys.executable, "ytclipper.py"],
            cwd=self.app_dir
        )
    
    def on_modified(self, event):
        if event.src_path.endswith(".py"):
            time.sleep(0.5)
            self.start_app()

if __name__ == "__main__":
    handler = ChangeHandler()
    observer = Observer()
    # Watch all files under project recursively, no solo ytclipper.py
    observer.schedule(handler, ".", recursive=True)
    observer.start()
    try:
        observer.join()
    except KeyboardInterrupt:
        observer.stop()
        if handler.process:
            handler.process.terminate()
