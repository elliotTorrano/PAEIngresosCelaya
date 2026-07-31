# Estado actual del proyecto (para retomar en otra máquina)

> Generado: 2026-07-31. Este archivo es un resumen de contexto para arrancar
> una sesión nueva de Claude Code rápido, no un changelog formal (ese es
> [CHANGELOG.md](CHANGELOG.md)).

## Versión actual: 0.20.0

Código, `.exe`, `updater.exe` e instalador ya están en esa versión.
Working tree limpio, todo confirmado y **empujado a `origin/main`**
(https://github.com/elliotTorrano/PAEIngresosCelaya). En la otra máquina
basta con `git pull`.

## Lo que se construyó en las últimas sesiones (más reciente primero)

- **v0.20.0 — Menú "Seguimiento" (sólo Agente del PAE)**: dashboard con 4
  estados (GENERADOS / EN REVISIÓN / PENDIENTES DE ENVIAR COMO REPORTE /
  REPORTES ENVIADOS) que cruza los flujos de Generar y Revisar Formato.
  Columnas: Archivo, Abogado, Cargado, Estatus cambiado. Doble clic o botón
  de acción por estado:
  - GENERADOS → confirmar y volver a exportar (certificado + elegir
    carpeta y nombre con `QFileDialog.getSaveFileName`).
  - EN REVISIÓN → salta a "Revisar Formato Requerimiento" con ese archivo
    cargado.
  - PENDIENTES DE ENVIAR COMO REPORTE → **deliberadamente sin programar**
    (muestra "Próximamente"). El usuario pidió explícitamente no
    implementarlo todavía ("se necesita más planeación para esta fase").
  - REPORTES ENVIADOS → por lo tanto queda siempre vacío hasta que se
    construya esa fase.
  - Pestaña "Mandamiento (Próximamente)" ya preparada, sin contenido.
  - Archivos clave: `app/ui/agente/seguimiento_view.py` (nuevo),
    `app/db/repositories/requerimientos.py::list_batches_for_agente`,
    `app/db/repositories/revisiones.py` (constantes `STATUS_*`,
    `_sync_import_status`), `app/ui/main_window.py`
    (`_build_seguimiento_menu`, `_show_seguimiento_tab`,
    `_on_continuar_revision_solicitada`).

- **v0.19.0 — Fix de concatenación en Revisar Formato**: cada archivo
  importado por el Agente ahora es su propio evento (`revision_imports`
  con `revision_import_id` en `revision_rows`), en vez de mezclarse todo
  lo importado por un Agente en una sola tabla. Se agregó el patrón
  Pendiente/Revisado (combo + lista + Abrir/Limpiar) como mecanismo para
  verificar qué ya se revisó y qué no.

- **v0.18.0 / v0.18.1 — Reestructura de menús y vistas**:
  - Vista combinada del Agente dividida en dos independientes:
    `RequerimientosGenerarView` y `RequerimientosRevisionView`.
  - Menú "Formato" con submenús anidados: Generar Formato → Requerimiento
    / Mandamiento (Próximamente); Revisar Formato → Requerimiento /
    Mandamiento (Próximamente). Títulos de pestaña incluyen el tipo de
    documento ("Generar Formato Requerimiento", etc.).
  - Vista del Abogado: pestañas Pendientes/Exportados/Finalizados
    reemplazadas por combo + lista + Abrir/Limpiar (mismo patrón que se
    reutilizó después en Revisar Formato y Seguimiento).

- **v0.17.0 — Búsqueda y bloqueo por exportación**: botones de búsqueda
  por FOLIO/CTA PREDIAL/CONTRIBUYENTE en captura del Abogado y revisión
  del Agente, con salto directo a la fila. Lotes exportados por el
  Abogado se bloquean automáticamente; desbloquear pide confirmación con
  advertencia.

## Lección arquitectónica importante (no repetir el error)

`app/db/migrations.py::ensure_schema()` corre `schema.sql` completo
(vía `executescript`) **antes** de revisar `schema_version` o correr
migraciones. Si `schema.sql` tiene un `CREATE INDEX` que referencia una
columna que una migración posterior agrega con `ALTER TABLE`, una base de
datos existente (pre-migración) truena, porque el `CREATE TABLE IF NOT
EXISTS` no hace nada en una tabla ya existente y esa columna todavía no
existe cuando corre el índice.

**Regla**: si una migración agrega una columna a una tabla que ya existía
en una versión anterior del esquema, el índice/constraint sobre esa
columna nueva va **sólo** dentro de la lista de sentencias de la
migración, nunca en `schema.sql` como `CREATE INDEX` suelto.

## Patrones establecidos (reutilizar, no reinventar)

- **Tabla cabecera/detalle**: `requerimiento_batches`+`requerimiento_rows`,
  replicado en `revision_imports`+`revision_rows`.
- **Combo + lista + Abrir/Limpiar**: UI reutilizada en Abogado
  (Pendiente/Exportado/Finalizado), Revisar Formato
  (Pendiente/Revisado) y Seguimiento (4 estados).
- **Rebuild seguro del `.exe`** (nunca toca `dist/data` ni
  `dist/certificados`):
  ```bash
  rm -rf build dist_new && python -m PyInstaller --distpath dist_new packaging/pae.spec && cp dist_new/SistemaPAE.exe dist/SistemaPAE.exe && cp dist_new/updater.exe dist/updater.exe && rm -rf dist_new build
  ```
  Luego el instalador con Inno Setup (`ISCC.exe packaging\installer.iss`
  desde `packaging/`). Ver [PUBLICAR_NUEVA_VERSION.md](PUBLICAR_NUEVA_VERSION.md)
  para el flujo completo de publicación.

## Pendiente / diferido a propósito

- **Exportación como reporte** (Excel) para
  PENDIENTES DE ENVIAR COMO REPORTE → REPORTES ENVIADOS: el usuario pidió
  explícitamente no construirlo todavía, falta planear esa fase. No hay
  ninguna función de "marcar como reportado" en el código (se escribió y
  se borró por no tener quién la llamara).
- **Mandamiento** (Generar y Revisar): sólo hay pestañas placeholder,
  nada de lógica real. Preparado para cuando se desarrolle.
- No hay ninguna otra tarea abierta reportada por el usuario al cierre de
  la v0.20.0.

## Cómo arrancar en la otra máquina

```bash
git pull
python -m pytest tests/ -q   # línea base: 244 pasando
```

Si hace falta reconstruir el `.exe`, usar el comando de rebuild de arriba
y luego `ISCC.exe` para el instalador — pero sólo si de verdad se va a
distribuir una nueva versión, no hace falta para seguir programando.
