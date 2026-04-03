@echo off
REM YTClipper Local Installation (offline mode)
REM Use this script when all dependencies are included in the same folder
REM Requires Admin privileges

setlocal enabledelayedexpansion

REM Check if running as Administrator
net session >nul 2>nul
if errorlevel 1 (
    echo.
    echo === ERROR: Administrator privileges required ===
    echo Please right-click install-local.bat and select "Run as Administrator"
    echo.
    pause
    exit /b 1
)

cls
echo.
echo ====================================
echo YTClipper - Local Setup (Offline)
echo ====================================
echo.

REM Check if dependencies exist in current folder
if not exist "yt-dlp.exe" (
    echo ✗ yt-dlp.exe not found in this folder
    goto error
)
if not exist "ffmpeg.exe" (
    echo ✗ ffmpeg.exe not found in this folder
    goto error
)
if not exist "ffprobe.exe" (
    echo ✗ ffprobe.exe not found in this folder
    goto error
)
if not exist "vlc-installer.exe" (
    echo ✗ vlc-installer.exe not found in this folder
    goto error
)

REM Install yt-dlp
echo [1/4] Installing yt-dlp...
where yt-dlp >nul 2>nul
if errorlevel 1 (
    copy "yt-dlp.exe" "C:\Windows\System32\" >nul 2>nul
    if errorlevel 1 (
        echo ✗ Failed to copy yt-dlp.exe
        goto error
    )
    echo        ✓ yt-dlp installed
) else (
    echo        ✓ yt-dlp already installed
)

REM Install ffmpeg and ffprobe
echo.
echo [2/4] Installing ffmpeg and ffprobe...
where ffmpeg >nul 2>nul
set has_ffmpeg=!errorlevel!
where ffprobe >nul 2>nul
set has_ffprobe=!errorlevel!

if !has_ffmpeg! equ 0 if !has_ffprobe! equ 0 (
    echo        ✓ ffmpeg and ffprobe already installed
) else (
    echo        ⏳ Copying ffmpeg.exe and ffprobe.exe...
    copy "ffmpeg.exe" "C:\Windows\System32\" >nul 2>nul
    if errorlevel 1 (
        echo ✗ Failed to copy ffmpeg.exe
        goto error
    )
    copy "ffprobe.exe" "C:\Windows\System32\" >nul 2>nul
    if errorlevel 1 (
        echo ✗ Failed to copy ffprobe.exe
        goto error
    )
    echo        ✓ ffmpeg and ffprobe installed
    
    REM Verify both files exist
    if exist "C:\Windows\System32\ffmpeg.exe" (
        echo        ✓ ffmpeg.exe verified in System32
    ) else (
        echo        ✗ ffmpeg.exe verification failed
        goto error
    )
    if exist "C:\Windows\System32\ffprobe.exe" (
        echo        ✓ ffprobe.exe verified in System32
    ) else (
        echo        ✗ ffprobe.exe verification failed
        goto error
    )
)

REM Install VLC
echo.
echo [3/4] Installing VLC...
where vlc >nul 2>nul
if errorlevel 1 (
    echo        ⏳ Running VLC installer (this may take a minute)...
    start /wait "vlc-installer.exe" /L=1033 /S
    echo        ✓ VLC installed
) else (
    echo        ✓ VLC already installed
)

REM Refresh PATH
echo.
echo [4/4] Refreshing system PATH...
setx PATH "%PATH%"
echo        ✓ PATH refreshed

echo.
echo ====================================
echo ✓ Setup complete!
echo ====================================
echo.
echo Launching YTClipper in 2 seconds...
timeout /t 2 /nobreak >nul

if exist "YTClipper.exe" (
    start "" "YTClipper.exe"
) else (
    echo.
    echo ✗ Warning: YTClipper.exe not found in this directory
    echo.
    pause
)
exit /b 0

:error
echo.
echo ====================================
echo ✗ Error: Missing required files
echo ====================================
echo.
echo This folder must contain:
echo  - yt-dlp.exe
echo  - ffmpeg.exe
echo  - ffprobe.exe
echo  - vlc-installer.exe
echo  - YTClipper.exe
echo.
pause
exit /b 1
