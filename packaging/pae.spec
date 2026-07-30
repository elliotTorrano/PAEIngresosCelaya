# PyInstaller spec — build con: pyinstaller packaging/pae.spec
# Este comando produce DOS ejecutables: dist/SistemaPAE.exe y dist/updater.exe
# (este último hace el reemplazo cuando el programa se autoactualiza desde
# GitHub Releases). Ambos deben copiarse juntos -- y junto con la carpeta
# "data" que el programa crea junto a sí mismo la primera vez que corre -- al
# distribuir o actualizar una instalación.

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

# --- updater.exe: ayudante mínimo que reemplaza SistemaPAE.exe al autoactualizar ---
# Sin PySide6/paquete app (Analysis independiente) y sin ícono/version_info
# propios: es un binario invisible que el usuario nunca abre a mano.
a2 = Analysis(
    [os.path.join(PROJECT_ROOT, "packaging", "updater", "main.py")],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz2 = PYZ(a2.pure, a2.zipped_data, cipher=block_cipher)

updater_exe = EXE(
    pyz2,
    a2.scripts,
    a2.binaries,
    a2.zipfiles,
    a2.datas,
    [],
    name="updater",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
)
