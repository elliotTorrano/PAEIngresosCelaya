"""Constantes globales: roles, tipos de autenticación y estados."""

from app.__version__ import __version__

APP_NAME = "Sistema PAE"
SICPAE_NAME = "SICPAE"


def window_title(name: str) -> str:
    """Formato estándar del título de toda ventana: '{nombre} - SICPAE v#.##.##'."""
    return f"{name} - {SICPAE_NAME} v{__version__}"

ROLE_SUPERUSUARIO = "SUPERUSUARIO"
ROLE_ADMINISTRADOR = "ADMINISTRADOR"
ROLE_AGENTE_PAE = "AGENTE_PAE"
ROLE_ABOGADO = "ABOGADO"
ROLE_REPORTEADOR = "REPORTEADOR"

ROLES = (ROLE_SUPERUSUARIO, ROLE_ADMINISTRADOR, ROLE_AGENTE_PAE, ROLE_ABOGADO, ROLE_REPORTEADOR)

ROLE_LABELS = {
    ROLE_SUPERUSUARIO: "Súper-usuario",
    ROLE_ADMINISTRADOR: "Administrador",
    ROLE_AGENTE_PAE: "Agente del PAE",
    ROLE_ABOGADO: "Abogado",
    ROLE_REPORTEADOR: "Reporteador",
}

# Roles que se autentican con certificado autofirmado (vs. usuario/contraseña)
CERT_ROLES = (ROLE_SUPERUSUARIO, ROLE_ADMINISTRADOR, ROLE_AGENTE_PAE, ROLE_REPORTEADOR)
PASSWORD_ROLES = (ROLE_ABOGADO,)

AUTH_TYPE_CERTIFICADO = "CERTIFICADO"
AUTH_TYPE_PASSWORD = "PASSWORD"

# Roles que además pueden actuar como Agente del PAE
ROLES_CAN_ACT_AS_AGENTE = (ROLE_SUPERUSUARIO, ROLE_ADMINISTRADOR)

# Cuentas de prueba fijas para el piloto alpha con usuarios finales -- se
# siembran automáticamente en cualquier instalación (ver
# app/auth/dummy_accounts.py), con esta contraseña conocida, para que
# cualquier persona pueda entrar a probar sin necesitar que alguien más la
# dé de alta ni le genere un certificado. Nada de lo que se haga con ellas
# se guarda: ver app/ui/main_window.py, donde se fuerza `simulate=True` en
# Formato (Generar/Revisar/Captura) y se bloquea Datos de cuenta.
DUMMY_AGENTE_USERNAME = "agente_dummy"
DUMMY_ABOGADO_USERNAME = "abogado_dummy"
DUMMY_USERNAMES = (DUMMY_AGENTE_USERNAME, DUMMY_ABOGADO_USERNAME)
DUMMY_PASSWORD = "dummy12345"


def is_dummy_user(user) -> bool:
    return getattr(user, "username", None) in DUMMY_USERNAMES

BATCH_STATUS_PENDIENTE_ABOGADO = "PENDIENTE_ABOGADO"
BATCH_STATUS_CAPTURADO = "CAPTURADO"
BATCH_STATUS_EXPORTADO = "EXPORTADO"

QUIEN_RECIBE_EN_PUERTA = "EN PUERTA"
QUIEN_RECIBE_NOMBRE = "NOMBRE"
QUIEN_RECIBE_HOJA_CAMPO = "HOJA DE CAMPO"

RESET_REASON_CONTRASENA = "CONTRASENA_OLVIDADA"
RESET_REASON_CERTIFICADO_PERDIDO = "CERTIFICADO_PERDIDO"
RESET_REASON_CERTIFICADO_VENCIDO = "CERTIFICADO_VENCIDO"

RESET_REASON_LABELS = {
    RESET_REASON_CONTRASENA: "Contraseña olvidada",
    RESET_REASON_CERTIFICADO_PERDIDO: "Certificado perdido/dañado",
    RESET_REASON_CERTIFICADO_VENCIDO: "Certificado vencido",
}

RESET_STATUS_PENDIENTE = "PENDIENTE"
RESET_STATUS_ATENDIDA = "ATENDIDA"

ADMIN_NOTIFICATION_EMAIL_SUBJECT = "Solicitud de cambio de contraseña o certificado"
