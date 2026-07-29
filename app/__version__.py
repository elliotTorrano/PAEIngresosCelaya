"""Versionado semántico del programa (independiente del control de versiones del código)."""

__version__ = "0.4.1"

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
}
