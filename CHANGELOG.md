# Historial de versiones — Sistema PAE

## 0.30.0

- Nuevo botón **"Abrir ubicación del archivo"** en el menú **"Histórico"**
  (Agente del PAE y Abogado, pestañas Requerimiento y Mandamiento):
  seleccionando una fila de un archivo cargado, abre el Explorador de
  Windows en la carpeta donde estaba ese archivo al momento de importarlo,
  con el archivo ya seleccionado.
- Se guarda ahora la **ruta completa** de cada archivo cargado (antes sólo
  se guardaba el nombre) -- migración de base de datos v12
  (`imported_files.original_path` / `mandamiento_imported_files.original_path`).
  Los registros anteriores a esta versión quedan sin ruta (no se puede
  reconstruir después del hecho): al intentar abrir su ubicación, se avisa
  que no se registró.
- Si el archivo ya no está en esa ubicación (se movió o se borró), se
  avisa en vez de fallar.

## 0.29.0

- **"Generar Formato" (Requerimiento y Mandamiento) del Agente del PAE**
  ahora exporta también un **.xlsx de respaldo**, además del .mcdiep y el
  PDF que ya generaba -- mismos datos, en un formato universal abrible con
  cualquier hoja de cálculo.
- Es una medida adicional de control de archivos: si el .mcdiep se daña,
  se pierde, o algo falla en el programa, el .xlsx conserva un respaldo
  legible de exactamente lo que se exportó. No reemplaza al .mcdiep -- el
  Abogado lo sigue necesitando para importar dentro del programa; el .xlsx
  es sólo respaldo/control, no se abre desde Sistema PAE.
- La exportación de "Revisar Formato" (`export_revision`) ya era un .xlsx
  por sí sola desde antes -- no necesitó cambios.
- Las exportaciones de prueba de `agente_dummy` no llevan este respaldo
  (siguen siendo sólo .mcdiep + PDF de una página, sin datos reales que
  proteger).

## 0.28.0

- **"Generar Formato" (Requerimiento y Mandamiento) para `agente_dummy`**
  ahora genera un archivo real (.mcdiep + PDF), en vez de simularlo por
  completo:
  - Sin certificado ni firma digital (la cuenta de prueba no tiene
    certificado).
  - Acotado a una sola página -- máximo 8 filas por exportación de prueba.
  - El UUID y el Hash muestran literalmente **"USUARIO PRUEBA"** en vez de
    calcularse de verdad -- no hay generación real de UUID, hash ni QR.
  - Marca de agua diagonal semi-transparente **"PAE PRUEBA - {nombre del
    agente}"** repetida en toda la hoja.
  - Sigue sin guardar nada en la base de datos: el archivo generado es sólo
    para revisar visualmente el formato, no queda ningún registro asociado.
- "Revisar Formato" (Agente) y la captura del `abogado_dummy` siguen en
  modo simulación completa, sin generar ningún archivo real -- esa parte
  del flujo no cambió en esta versión.

## 0.27.0

- Nuevas **cuentas de prueba** para el piloto alpha con usuarios finales:
  `agente_dummy` (rol Agente del PAE) y `abogado_dummy` (rol Abogado), ambas
  con contraseña `dummy12345`. Se crean solas en cualquier instalación al
  arrancar el programa -- igual que el súper-usuario/Administrador -- sin
  necesitar que nadie las dé de alta a mano.
- Con estas cuentas se puede probar el flujo completo de Generar/Revisar
  formato y Capturar (Requerimientos y Mandamientos), pero **nada de lo que
  se haga con ellas se guarda**: corren siempre en modo simulación (el mismo
  mecanismo que ya usaba "Ver como" para el Súper-usuario), y el título de
  la ventana avisa "CUENTA DE PRUEBA, NADA SE GUARDA" mientras están
  activas.
- Tampoco se puede cambiar su correo, contraseña ni certificado desde
  "Datos de cuenta" (queda reemplazado por un aviso), ni guardar cambios de
  color desde "Colores" (para `agente_dummy`) -- así la cuenta compartida
  sigue siendo utilizable indefinidamente con la misma contraseña conocida,
  sin importar cuántas personas la usen para probar.

