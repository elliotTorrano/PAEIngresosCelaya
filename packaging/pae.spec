# PyInstaller spec — build con: pyinstaller packaging/pae.spec
# El .exe resultante queda en dist/SistemaPAE.exe; cópiese junto con la carpeta
# "data" que el programa crea junto a sí mismo la primera vez que corre.

import os

block_cipher = None
PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(PROJECT_ROOT, "app", "main.py")],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, "resources"), "resources"),
        (os.path.join(PROJECT_ROOT, "app", "db", "schema.sql"), os.path.join("app", "db")),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
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
    name="SistemaPAE",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=os.path.join(PROJECT_ROOT, "resources", "default_icon.ico"),
    version=os.path.join(PROJECT_ROOT, "packaging", "version_info.txt"),
)
