# Historial de versiones — Sistema PAE

## 0.4.1

- **Corrección de bug**: al importar Excel como Agente del PAE, si un archivo
  no producía filas (por ejemplo un archivo de prueba sin la fila final de
  totales que el formato real siempre trae) o no se podía leer (formato
  inválido, o un `.xls` antiguo que la librería de lectura no soporta), el
  programa no mostraba nada — parecía que el botón no hacía nada. Ahora
  siempre aparece un aviso explicando qué archivo falló y por qué.

## 0.4.0

- **Respaldo automático antes de migrar el esquema**: cuando una nueva versión
  del programa necesita cambiar la estructura de la base (como el
  `must_change_password` de la 0.2.0), antes de aplicar el cambio se copia
  `pae.db` a `pae.db.bak-vN` (N = la versión anterior). Así, actualizar el
  `.exe` nunca pone en riesgo los datos ya capturados: sólo se reemplaza el
  archivo del programa, `data/` se queda intacta y, si algo saliera mal, el
  respaldo previo a la migración sigue ahí.
- **Nueva pestaña "Trazabilidad"** (sólo Administrador y súper-usuario): permite
  importar, en modo de sólo lectura, el archivo `pae.db` de otra computadora
  (de un Agente del PAE o un Abogado) para revisar qué se importó y capturó,
  cuándo y por quién — sin fusionarlo ni modificar la base propia. Usa las
  columnas de trazabilidad que ya existían en `imported_files`
  (`imported_at`, `agente_id`, `abogado_id`).
- Se corrigió que el import del Abogado (cuando carga el archivo del Agente
  del PAE) no quedaba registrado en `imported_files` — sólo se registraba el
  import del lado del Agente. Ahora ambos eventos quedan trazados con fecha,
  hora, agente y abogado.

## 0.3.0

- El súper-usuario y el Administrador tienen ahora sus datos reales de
  identidad sembrados (antes traían valores de ejemplo "CAMBIAR_...").
- Los datos de identidad (usuario, nombre completo, correo) del Administrador
  pueden cambiarse desde el menú del súper-usuario o del propio Administrador
  ("Datos de cuenta"); los del súper-usuario, sólo desde su propio menú. En
  ambos casos se exige confirmar primero con el certificado .pfx ACTUAL de la
  cuenta afectada, y el cambio obliga a generar un certificado nuevo en el
  siguiente inicio de sesión de esa cuenta.
- `resources/seed_accounts.enc` reemplaza al `seed_accounts.json` en texto
  plano: el nombre/correo reales del súper-usuario y del Administrador viajan
  cifrados dentro del `.exe`, para que no queden a la vista si alguien
  extrae los recursos empaquetados. La clave vive en el propio binario (ver
  `app/auth/seed_crypto.py`), así que esto es una barrera contra la lectura
  casual, no un secreto criptográficamente inviolable frente a un atacante
  dispuesto a decompilar el ejecutable.
- Nueva herramienta de desarrollo `packaging/generate_seed.py` para regenerar
  ese archivo cifrado cuando cambien los datos por defecto antes de compilar
  una nueva distribución.

## 0.2.0

- El Súper-usuario y el Administrador ya no se crean con un asistente interactivo:
  se siembran automáticamente y en silencio desde `resources/seed_accounts.json`
  la primera vez que faltan en la base de datos local. Como ese archivo se
  empaqueta con el programa, la cuenta creada es siempre la misma sin importar
  en qué máquina o cuántas veces se ejecute el `.exe` — nunca se vuelve a pedir.
  **Antes de generar el `.exe` para distribuir, edítese ese archivo con los
  datos reales.**
- El Abogado debe cambiar su contraseña obligatoriamente la primera vez que
  inicia sesión (o después de que el Administrador le asigna una nueva por un
  reset), mediante un diálogo que no se puede omitir.
- En las pantallas de login (usuario, contraseña y certificado) la tecla Enter
  ahora dispara el botón "Iniciar sesión"/"Continuar" correspondiente.

## 0.1.0

Primera fase del programa:

- Login con 3 niveles de rol (Súper-usuario, Administrador, Agente del PAE, Abogado).
- Certificado digital autofirmado (.pfx) para Súper-usuario/Administrador/Agentes; usuario y contraseña para Abogados.
- Asistente de primer arranque: crea al único Súper-usuario y al primer (único) Administrador.
- Recuperación de acceso por archivo de solicitud + correo al Administrador, y paquete de actualización de credenciales para aplicar en la instalación del solicitante.
- Gestión de Agentes del PAE y Abogados por el Administrador.
- Apariencia personalizable (ícono de ventana y fondo) por el Administrador.
- Formato de Requerimientos completo:
  - Agente del PAE: selección de abogado, carga de Excel con aviso de duplicados por nombre de archivo, conteo acumulado de filas, vista previa y exportación.
  - Abogado: importación del archivo del Agente (sin poder modificar sus datos), captura de "Fecha de Notificación de citatorio" y "Quién recibe el citatorio" (con mayúsculas automáticas), botón para resaltar la primera fila pendiente de captura, y exportación final.
- Formato de Mandamientos y los Reportes de Requerimientos/Mandamientos quedan como fase pendiente.
