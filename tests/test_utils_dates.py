from app.utils.dates import format_local_datetime


def test_format_local_datetime_converts_utc_to_local_dd_mm_yyyy():
    formatted = format_local_datetime("2026-01-15 10:30:00")
    assert "/" in formatted
    day, month, year_and_time = formatted.split("/")
    assert len(day) == 2 and len(month) == 2
    assert year_and_time.startswith("2026")


def test_format_local_datetime_empty_returns_empty():
    assert format_local_datetime(None) == ""
    assert format_local_datetime("") == ""


def test_format_local_datetime_unparseable_returns_as_is():
    assert format_local_datetime("no es una fecha") == "no es una fecha"