## 0.26.0

- El **Agente del PAE** ya tiene acceso propio a "Colores" desde el menú
  "Otros": puede personalizar los colores de SU interfaz (menús, botones,
  pestañas) con "Restaurar predeterminados", "Aplicar (vista previa)" y
  "Guardar cambios de interfaz" -- igual que Administrador/Súper-usuario,
  pero **sin** el botón "Guardar cambios del PDF": el color de los PDF
  exportados sigue siendo exclusivo de Administrador/Súper-usuario, porque
  es un documento oficial y debe ser el mismo para todos.
- El **Abogado** sigue sin acceso a "Colores": siempre ve la interfaz con
  los colores que estén guardados en ese momento, sin poder cambiarlos.

## 0.25.0

- En la pestaña "Colores", el botón único **"Guardar como predeterminado"**
  se separó en dos botones independientes, cada uno con su propia
  confirmación:
  - **"Guardar cambios de interfaz"**: deja fijos los colores de pantalla
    (menús, botones, pestañas). No afecta el PDF.
  - **"Guardar cambios del PDF"**: deja fijo el color del encabezado de
    tabla de los PDF exportados (Requerimiento y Mandamiento). No afecta la
    interfaz.
- Motivo: la interfaz puede ajustarse al gusto de quien use el programa en
  esa computadora, pero el PDF es un documento oficial -- su color sólo
  debe cambiar cuando alguien lo decida explícitamente, no como efecto
  colateral de personalizar la pantalla.
- Ambas paletas se guardan por separado en `pae.db` y sobreviven cualquier
  actualización futura del programa, igual que antes.
- Nueva etiqueta en la pestaña "Colores" que muestra el color actualmente
  guardado para el encabezado del PDF.

## 0.24.0

- **Nueva pestaña "Colores"** (Administrador/Súper-usuario), junto a
  "Apariencia": permite personalizar los 3 colores base del programa
  escribiendo el código hexadecimal deseado --
  - **Identidad** (menús, pestañas, botones de uso diario)
  - **Crítico** (Exportar/Firmar, encabezados de tabla y del PDF)
  - **Estructura** (bordes y separadores)
  Cada campo tiene una muestra de color en vivo mientras se escribe.
- **"Aplicar (vista previa)"**: prueba los colores de inmediato en TODAS
  las ventanas abiertas del programa (no sólo la pestaña de Colores), para
  poder revisarlos visualmente antes de decidir nada. No es permanente: si
  no se guardan, se pierden en cuanto se reinicia el programa.
- **"Restaurar predeterminados"**: vuelve en cualquier momento a la
  combinación de fábrica (verde `#3A6B46` / guinda `#8A1E2D` / ocre
  `#A67242`), sin importar qué se haya guardado después.
- **"Guardar como predeterminado"**: pide confirmación explícita
  (advirtiendo que el cambio afecta a todo el programa y no se puede
  deshacer) y deja los colores fijos de forma permanente -- se guardan en
  la base de datos local (`pae.db`), así que sobreviven cualquier
  actualización futura del programa (a diferencia de la hoja de estilos
  de fábrica, que viaja empacada dentro del propio `.exe`).
- El encabezado de tabla del PDF exportado ahora sigue el color "crítico"
  realmente **guardado** -- nunca una vista previa sin confirmar, para que
  un documento oficial jamás lleve un color que sólo se estaba probando.

## 0.23.0

- **Nueva paleta institucional** en toda la interfaz, para los 4 roles:
  - **Verde `#3A6B46`** -- color de uso diario: barras de menú/pestañas,
    pestaña activa, botones secundarios (bordes y texto).
  - **Guinda `#8A1E2D`** -- reservado para lo importante: botones de
    "Exportar" (Generar/Revisar Formato, captura del Abogado), "Confirmar
    identidad" (firma con certificado), "Iniciar sesión", y los
    encabezados de todas las tablas.
  - **Ocre `#A67242`** -- bordes, separadores y fondos suaves de pestañas
    inactivas, grupos y campos.
  - El login y los diálogos (confirmar certificado, cambiar contraseña,
    código de respaldo, enrolamiento, olvidé mi contraseña, importar
    actualización, ver como) ahora tienen estilo propio -- antes no
    heredaban ningún QSS y se veían con la apariencia nativa de Windows.
