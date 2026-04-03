@echo off
REM YTClipper Automatic Dependency Installer
REM Script that detects and installs missing dependencies for YTClipper
REM Requires Admin privileges

setlocal enabledelayedexpansion

REM Check if running as Administrator
net session >nul 2>nul
if errorlevel 1 (
    echo.
    echo === ERROR: Administrator privileges required ===
    echo Please right-click install.bat and select "Run as Administrator"
    echo.
    pause
    exit /b 1
)

cls
echo.
echo ====================================
echo YTClipper - Automatic Setup
echo ====================================
echo.

REM Detect and install yt-dlp
echo [1/3] Checking yt-dlp...
where yt-dlp >nul 2>nul
if errorlevel 1 (
    echo        ⏳ Installing yt-dlp...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ProgressPreference='SilentlyContinue'; $url='https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe'; $dest='C:\Windows\System32\yt-dlp.exe'; try { Invoke-WebRequest -Uri $url -OutFile $dest -ErrorAction Stop; Write-Host '        ✓ yt-dlp installed' } catch { Write-Host '        ✗ Failed to install yt-dlp'; exit 1 }"
    if errorlevel 1 (
        echo        ✗ Failed to install yt-dlp. Check your internet connection.
    )
) else (
    echo        ✓ yt-dlp already installed
)

REM Detect and install ffmpeg + ffprobe
echo.
echo [2/3] Checking ffmpeg and ffprobe...
where ffmpeg >nul 2>nul
set has_ffmpeg=!errorlevel!
where ffprobe >nul 2>nul
set has_ffprobe=!errorlevel!

if !has_ffmpeg! equ 0 if !has_ffprobe! equ 0 (
    echo        ✓ ffmpeg and ffprobe already installed
) else (
    echo        ⏳ Installing ffmpeg and ffprobe...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ProgressPreference='SilentlyContinue'; $url='https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'; $zip='$env:temp\ffmpeg.zip'; $extract='$env:temp\ffmpeg-extract'; try { Invoke-WebRequest -Uri $url -OutFile $zip -ErrorAction Stop; Expand-Archive -Path $zip -DestinationPath $extract -Force; Get-ChildItem -Path $extract -Filter 'ffmpeg.exe' -Recurse | Copy-Item -Destination 'C:\Windows\System32\' -Force; Get-ChildItem -Path $extract -Filter 'ffprobe.exe' -Recurse | Copy-Item -Destination 'C:\Windows\System32\' -Force; Remove-Item -Recurse -Force $extract, $zip -ErrorAction SilentlyContinue; Write-Host '        ✓ ffmpeg and ffprobe installed' } catch { Write-Host '        ✗ Failed to install ffmpeg'; exit 1 }"
    if errorlevel 1 (
        echo        ✗ Failed to install ffmpeg. Check your internet connection.
    ) else (
        REM Verify both are present
        if exist "C:\Windows\System32\ffmpeg.exe" (
            echo        ✓ ffmpeg.exe verified in System32
        ) else (
            echo        ✗ ffmpeg.exe not found after installation
        )
        if exist "C:\Windows\System32\ffprobe.exe" (
            echo        ✓ ffprobe.exe verified in System32
        ) else (
            echo        ✗ ffprobe.exe not found after installation
        )
    )
)

REM Detect and install VLC
echo.
echo [3/3] Checking VLC...
where vlc >nul 2>nul
if errorlevel 1 (
    echo        ⏳ Installing VLC...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ProgressPreference='SilentlyContinue'; $url='https://get.videolan.org/vlc/3.0.21/win64/vlc-3.0.21-win64.exe'; $installer='$env:temp\vlc-installer.exe'; try { Invoke-WebRequest -Uri $url -OutFile $installer -ErrorAction Stop; Start-Process -FilePath $installer -ArgumentList '/L=1033 /S' -Wait -WindowStyle Hidden; Remove-Item $installer -Force -ErrorAction SilentlyContinue; Write-Host '        ✓ VLC installed' } catch { Write-Host '        ✗ Failed to install VLC'; exit 1 }"
    if errorlevel 1 (
        echo        ✗ Failed to install VLC. Check your internet connection.
    )
) else (
    echo        ✓ VLC already installed
)

REM Refresh PATH for current session
echo.
echo [4/4] Refreshing system PATH...
setx PATH "%PATH%"
if errorlevel 1 (
    echo        ✓ PATH refreshed
) else (
    echo        ✓ PATH refreshed
)

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
    echo Please make sure YTClipper.exe is in the same folder as install.bat
    echo.
    pause
)
