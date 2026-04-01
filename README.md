# YTClipper — Build Instructions
## Prerequisites

### 1. Python 3.10 or higher
Download from https://www.python.org/downloads/
> ⚠️ During installation, check **"Add Python to PATH"**

Verify it works by opening CMD and running:
```
python --version
```

---

### 2. yt-dlp (YouTube downloader)
Download the executable from:  
https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe

Copy it to a folder in your PATH, for example:
```
C:\Windows\System32\yt-dlp.exe
```
Or add the folder where you placed it to your system PATH.

Verify:
```
yt-dlp --version
```

---

### 3. ffmpeg (video processor)
Download the "essentials" version from:  
https://www.gyan.dev/ffmpeg/builds/  
→ Download `ffmpeg-release-essentials.zip`

Extract and copy `ffmpeg.exe`, `ffprobe.exe`, `ffplay.exe` to:
```
C:\Windows\System32\
```
Or add the `bin\` folder to your system PATH.

Verify:
```
ffmpeg -version
```

---

## Set up the project

### 4. Install Python dependencies
Open CMD **in the project folder** (where `ytclipper.py` is located) and run:

```cmd
pip install -r requirements.txt
```

---

## Build the .exe

### 5. Build with PyInstaller (simple option, single .exe)
```cmd
pyinstaller ytclipper.spec
```

The executable will be in:
```
dist\YTClipper.exe
```

> May take 1–3 minutes. When done, you'll see the `dist\` folder.

---

### 6. Alternative build (without .spec, one command)
If the .spec causes issues, use this command directly:

```cmd
pyinstaller --onefile --windowed --name YTClipper ^
  --collect-all customtkinter ^
  ytclipper.py
```

---

## Test before building

If you want to test the app without building:
```cmd
python ytclipper.py
```
or in real time:
```cmd
python run_with_reload.py
```

---

## Distribution

The file `dist\YTClipper.exe` is **self-contained** (includes Python and libraries).

However, the target PC needs to have **yt-dlp**, **ffmpeg**, and **VLC** installed and in PATH,
as they are external tools that the app calls by name.

### Automatic Installation (recommended for end users)

1. Copy `dist\YTClipper.exe` and `install.bat` to the same folder
2. End user runs `install.bat` (as Administrator)
3. It will automatically:
   - ✓ Detect if yt-dlp, ffmpeg, and VLC are already installed
   - ✓ Skip installation if they exist
   - ✓ Download and install missing dependencies
   - ✓ Launch YTClipper when done

**To distribute:** Create a ZIP with:
```
YTClipper-Setup.zip
├── YTClipper.exe
├── install.bat
└── README.txt (instructions)
```

### Manual Distribution (alternative)

If you prefer to include all tools in the package:

1. Download offline:
   - `yt-dlp.exe` from https://github.com/yt-dlp/yt-dlp/releases
   - `ffmpeg.exe` and `ffprobe.exe` from https://www.gyan.dev/ffmpeg/builds/
   - `vlc-installer.exe` from https://get.videolan.org/vlc/

2. Include everything in the ZIP:
   ```
   YTClipper-Complete.zip
   ├── YTClipper.exe
   ├── yt-dlp.exe
   ├── ffmpeg.exe
   ├── ffprobe.exe
   ├── vlc-installer.exe
   └── install-local.bat
   ```

---

## Common Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError: customtkinter` | `pip install customtkinter` |
| `yt-dlp: command not found` | yt-dlp.exe is not in PATH |
| `ffmpeg: command not found` | ffmpeg.exe is not in PATH |
| Antivirus blocks the .exe | Add exception; PyInstaller .exe files trigger false positives |
| .exe won't open (DLL error) | Install [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) |
| Black screen when opening | Make sure to build with `--windowed` or `console=False` in the .spec |

---

## Project Structure

```
ytclipper/
├── ytclipper.py        ← main source code
├── ytclipper.spec      ← PyInstaller configuration
├── requirements.txt    ← Python dependencies
└── README.md           ← this file
```
