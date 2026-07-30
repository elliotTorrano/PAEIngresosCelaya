# Historial de versiones — Sistema PAE

## 0.9.0

- **Nuevo: código de respaldo para Súper-usuario y Administrador.** Al
  generar su certificado (la primera vez, o al reenrolar después de
  perderlo) se muestra -- una sola vez -- un código de respaldo que debe
  guardarse en un lugar seguro y distinto de la computadora. Si en el
  futuro se pierde o daña el certificado, ese código permite recuperar el
  acceso de inmediato desde la propia pantalla de login ("¿Perdió o dañó
  su certificado? Recuperar con código de respaldo"), sin depender de que
  otra persona apruebe nada. Sólo se guarda el hash del código, nunca el
  código en sí; cada vez que se emite un certificado nuevo el código
  anterior queda invalidado.
- Para las cuentas que ya tenían certificado antes de esta versión, se
  agregó un botón "Generar nuevo código de respaldo" en "Datos de
  cuenta" (pide confirmar con el certificado actual, igual que cambiar
  usuario/nombre/correo).
- **Corrección**: si el propio Administrador perdía su certificado, el
  botón "Olvidé mi contraseña o certificado" enviaba la solicitud a...
  el correo del Administrador -- la misma cuenta bloqueada, sin nadie que
  pudiera atenderla. Ahora, cuando quien solicita es el Administrador, la
  solicitud se dirige al Súper-usuario (que ya puede resolverla desde
  "Solicitudes de reset"); para los demás roles no cambia nada. Este
  flujo por archivo queda como respaldo adicional si además se pierde el
  código de respaldo.

## 0.8.0

- **Corrección de bug en el login**: las tres pantallas del login (usuario,
  contraseña, certificado) llamaban cada una `setDefault()` en su propio
  botón, pero Qt sólo permite UN botón "default" activo por ventana --
  presionar Enter en cualquier pantalla podía disparar además, en segundo
  plano, la acción de la pantalla que hubiera quedado "default" al final
  (a veces mostrando un aviso invisible que dejaba todo bloqueado, otras
  veces mandando directo a "Olvidé mi contraseña" sin haberlo pedido). Se
  quitaron esas llamadas -- cada campo ya dispara su acción con Enter y
  cada botón con clic, sin necesitarlas.
- **Dos eventos separados en la captura del Abogado**: se agregaron las
  columnas "Fecha de citatorio" y "Recibe citatorio" (con su nombre si
  aplica), distintas de "Fecha de notificación" y "Quién recibe" que ya
  existían -- son dos momentos distintos del mismo trámite.
- El archivo que el Agente del PAE exporta para el Abogado ahora se llama
  `LISTA DEL {fecha} {nombre del Abogado}.xlsx`.
- **Nuevo: revisión del Agente**. En la pantalla del Agente del PAE, un
  botón "Importar captura del Abogado" lee el Excel que el Abogado
  exportó y agrega cada fila a una tabla donde el Agente marca PROCEDE o
  NO PROCEDE; esa tabla se puede exportar aparte (queda lista para la
  futura fase de Reportes).
- **Nuevo menú "Histórico"** para Agente del PAE y Abogado: lista, sólo
  para ellos mismos, los archivos que han cargado en esta computadora,
  con fecha/hora y quién fue la otra parte (Agente o Abogado según
  corresponda).
- La exportación final del Abogado agrega `ENTREGA {fecha}` al nombre del
  archivo, y antes de exportar pregunta si se quiere enviar por correo al
  Agente del lote (usando el mismo mecanismo de Outlook/mailto que ya
  existía) o sólo exportarlo.

## 0.7.1

- **Pestañas de Formato cerrables**: las pestañas abiertas desde el menú
  "Formato" (Requerimientos/Mandamientos) para Agente del PAE y Abogado ya
  se pueden cerrar con la "x"; se pueden volver a abrir después desde el
  mismo menú. Las pestañas fijas (Bienvenida, y las de Administrador/Súper)
  no tienen botón de cerrar.
