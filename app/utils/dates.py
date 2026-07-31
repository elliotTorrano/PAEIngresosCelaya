"""La base de datos guarda las fechas con datetime('now') de SQLite, que es
UTC -- estas funciones las convierten a la hora local de la máquina para
mostrarlas al usuario, en formato dd/mm/aaaa."""

from __future__ import annotations

from datetime import datetime, timezone

_SQLITE_FORMAT = "%Y-%m-%d %H:%M:%S"


def format_local_datetime(value: str | None) -> str:
    """Convierte un timestamp UTC de SQLite ('aaaa-mm-dd hh:mm:ss') a hora
    local en formato 'dd/mm/aaaa hh:mm'. Si `value` no tiene ese formato
    (o está vacío), se devuelve tal cual para no ocultar datos inesperados."""
    if not value:
        return ""
    try:
        dt = datetime.strptime(value, _SQLITE_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return value
    return dt.astimezone().strftime("%d/%m/%Y %H:%M")
