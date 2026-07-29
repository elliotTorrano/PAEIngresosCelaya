"""Versionado semántico del programa (independiente del control de versiones del código)."""

__version__ = "0.2.0"

# Historial resumido — el detalle completo vive en CHANGELOG.md
VERSION_NOTES = {
    "0.1.0": "Primera fase: login por certificado/contraseña, gestión de usuarios, "
              "y flujo completo de Formato de Requerimientos (Agente del PAE y Abogado).",
    "0.2.0": "Súper-usuario y Administrador se siembran automáticamente (una sola vez, "
              "sin importar la máquina); cambio de contraseña obligatorio para el Abogado "
              "en su primer inicio de sesión o tras un reset; tecla Enter vinculada al "
              "botón 'Iniciar sesión' en las pantallas de login.",
}