- **"Datos de cuenta" se movió a un menú nuevo llamado "Otros"** (Agente del
  PAE y Abogado): ya no ocupa una pestaña fija; se abre bajo demanda desde
  ese menú, igual que "Formato".
- **Nuevo menú "Ver como" (sólo Súper-usuario)**: permite elegir cualquier
  Agente del PAE o Abogado dado de alta y ver su pantalla dentro de una
  pestaña nueva ("Viendo como: ..."), en **modo simulación** -- se puede
  navegar, seleccionar archivos y probar la captura, pero absolutamente
  nada de lo que se haga ahí se guarda en la base de datos ni se exporta a
  disco. Sólo los cambios hechos directamente en las pestañas propias del
  Súper-usuario tienen efecto real.
- **Login: botón "Regresar"** en las pantallas de contraseña y certificado,
  para volver a escribir el usuario sin cerrar la ventana de inicio de
  sesión.
- **Corrección adicional al redimensionado de la ventana principal**: la
  hoja de estilos (QSS) ya no se aplica directamente sobre la QMainWindow,
  sino sobre su contenido interno -- aplicar un stylesheet directamente a
  una QMainWindow es una causa conocida de comportamientos raros del marco
  nativo de la ventana en Windows, y es la explicación más probable de que
  sólo se pudiera ajustar el ancho y no el alto tras la corrección de la
  0.7.0.

## 0.7.0

- **Pantalla de Bienvenida**: al iniciar sesión, cualquier rol ve ahora una
  primera pestaña "Bienvenida" con la imagen de fondo configurada en
  Apariencia, mostrada completa y centrada, sin deformarse.
- **Corrección de la imagen de fondo**: antes se estiraba para llenar la
  ventana sin respetar su proporción (`border-image` de Qt); ahora un
  widget propio la escala manteniendo el aspecto original, tanto en el
  fondo general de la ventana como en la pestaña de Bienvenida.
- **Cajas y pestañas más legibles sobre el fondo**: las cajas de "Datos de
  cuenta" y el área de las pestañas ya no son casi transparentes -- tienen
  un fondo blanco semi-opaco para que el texto no se pierda contra la
  imagen.
- **Navegación por menú para Agente del PAE y Abogado**: ya no ven la
  pestaña de "Formato de Requerimientos" abierta todo el tiempo; ahora se
  accede desde un nuevo menú "Formato" (con "Formato de Requerimientos" y
  "Mandamientos", éste último sigue pendiente para una fase futura), que
  la muestra dentro de la misma ventana. Administrador y Súper-usuario no
  cambian: conservan sus pestañas de siempre.
- **Datos de cuenta para Agente del PAE y Abogado**: nueva pestaña
  simplificada donde pueden ver su usuario y nombre, y actualizar
  únicamente su correo electrónico (sin necesidad de certificado).
- **Trazabilidad**: se agregó un botón "Cerrar archivo" para limpiar la
  base de datos importada que se estaba revisando.
- **Corrección**: la ventana principal no se podía redimensionar
  libremente a lo alto después de iniciar sesión (causado por la forma en
  que se aplicaba la imagen de fondo); ya se puede ajustar en cualquier
  dirección.

## 0.6.0

- **Autoactualización desde GitHub**: justo después de iniciar sesión (cualquier
  rol), el programa consulta en segundo plano si hay una versión más nueva
  publicada en el repositorio público de GitHub (`elliotTorrano/PAEIngresosCelaya`).
  Si la hay, pregunta si se quiere instalar; de aceptar, la descarga y se
  reemplaza sola, apoyándose en un ayudante externo (`updater.exe`, incluido
  junto a `SistemaPAE.exe`) que hace el reemplazo del archivo una vez que el
  programa principal ya se cerró, y lo vuelve a abrir automáticamente.
