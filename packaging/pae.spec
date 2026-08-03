# PyInstaller spec — build con: pyinstaller packaging/pae.spec
# Este comando produce DOS ejecutables: dist/SistemaPAE.exe y dist/updater.exe
# (este último hace el reemplazo cuando el programa se autoactualiza desde
# GitHub Releases). Ambos deben copiarse juntos -- y junto con la carpeta
# "data" que el programa crea junto a sí mismo la primera vez que corre -- al
# distribuir o actualizar una instalación.

import os

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

# reportlab.graphics.barcode.__init__ importa sus submódulos (code128, qr,
# etc.) dinámicamente por nombre -- el análisis estático de PyInstaller no
# los detecta, así que hay que declararlos a mano o el .exe truena con
# "ModuleNotFoundError: No module named 'reportlab.graphics.barcode.code128'"
# en cuanto se use el widget QR (ver CHANGELOG v0.21.1).
reportlab_barcode_submodules = collect_submodules("reportlab.graphics.barcode")

# numpy: nunca se importa en app/ -- se cuela porque Pillow lo detecta como
# dependencia opcional y, en la máquina donde se compila, suele estar
# instalado por otras herramientas (aquí, unas pruebas de QR con opencv
# ajenas al programa). QtQml/QtQuick/QtQuickWidgets/QtQuick3D/QtPdf/
# QtPdfWidgets: este programa es QtWidgets clásico -- ninguna pantalla usa
# QML, y los PDF se generan con reportlab, nunca se renderizan con Qt.
EXCLUDED_MODULES = [
    "numpy",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQuick3D",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
]

a = Analysis(
    [os.path.join(PROJECT_ROOT, "app", "main.py")],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, "resources"), "resources"),
        (os.path.join(PROJECT_ROOT, "app", "db", "schema.sql"), os.path.join("app", "db")),
    ],
    hiddenimports=reportlab_barcode_submodules,
    hookspath=[],
    runtime_hooks=[],
    excludes=EXCLUDED_MODULES,
    cipher=block_cipher,
    noarchive=False,
)

# Aun excluyendo los módulos de arriba, dos plugins de Qt siguen arrastrando
# sus DLL de QML/Quick/Pdf porque el propio hook de Qt de PyInstaller los
# agrega por compatibilidad general, sin importar qué se use en el código:
# el plugin de teclado virtual táctil (platforminputcontexts) y el plugin
# que permite abrir un PDF como si fuera una imagen (imageformats/qpdf.dll).
# Ninguno de los dos aplica aquí (teclado físico de escritorio, PDF sólo
# generado -- nunca abierto -- por el programa), así que se filtran del
# listado final de binarios. Verificado con un análisis de dependencias
# binarias (pefile) que ninguna otra DLL que sí se usa (Qt6Core/Gui/
# Widgets/Network, ni los plugins de platforms/imageformats restantes)
# depende de ellas.
_QT_UNUSED_BINARY_DIRS = (
    os.path.normcase(os.path.join("pyside6", "plugins", "platforminputcontexts")),
)
_QT_UNUSED_BINARY_NAMES = {
    "qt6qml.dll", "qt6quick.dll", "qt6qmlmodels.dll", "qt6qmlworkerscript.dll",
    "qt6qmlmeta.dll", "qt6virtualkeyboard.dll", "qt6pdf.dll", "qpdf.dll",
}
a.binaries = [
    entry for entry in a.binaries
    if not os.path.normcase(entry[0]).startswith(_QT_UNUSED_BINARY_DIRS)
    and os.path.basename(os.path.normcase(entry[0])) not in _QT_UNUSED_BINARY_NAMES
]

# Traducciones de Qt (~100 archivos .qm, uno por idioma): el programa nunca
# instala un QTranslator -- todo el texto está escrito directamente en
# español en el código -- así que ninguno hace falta.
a.datas = [
    entry for entry in a.datas
    if os.path.normcase(os.path.join("pyside6", "translations")) not in os.path.normcase(entry[0])
]

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
