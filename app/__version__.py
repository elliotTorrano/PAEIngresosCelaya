"""Versionado semántico del programa (independiente del control de versiones del código)."""

__version__ = "0.9.0"

# Historial resumido — el detalle completo vive en CHANGELOG.md
VERSION_NOTES = {
    "0.1.0": "Primera fase: login por certificado/contraseña, gestión de usuarios, "
              "y flujo completo de Formato de Requerimientos (Agente del PAE y Abogado).",
    "0.2.0": "Súper-usuario y Administrador se siembran automáticamente (una sola vez, "
              "sin importar la máquina); cambio de contraseña obligatorio para el Abogado "
              "en su primer inicio de sesión o tras un reset; tecla Enter vinculada al "
              "botón 'Iniciar sesión' en las pantallas de login.",
    "0.3.0": "Los datos de identidad (usuario/nombre/correo) del Administrador y del "
              "súper-usuario ya pueden cambiarse desde el programa, siempre confirmando "
              "con el certificado ACTUAL de la cuenta afectada; el cambio obliga a generar "
              "un certificado nuevo. El archivo de sembrado del súper-usuario/Administrador "
              "ahora viaja cifrado dentro del .exe.",
    "0.4.0": "Respaldo automático de pae.db antes de cualquier migración de esquema; "
              "nueva pestaña 'Trazabilidad' (sólo Administrador/súper-usuario) para "
              "importar en modo sólo lectura el pae.db de otra máquina y revisar qué se "
              "importó/capturó, cuándo y por quién; se corrigió que el import del Abogado "
              "no quedaba registrado en el historial de archivos importados.",
    "0.4.1": "Corrección: el Agente del PAE ya no importa en silencio. Si un archivo "
              "no tiene filas de datos (p. ej. porque no tiene fila final de totales) "
              "o no se pudo leer (formato inválido/.xls antiguo), ahora se muestra un "
              "aviso claro en vez de no hacer nada.",
    "0.5.0": "El Agente del PAE ya puede importar archivos .xls antiguos, además de "
              ".xlsx. Cada archivo subido queda registrado de inmediato en el histórico "
              "(quién, cuándo, cuántas filas), sin límite de repeticiones -- el aviso de "
              "'archivo duplicado' ahora sólo aplica dentro del lote que se está "
              "preparando en ese momento para el Abogado, nunca contra el histórico completo.",
    "0.5.1": "Corrección importante: la base de datos usaba el modo WAL de SQLite, "
              "que guarda cambios recientes en archivos adicionales (pae.db-wal, "
              "pae.db-shm) aparte de pae.db. Como el programa se distribuye copiando "
              "la carpeta data/ a mano entre computadoras, copiar sólo pae.db (o "
              "copiar mientras el programa seguía abierto) podía dejar una copia "
              "con cuentas/contraseñas desactualizadas -- pae.db ahora es siempre "
              "el único archivo con la verdad completa (modo DELETE); las bases ya "
              "creadas se convierten automáticamente la primera vez que se abren "
              "con esta versión.",
    "0.6.0": "El programa ahora revisa, justo después de cada inicio de sesión, si hay "
              "una versión más nueva publicada en GitHub; si la hay, pregunta si se "
              "quiere instalar y, de aceptar, la descarga y se reemplaza sola "
              "(usando un ayudante updater.exe incluido junto al programa). Si no hay "
              "internet o algo falla en la consulta, no aparece ningún aviso y el "
              "programa sigue igual que siempre. Las instalaciones anteriores a la "
              "0.6.0 no tienen ese ayudante todavía, así que este primer salto debe "
              "hacerse una vez de forma manual, como antes.",
    "0.7.0": "Nueva pestaña 'Bienvenida' al iniciar sesión (para todos los roles), con la "
              "imagen de Apariencia mostrada completa y sin deformarse (antes se estiraba "
              "sin respetar proporción). Cajas y pestañas ahora tienen un fondo semi-opaco "
              "para que el texto no se pierda contra la imagen de fondo. El Agente del PAE "
              "y el Abogado ya no ven la pestaña de Requerimientos siempre abierta: se "
              "accede desde un nuevo menú 'Formato', y ambos ganan una pestaña simplificada "
              "de 'Datos de cuenta' para actualizar su correo. En Trazabilidad se agregó un "
              "botón para cerrar el archivo que se está revisando. Se corrigió que la "
              "ventana principal no se pudiera redimensionar libremente a lo alto tras "
              "iniciar sesión.",
    "0.7.1": "Las pestañas de Formato de Requerimientos/Mandamientos (Agente del PAE y "
              "Abogado) ya se pueden cerrar. 'Datos de cuenta' se movió de pestaña fija a "
              "un nuevo menú 'Otros'. Nuevo menú 'Ver como' para el Súper-usuario: elige un "
              "Agente del PAE o Abogado y ve su pantalla en modo simulación, sin guardar "
              "nada de lo que haga ahí. En el login se agregó un botón 'Regresar' para "
              "volver a escribir el usuario. Corrección adicional al redimensionado: la "
              "hoja de estilos ya no se aplica directamente sobre la ventana principal "
              "(causa más probable de que sólo se pudiera ajustar a lo ancho).",
    "0.8.0": "Corregido un bug de arranque en el login (Enter disparaba, en segundo "
              "plano, la acción de una página oculta -- por eso a veces mandaba a "
              "'Olvidé mi contraseña' sin haberlo pedido). El Abogado captura ahora dos "
              "eventos separados: Fecha/Recibe de CITATORIO y Fecha/Quién recibe de "
              "NOTIFICACIÓN. El archivo que el Agente exporta para el Abogado se llama "
              "'LISTA DEL {fecha} {abogado}'. Nuevo: el Agente puede importar la captura "
              "que el Abogado exportó y marcar PROCEDE/NO PROCEDE por fila, con su propia "
              "exportación. Nuevo menú 'Histórico' (Agente y Abogado) con los archivos que "
              "han cargado. La exportación del Abogado agrega 'ENTREGA {fecha}' al nombre "
              "y ofrece enviarla por correo al Agente del lote, o sólo exportarla.",
    "0.9.0": "Nuevo código de respaldo para Súper-usuario y Administrador: se muestra una "
              "sola vez al generar el certificado y permite recuperar el acceso de "
              "inmediato desde el login si se pierde o daña el certificado, sin depender "
              "de la aprobación de nadie más. Las cuentas ya existentes pueden generar uno "
              "desde 'Datos de cuenta'. Corregido además que la solicitud de 'Olvidé mi "
              "contraseña o certificado' del propio Administrador se dirigía a sí mismo "
              "(ahora se dirige al Súper-usuario, como respaldo adicional).",
}