- **El encabezado de la tabla en el PDF exportado** (Requerimiento y
  Mandamiento) cambia de azul a guinda `#8A1E2D`, para que coincida con
  la pantalla.

## 0.22.0

- **Nuevo módulo de Mandamiento**, completo y en paralelo a Requerimiento --
  ya no es el "(Próximamente)" del menú. Mismo flujo de punta a punta, con
  tablas y pantallas propias para no tocar nada de lo ya existente:
  - **Generar Formato** y **Revisar Formato** del Agente del PAE (submenú
    "Mandamiento", junto al de "Requerimiento").
  - **Formato de Mandamientos** del Abogado (importar, capturar
    citatorio/notificación, finalizar/editar, exportar con o sin correo).
  - **Seguimiento** del Agente: pestaña "Mandamiento" junto a la de
    "Requerimiento", con sus 4 estados (Generados/En revisión/Pendientes de
    reporte/Reportes enviados).
  - **Histórico** (Agente/Abogado) y **Trazabilidad** (Administrador/
    Súper-usuario): ambos ahora muestran Requerimiento y Mandamiento por
    separado.
  - **"Ver como"** del Súper-usuario también simula Mandamiento.
  - Mismo sistema de identidad UUID/hash, firma digital y PDF de
    acompañamiento (QR, sello estilo CFDI, doble cara) que Requerimiento.
  - **Única diferencia real**: el Excel de origen de Mandamiento sólo trae
    FOLIO, CTA PREDIAL y CONTRIBUYENTE (columnas B, C y D) -- no hay
    DOMICILIO, ni en la captura ni en el PDF. El PDF lleva su propio
    encabezado institucional ("FORMATO: ENTREGA DE MANDAMIENTOS DE
    EJECUCIÓN").

## 0.21.2

- **El instalador y el .exe pesan ~20 MB menos** (de ~77 MB a ~56 MB, un
  27% menos), sin cambios de funcionalidad. Se quitó del empaquetado lo
  que nunca se usa en el programa:
  - `numpy` (8.4 MB): no aparece en ningún import de `app/` -- se colaba
    porque Pillow lo detecta como dependencia opcional cuando está
    instalado en la máquina donde se compila.
  - Los módulos de Qt para interfaces QML/táctiles (`QtQml`, `QtQuick`,
    `QtQuick3D`, teclado virtual en pantalla) y el lector de PDF-como-
    imagen de Qt (`QtPdf`): el programa es 100% de escritorio con
    `QtWidgets` clásico y teclado físico, y los PDF se generan con
    reportlab -- nunca se abren dentro del programa. Verificado con un
    análisis de dependencias binarias que ninguna DLL de Qt que sí se usa
    (Core/Gui/Widgets/Network) depende de ellos.
  - Las ~96 traducciones de Qt a otros idiomas (~1.8 MB): el programa
    nunca instala un `QTranslator` -- todo el texto está en español,
    directamente en el código.
  - Verificado con una prueba de extremo a extremo en modo congelado
    (simulando el .exe empacado) que el sello con código QR de los PDF
    generados sigue produciéndose y decodificándose correctamente.

## 0.21.1

- **Corregido: "Generar Formato > Requerimiento" no hacía nada al hacer clic**
  en la versión instalada (.exe). Causa: `reportlab` importa internamente el
  módulo del código de barras/QR (`reportlab.graphics.barcode.code128` y
  hermanos) de forma dinámica, no con un `import` estático visible -- el
  análisis de PyInstaller no lo detectaba y quedaba fuera del paquete. Al
  abrir esa pantalla (que usa el widget QR del sello del PDF), fallaba con
  `ModuleNotFoundError`, y como el `.exe` no tiene consola, el error no se
  veía en ningún lado -- para quien usaba el programa, simplemente "no pasaba
  nada". Ya se declara explícitamente en `packaging/pae.spec` para que se
  incluya siempre.
- **Nuevo manejador global de errores**: cualquier error inesperado que
  ocurra al hacer clic en un botón o menú ahora se guarda en `data/error.log`
  y se muestra un aviso en pantalla con el detalle, en vez de no hacer nada
  visible (que fue justo lo que ocultó el bug anterior).

## 0.21.0

- **Contadores en la captura del Abogado**: "Total de la lista", "Total de
  llenados" y "Faltan por llenarse" (medidos por la columna QUIÉN RECIBE),
  visibles arriba de la tabla y actualizados en tiempo real.
- **Nueva opción "HOJA DE CAMPO"** en los combos Recibe citatorio y Quién
  recibe, junto a EN PUERTA y NOMBRE.
- **Exportación en PDF junto al .mcdiep**, en las tres exportaciones
  (Generar Formato del Agente, captura del Abogado, y "Volver a exportar"
  de Seguimiento): hoja horizontal pensada para imprimirse a doble cara,
  con:
  - Cabecera institucional (Municipio de Celaya, Tesorería, Formato,
    Impuesto Predial, Dirección, Procedimiento, Despacho, fecha), con el
    escudo y, sólo en la exportación del Abogado, los contadores
    Notificado/Instructivo/Hoja de campo además del total de documentos a
    entregar (que en la del Agente es la totalidad de las filas, y en la
    del Abogado sólo las que ya tienen QUIÉN RECIBE lleno).
  - Cuerpo con todas las columnas de la captura ajustadas al ancho de la
    hoja (el texto envuelve dentro de cada celda en vez de recortar
    columnas), repitiendo el encabezado en cada página si el lote es
    grande.
  - Un sello final estilo CFDI del SAT: UUID, hash SHA-256, firma digital
    (cuando la exportación llevó certificado -- el flujo del Agente; el
    del Abogado no, porque se autentica con contraseña), y un código QR
    con UUID/agente/archivo/hash. Ese mismo QR chico (con UUID y hash
    abreviados) también aparece dentro del cuadro de la cabecera en la
    primera página, y al pie izquierdo de las páginas siguientes.
- **UUID y hash quedan embebidos en el propio .mcdiep** y guardados en la
  base de datos de quien exporta (para poder relacionarlos después). Al
  importar -- ya sea el Abogado recibiendo la lista del Agente, o el
  Agente recibiendo la captura del Abogado en "Revisar Formato" -- se
  muestran en pantalla, para comparar visualmente que lo que se está
  revisando en el programa concuerda con el documento físico impreso.
- **Nuevo patrón de nombre sugerido** para los archivos exportados:
  `AGENTE_ABOGADO_{primeros 8 del UUID}_{primeros 10 del hash} fecha`.

## 0.20.1

- **Corrección: instalaciones nuevas se veían sin fondo en las ventanas del
  programa.** Sólo el login trae una imagen fija empacada en el `.exe`; el
  fondo del resto de las ventanas (Bienvenida, Agente, Abogado, etc.)
  siempre dependió de que el Administrador lo configurara manualmente en
  **Otros → Apariencia → "Cambiar imagen de fondo"**, algo que nadie hace
  todavía en una instalación recién estrenada. Ahora, si esa apariencia
  nunca se configuró en la máquina, se usa automáticamente un fondo de
  fábrica (`resources/default_background.png`); si el Administrador ya
  eligió una imagen o un color propio, esa elección se sigue respetando
  sin cambios.

## 0.20.0

- **Nuevo menú "Seguimiento" (Agente del PAE)**: reúne en una sola pantalla
  los documentos en sus 4 etapas:
  - **GENERADOS**: lo que se exportó desde "Generar Formato Requerimiento".
  - **EN REVISIÓN**: capturas del Abogado importadas, todavía sin marcar
    PROCEDE/NO PROCEDE en todas sus filas.
  - **PENDIENTES DE ENVIAR COMO REPORTE**: ya se marcó cada fila, falta
    enviarlo como reporte.
  - **REPORTES ENVIADOS**: ya se envió como reporte.
  
  Cada archivo muestra cuándo se cargó y cuándo cambió de estatus por
  última vez. Con doble clic o el botón de acción: en **GENERADOS**,
  vuelve a exportar el documento (con confirmación, verificación de
  certificado, y eligiendo dónde guardarlo y con qué nombre); en **EN
  REVISIÓN**, lleva directo a "Revisar Formato Requerimiento" con ese
  archivo abierto para continuar la captura. La exportación como reporte
  (que movería PENDIENTES DE ENVIAR → REPORTES ENVIADOS) todavía no está
  disponible -- se necesita más planeación para esa fase; por ahora esa
  pestaña queda preparada pero vacía. También se preparó, sin desarrollar
  todavía, el mismo seguimiento para el futuro Formato de Mandamientos.

## 0.19.0

- **Corregido: "Revisar Formato Requerimiento" concatenaba archivos**. Al
  importar varias capturas del Abogado una tras otra, la tabla mostraba
  TODAS las filas de TODOS los archivos importados alguna vez, mezcladas
  entre sí, en vez de sólo las del archivo recién cargado. Ahora cada
  archivo importado es su propio evento (`revision_imports`), y la tabla
  sólo muestra el que está abierto.
- **Nueva pantalla previa Pendiente/Revisado**: al abrir "Revisar Formato
  Requerimiento" se elige primero si se quieren ver los archivos
  pendientes de marcar PROCEDE/NO PROCEDE en todas sus filas, o los que
  ya se terminaron de revisar; la lista muestra cuántas filas de cada uno
  ya se revisaron. Esto sirve para verificar de un vistazo qué entregas
  del Abogado siguen pendientes. Un botón "Abrir" carga el archivo
  elegido en la tabla y otro "Limpiar" vacía la lista y cierra lo
  abierto. La exportación consolidada ("Exportar revisión") no cambió:
  sigue incluyendo todo lo importado, revisado o no.
- Las bases de datos existentes migran automáticamente: las filas de
  revisión ya guardadas se agrupan por archivo/fecha de importación para
  reconstruir sus `revision_imports` sin perder ningún dato ni el
  PROCEDE/NO PROCEDE ya marcado.

## 0.18.1

- **Menú Formato del Agente del PAE reorganizado en submenús**: en vez de
  dos acciones sueltas, ahora es "Generar Formato" y "Revisar Formato",
  cada uno desplegando "Requerimiento" y "Mandamiento (Próximamente)".
  El Mandamiento todavía no está desarrollado, pero el menú y su pestaña
  ya quedan preparados para cuando se implemente. Las pestañas se
  renombraron a "Generar Formato Requerimiento", "Generar Formato
  Mandamiento", "Revisar Formato Requerimiento" y "Revisar Formato
  Mandamiento" para que coincidan con la ruta del menú que las abrió.

## 0.18.0

- **Menú Formato del Agente del PAE dividido en dos pantallas**: "Generar
  formato" (subir Excel y exportar para el Abogado) y "Revisar formato de
  abogado" (importar la captura y marcar PROCEDE/NO PROCEDE) ya no
  comparten una sola pantalla apilada -- cada una es su propia pestaña,
  para que una no interrumpa visualmente a la otra.
- **Revisar formato de abogado** muestra el nombre del archivo que se
  está revisando, tanto en una etiqueta dentro de la pantalla como en el
  título de su propia pestaña.
- **Vista del Abogado rediseñada**: se quitaron las pestañas Pendientes/
  Exportados/Finalizados. En su lugar hay una pantalla previa con un
  combo para elegir el tipo de documento (Pendiente/Exportado/
  Finalizado); al elegir uno se listan los lotes de ese tipo, un botón
  "Abrir" carga el seleccionado en la tabla de captura y otro "Limpiar"
  vacía la lista y cierra lo que estuviera abierto. Cambiar el tipo
  directamente también vacía la lista mostrada, sin mezclar tipos.

## 0.17.0

- **Buscador de filas (Abogado y Agente)**: nuevo botón "Buscar" en la
  captura del Abogado y en la sección de revisión del Agente, que permite
  elegir el campo (FOLIO, CTA PREDIAL o CONTRIBUYENTE), escribir un texto y
  posicionarse directamente en la fila que coincide, resaltándola
  brevemente. Si no hay coincidencias, avisa que no se encontró nada.
- **Pestañas de lotes para el Abogado**: la lista de lotes ahora se
  organiza en tres pestañas -- Pendientes, Exportados y Finalizados -- y
  cada lote se ubica solo en la que le corresponde según su estado actual,
  sin intervención manual.
- **Bloqueo automático al exportar**: en cuanto el Abogado exporta un lote
  queda bloqueado de inmediato (igual que "Finalizar captura"), para
  evitar ediciones accidentales después de entregado. Para editarlo de
  nuevo se usa "Editar captura", que ahora advierte explícitamente cuando
  el lote ya se había exportado antes -- el archivo ya entregado no se
  actualiza solo, así que hay que volver a exportarlo tras corregir.

## 0.16.1

- **Corregido: texto sin opacidad en la pantalla de login**. Las etiquetas
  de las páginas de usuario, contraseña y certificado no tenían fondo
  opaco, así que el texto se perdía contra las zonas claras del escudo de
  fondo. Ahora tienen el mismo fondo blanco semi-opaco que ya tenía el
  mensaje de bienvenida.

## 0.16.0

- **Nueva pantalla de login**: fondo con el escudo del Municipio de Celaya
  (ajustado al tamaño de la ventana en cada momento, preservando la
  proporción -- no se deforma ni usa el tamaño real de la imagen) y mensaje
  de bienvenida: "Bienvenido/a al Sistema de Control del Proceso
  Administrativo de Ejecución del Municipio de Celaya, Gto." seguido de
  "Por favor, ingrese su usuario y posteriormente su certificado."
- **Títulos de ventana unificados**: las 10 ventanas del programa (login,
  ventana principal, enrolamiento, cambio de contraseña, código de
  respaldo, confirmar identidad, etc.) ahora siguen el mismo formato:
  "{nombre de la ventana} - SICPAE v#.##.##".
- **Corregido: FOLIO numérico con ".0" al importar**. Cuando el Excel de
  origen guarda el FOLIO como número (no como texto), Excel/openpyxl lo
  entregan como decimal (p. ej. 1234.0); ahora se importa como "1234".

## 0.15.0

- **Seguridad: mensaje unificado al fallar la verificación de un
  certificado** (login y confirmación de identidad antes de operaciones
  sensibles como exportar). Antes, probar un .pfx que NO es el de la cuenta
  con la contraseña correcta mostraba "Este certificado no corresponde a
  este usuario", mientras que una contraseña incorrecta mostraba "El
  archivo o la contraseña no son correctos" -- esa diferencia le permitía a
  quien prueba un certificado ajeno confirmar si acertó su contraseña,
  aunque no le sirviera para entrar a esa cuenta. Ahora ambos casos (y
  cualquier otro motivo de rechazo) muestran siempre el mismo mensaje
  genérico.

## 0.14.0

- **Corregido: Enter dejaba de funcionar en el login tras "Regresar"**. Si se
  cancelaba la selección del certificado y se presionaba "Regresar" para
  escribir otro usuario, Enter no disparaba nada (el clic en "Continuar" sí
  funcionaba) -- el foco del campo de usuario no se recuperaba a tiempo tras
  cerrar el diálogo nativo de archivo. Se difiere el `setFocus()` para que se
  aplique después de que esos eventos terminen de procesarse.
- **Agente: lista visible de Excel del lote + confirmación antes de
  exportar**. Ahora se muestra qué archivos están cargados en el lote actual.
  Antes de exportar (LISTA DEL...) se pide confirmar con esa misma lista; si
  se rechaza, no se exporta nada y lo ya cargado se conserva.
- **Confirmación al sobrescribir un archivo existente**: tanto la
  exportación del Agente como la del Abogado avisan si ya existe un archivo
  con el mismo nombre en la carpeta elegida, y piden confirmar antes de
  reemplazarlo.
- **Revisión de captura del Abogado**: se agrega y muestra, en la columna
  más a la derecha, el ID del Abogado al que pertenece cada fila importada
  (además del nombre, que ya se mostraba).
- **Columnas redimensionables** en las tablas de importación y revisión del
  Agente -- antes el ancho era fijo (Stretch) y no se podía ajustar
  arrastrando el borde.
- **Optimización de tablas grandes**: el refresco de las tablas de
  importación/revisión del Agente y de captura del Abogado ya no reconstruye
  fila por fila con `insertRow()` -- se preasigna el tamaño y se desactivan
  los repintados intermedios, notablemente más rápido con lotes grandes.

## 0.13.0

- **Corregidas las fechas/horas mal mostradas**: la base de datos guarda
  los timestamps en UTC (`datetime('now')` de SQLite); las pantallas que
  los mostraban lo hacían tal cual, en formato `aaaa-mm-dd` y sin
  convertir a la hora local del equipo. Se agregó
  `app/utils/dates.py::format_local_datetime`, que convierte a hora local
  y formatea `dd/mm/aaaa hh:mm`. Aplicado en Histórico (Agente/Abogado),
  Trazabilidad (Súper/Administrador), solicitudes de reset y la lista de
  lotes del Abogado.
- **Nuevo: "Finalizar captura" / "Editar captura" (Abogado)**. Al
  terminar de capturar un lote, el Abogado puede marcarlo como
  finalizado: queda guardado y sus filas se bloquean (no se pueden
  modificar por accidente). El botón "Editar captura" aparece sólo
  cuando el lote está finalizado y lo desbloquea de nuevo. La lista de
  lotes muestra "FINALIZADO" junto a los que ya están en ese estado.
- **La exportación del Abogado ahora sólo incluye las filas que
  capturó**: las filas que quedaron exactamente como se importaron (sin
  ningún dato de citatorio o notificación) ya no se incluyen en el
  archivo exportado para el Agente del PAE.

## 0.12.1

- **Nuevo: la exportación (Agente y Abogado) ahora deja elegir la carpeta
  de destino** en vez de guardar siempre en la carpeta interna del
  programa -- útil para guardar directo en una USB o en una carpeta
  específica. Si se cancela la selección de carpeta, no se crea el lote
  ni se guarda nada, igual que al cancelar cualquier otro paso del
  proceso.
- Se confirmó (con pruebas nuevas) que la verificación del certificado al
  exportar como Agente rechaza correctamente tanto una contraseña
  incorrecta como un certificado válido de otra cuenta -- y que en
  cualquiera de los dos casos no se llega a crear el lote ni a pedir la
  carpeta de destino. También se confirmó que el Abogado no tiene ningún
  diálogo de archivo que permita seleccionar un Excel: sólo `.mcdiep`.

## 0.12.0

- **Nuevo formato propio `.mcdiep`** para el intercambio de Requerimientos
  entre Agente del PAE y Abogado, en reemplazo del Excel (`.xlsx`) que se
  usaba antes en ambos sentidos:
  - Es un contenedor binario, no un Excel -- no se puede abrir ni editar a
    mano con Excel ni con un editor de texto; cualquier alteración rompe
    el archivo o invalida su firma.
  - **La exportación del Agente para el Abogado (`LISTA DEL...`) ahora se
    firma con el certificado del Agente** (se pide confirmar identidad con
    el `.pfx` + contraseña al exportar) **y queda atada a un Abogado
    específico** -- el destinatario elegido en el combo. Al importarla, el
    Abogado ya no elige manualmente "de qué Agente es": el programa lo
    determina de forma verificable a partir de la firma, muestra quién
    firmó, y **si la firma no es válida o el archivo fue firmado para otro
    Abogado, se niega a abrirlo**.
  - La exportación del Abogado para el Agente (`requerimientos_capturado_
    lote... ENTREGA...`) también pasa a `.mcdiep` -- no editable a mano --
    aunque sin firma (el Abogado se autentica con contraseña, no tiene
    certificado).
  - La revisión del Agente (PROCEDE/NO PROCEDE) sigue siendo un Excel
    normal: es un documento de trabajo interno, no el intercambio formal
    entre las dos partes.

## 0.11.0

- **Corrección**: la revisión de actualizaciones ahora corre ANTES de
  mostrar la pantalla de login (no después de iniciar sesión). Así, si hay
  una versión nueva, se ofrece instalarla de una vez -- nadie llega a
  autenticarse (ni, para el súper-usuario/Administrador, a generar un
  certificado) contra una versión ya desactualizada.
- **Nuevo: instalador `SistemaPAE_Setup.exe`** (con Inno Setup,
  `packaging/installer.iss`) para quien instala por primera vez. En una
  Windows recién instalada, descomprimir sólo el `.exe` podía dejar la
  interfaz sin texto ni fondos por faltar el Redistribuible de Visual C++
  de Microsoft -- el instalador lo revisa e instala automáticamente si
  hace falta, y deja accesos directos en Menú Inicio/Escritorio. Se
  instala en la carpeta del usuario, sin pedir permisos de administrador
  (el programa necesita poder escribir su propia base de datos junto al
  `.exe`). El `.zip` sigue disponible como alternativa portable.
- **Nuevo: certificado "maestro" del súper-usuario.** Con
  `packaging/generate_super_master_cert.py` (herramienta de quien publica
  el programa, se corre una sola vez en su propia terminal) se puede
  generar un certificado fijo que queda reconocido desde el primer
  arranque en cualquier instalación nueva -- el súper-usuario ya no
  necesita enrolar un certificado distinto en cada máquina; llega con el
  mismo `.pfx` a cualquier lado. El Administrador no cambia: sigue
  generando su propio certificado, distinto en cada máquina.

## 0.10.1

- El Súper-usuario (y el propio Administrador) ahora ven también los datos
  del Administrador en la pantalla "Usuarios", junto a Agentes del PAE y
  Abogados (usuario, nombre, correo, activo). Es sólo de consulta: sigue
  siendo una cuenta única, sembrada automáticamente -- no se da de alta
  desde ahí, y sus datos de identidad/certificado se siguen cambiando
  desde "Datos de cuenta".

## 0.10.0

- **Corrección**: al cambiar el nombre de usuario (o cualquier dato de
  identidad) del Administrador o del Súper-usuario, el certificado .pfx
  anterior se quedaba huérfano en la carpeta donde se había guardado (con
  el nombre de usuario viejo, ya inútil). Ahora el programa recuerda dónde
  se guardó el certificado vigente de cada cuenta y, al generarse uno
  nuevo -- por el motivo que sea -- borra automáticamente el archivo
  anterior de esa ubicación (si sigue ahí; si ya no está, o no se puede
  borrar, simplemente se ignora sin interrumpir el proceso). Sólo aplica
  hacia adelante: certificados ya huérfanos de antes de esta versión no
  se detectan retroactivamente y deben borrarse a mano.
- **Nuevo botón "Generar después"** en la pantalla de generar certificado:
  si en ese momento no se quiere generar uno (primer inicio de sesión, o
  después de recuperar el acceso), se puede posponer -- el programa cierra
  la sesión de inmediato en vez de quedar a medias.
- **Nuevo: cada rol con certificado puede renovar el suyo cuando quiera**,
  sin depender de nadie más. Súper-usuario y Administrador ya lo tenían
  implícito al cambiar sus datos; ahora hay un botón directo "Generar
  nuevo certificado" en Datos de cuenta que no obliga a cambiar
  usuario/nombre/correo. El Agente del PAE gana el mismo botón en su
  pantalla de Datos de cuenta.
- **Nuevo: el Abogado puede cambiar su propia contraseña** desde Datos de
  cuenta (pide la contraseña actual para confirmar, además de la nueva).

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
