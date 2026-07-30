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
4. Arrastra a la caja de archivos el `SistemaPAE.exe` que acabas de compilar,
   desde `dist/SistemaPAE.exe`. **El nombre debe quedar exactamente
   `SistemaPAE.exe`** — si tiene otro nombre, el programa no lo reconoce.
5. Clic en **"Publish release"**.

**No hace falta subir `updater.exe`** al Release — ya viaja dentro de cada
instalación desde la versión 0.6.0 y es lo que hace el reemplazo del lado
del usuario.

## Listo

A partir de aquí, cualquier instalación 0.6.0 o más nueva va a detectar la
versión publicada la próxima vez que alguien inicie sesión, y va a ofrecer
actualizarse sola.
