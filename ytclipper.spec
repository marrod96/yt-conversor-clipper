# ytclipper.spec
# Compile with:  pyinstaller ytclipper.spec

import sys
from pathlib import Path

block_cipher = None

# Collect customtkinter assets (themes, images)
import customtkinter
CTK_PATH = Path(customtkinter.__file__).parent

a = Analysis(
    ['ytclipper.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        (str(CTK_PATH), 'customtkinter'),  # include ctk themes/images
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageDraw',
        'PIL.ImageFilter',
        'requests',
        'urllib.request',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='YTClipper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # ← no black terminal window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',      # ← uncomment and add icon.ico if you want one
)
