# Cómo publicar una nueva versión del Sistema PAE

Guía de referencia rápida para cuando se haga un cambio al programa y haya
que sacar una versión nueva. Sigue estos pasos en orden.

## 1. Hacer los cambios de código

(Con ayuda de Claude Code, o directamente.) Cuando estén listos, sigue con
el resto de los pasos.

## 2. Subir el número de versión (3 archivos)

- **`app/__version__.py`**: cambia `__version__ = "X.Y.Z"` al número nuevo,
  y agrega una entrada nueva en `VERSION_NOTES` describiendo el cambio.
- **`packaging/version_info.txt`**: cambia `filevers`/`prodvers` y los dos
  `StringStruct(u'FileVersion', ...)` / `StringStruct(u'ProductVersion', ...)`
  al mismo número.
- **`packaging/installer.iss`**: cambia `#define MyAppVersion "X.Y.Z"` al
  mismo número (no afecta la autoactualización, sólo el número que ve quien
  instala por primera vez).
- **`CHANGELOG.md`**: agrega una sección `## X.Y.Z` arriba de todo,
  explicando qué cambió (mismo estilo que las secciones anteriores).

## 3. Correr las pruebas

```bash
python -m pytest tests/ -q
```

Todas deben pasar antes de continuar.

## 4. Compilar el .exe (sin tocar los datos reales)

Este patrón compila a una carpeta aparte (`dist_new`) y sólo copia los dos
ejecutables nuevos a `dist/` — así nunca se toca `dist/data` (la base de
datos real) ni `dist/certificados`:

```bash
rm -rf build dist_new
python -m PyInstaller --distpath dist_new packaging/pae.spec
cp dist_new/SistemaPAE.exe dist/SistemaPAE.exe
cp dist_new/updater.exe dist/updater.exe
rm -rf dist_new build
```

Antes de compilar, asegúrate de que `SistemaPAE.exe` no esté abierto en esta
computadora (si lo está, ciérralo primero).

### 4.1 Compilar el instalador para instalaciones nuevas (SistemaPAE_Setup.exe)

Alguien que **nunca** ha tenido el programa y sólo descarga `SistemaPAE.exe`
suelto de GitHub corre el riesgo de que la interfaz cargue sin texto/fondos
si a esa computadora le falta el Redistribuible de Visual C++ de Microsoft
(muy común en una Windows recién instalada; en la computadora de desarrollo
casi siempre ya está, por eso no se nota aquí). El instalador
`SistemaPAE_Setup.exe` (hecho con [Inno Setup](https://jrsoftware.org/isinfo.php),
`packaging/installer.iss`) revisa e instala ese Redistribuible automáticamente
si hace falta, y deja accesos directos en el Menú Inicio/Escritorio. Se
instala en la carpeta del usuario (no pide permisos de administrador) porque
el programa necesita poder escribir su propia `data\` junto al `.exe`.

Requiere tener [Inno Setup](https://jrsoftware.org/isdl.php) instalado una
vez en esta computadora (`winget install --id JRSoftware.InnoSetup -e`).
Compilar:

```powershell
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" "packaging\installer.iss"
```

Esto genera `dist\SistemaPAE_Setup.exe`. **No cambiar el `AppId` dentro de
`installer.iss`** entre versiones -- es lo que permite reinstalar/actualizar
en el mismo lugar sin duplicar accesos directos.

`packaging/installer/vc_redist.x64.exe` (el Redistribuible que se empaqueta
dentro del instalador, ~25 MB) **no se versiona** en git -- se descarga una
sola vez por computadora de compilación (o de nuevo si Microsoft publica una
versión más reciente):

```powershell
Invoke-WebRequest -Uri "https://aka.ms/vs/17/release/vc_redist.x64.exe" -OutFile "packaging\installer\vc_redist.x64.exe"
```

Alternativa más simple (sin instalador, modo portable/USB) -- sigue
sirviendo para quien prefiera sólo copiar una carpeta, pero no corrige el
problema de la interfaz en blanco si falta el Redistribuible:

```powershell
Compress-Archive -Path "dist\SistemaPAE.exe","dist\updater.exe" -DestinationPath "dist\SistemaPAE.zip" -Force
```

Si `SistemaPAE.exe` está abierto en esta computadora, `Compress-Archive`
puede fallar con "el proceso no puede tener acceso al archivo" aunque
`tasklist` no muestre el proceso corriendo (puede ser un antivirus
escaneándolo un momento) — si pasa, ciérralo, espera unos segundos y
reintenta.

## 5. Subir el código a GitHub

Con GitHub Desktop (repositorio: esta misma carpeta,
`C:\Users\Usuario\Documents\ejec\PAE\program`):

1. Verás los archivos modificados en la pestaña "Changes".
2. Escribe un resumen del cambio (por ejemplo `vX.Y.Z: descripción breve`).
3. Clic en **"Commit to main"**.
4. Clic en **"Push origin"**.

## 6. Publicar el Release en GitHub (esto es lo que activa la autoactualización)

En el navegador, en `https://github.com/elliotTorrano/PAEIngresosCelaya`:

1. Ve a **"Releases"** → **"Draft a new release"** (o "Create a new release").
2. En **"Choose a tag"**, escribe `vX.Y.Z` (el mismo número que usaste en el
   paso 2) y elige "Create new tag ... on publish".
3. En **"Release title"** pon `vX.Y.Z`.
4. Arrastra a la caja de archivos **tres** cosas: `dist/SistemaPAE.exe` (el
   nombre debe quedar exactamente **`SistemaPAE.exe`** — si tiene otro
   nombre, el programa no lo reconoce para autoactualizarse),
   `dist/SistemaPAE_Setup.exe` (el paso 4.1 de arriba — instalador
   recomendado para quien instale por primera vez) y, opcionalmente,
   `dist/SistemaPAE.zip` (modo portable, sin instalador).
5. Clic en **"Publish release"**.

**`updater.exe` suelto no se sube** al Release — va dentro del instalador y
del .zip. Ya viaja dentro de cada instalación desde la versión 0.6.0 y es lo
que hace el reemplazo del lado del usuario; el mecanismo de autoactualización
sólo usa el `SistemaPAE.exe` suelto, nunca el instalador ni el .zip.

### A quién mandarle qué

- **Alguien que YA tiene el programa instalado (0.6.0+)**: no le mandes
  nada — se actualiza solo la próxima vez que inicie sesión.
- **Alguien nuevo, sin el programa todavía**: mándale el vínculo del
  Release y dile que descargue **`SistemaPAE_Setup.exe`** y lo ejecute (no
  el `SistemaPAE.exe` suelto, y tampoco los "Source code (zip/tar.gz)" que
  GitHub agrega solo — ésos son el código fuente, no sirven para instalar).
  El instalador deja accesos directos y evita el problema de la interfaz en
  blanco por falta del Redistribuible de Visual C++.

## Listo

A partir de aquí, cualquier instalación 0.6.0 o más nueva va a detectar la
versión publicada la próxima vez que alguien inicie sesión, y va a ofrecer
actualizarse sola.