- **Si no hay internet, o la consulta a GitHub falla por cualquier motivo**
  (sin red, tiempo de espera agotado, GitHub no responde, etc.), no aparece
  ningún aviso ni se interrumpe nada: el inicio de sesión sigue exactamente
  igual que siempre. Sólo se avisa con un mensaje de error si el usuario ya
  aceptó instalar y la descarga se corta a medias.
- **Requisitos para publicar una versión nueva en GitHub** (para quien vaya a
  hacerlo): crear un release con tag `vX.Y.Z` (o `X.Y.Z`) y adjuntar el
  ejecutable con el nombre exacto `SistemaPAE.exe` — cualquier otro nombre no
  se reconoce. `updater.exe` **no** se sube al release: ya viaja dentro de
  cada carpeta distribuida (se genera junto con `SistemaPAE.exe` al compilar)
  y es lo que ejecuta el reemplazo del lado del usuario.
- **Aviso importante de arranque único**: las instalaciones en cualquier
  versión anterior a la 0.6.0 no tienen `updater.exe` todavía, así que no
  pueden autoactualizarse la primera vez (el programa simplemente no revisa
  nada, porque el código de autoactualización no existe en esas versiones).
  Ese primer salto a la 0.6.0 debe hacerse una vez de forma manual, copiando
  la carpeta más reciente como hasta ahora; de ahí en adelante, la
  autoactualización funciona sola.

## 0.5.1

- **Corrección importante de integridad de datos**: la base usaba el modo WAL
  de SQLite, que guarda los cambios más recientes en archivos adicionales
  (`pae.db-wal`, `pae.db-shm`) separados de `pae.db`. Como este programa se
  distribuye copiando la carpeta `data/` a mano entre computadoras, copiar
  sólo `pae.db` -- o copiar mientras el programa seguía abierto -- podía
  producir una copia con cuentas, contraseñas o certificados desactualizados,
  causando errores de "contraseña incorrecta" para todas las cuentas en la
  máquina destino aunque las credenciales fueran correctas.
  Ahora se usa el modo DELETE (el predeterminado de SQLite): `pae.db` es
  siempre el único archivo con la verdad completa en cuanto termina cada
  operación. Las bases ya creadas en modo WAL se convierten automáticamente
  la primera vez que se abren con esta versión.
- Corregido un problema en las pruebas automatizadas del proyecto que dejaba
  archivos de prueba sueltos dentro de la carpeta del programa.

**Si ya tuviste el problema de "contraseña incorrecta" en una computadora
nueva**: vuelve a copiar la carpeta `data/` completa desde el equipo
original (con el programa ya cerrado ahí) hacia la computadora nueva,
sobrescribiendo lo que haya, y esta vez sí debería quedar consistente.

## 0.5.0

- **Soporte para archivos .xls antiguos**: el Agente del PAE ya puede importar
  archivos de Excel en el formato binario viejo (.xls), además de .xlsx/.xlsm.
  Internamente se usa `xlrd` para leer .xls y `openpyxl` para .xlsx/.xlsm; la
  regla de negocio (omitir las primeras 2 filas y la última, columnas B/C/D/F)
  es la misma para ambos.
- **Histórico permanente de archivos subidos**: cada archivo que el Agente del
  PAE selecciona (con filas válidas) queda registrado de inmediato en
  `imported_files` -- quién lo subió, cuándo y cuántas filas trajo -- sin
  ninguna restricción de repetición. El mismo archivo puede volver a subirse
  el mes siguiente, o para corregir algo, sin ningún bloqueo.
- **El aviso de "archivo duplicado" cambió de alcance**: antes comparaba
  contra todo el histórico de ese Agente; ahora sólo avisa si el nombre se
  repite dentro de la selección actual o ya se había agregado al lote que se
  está preparando en ese momento para el Abogado (antes de exportarlo). Al
  exportar, esos registros del histórico quedan enlazados al lote exportado.

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
