import json
from unittest.mock import patch

import pytest

from app.update import checker, flow, installer


# --- parse_version / is_newer -------------------------------------------------

@pytest.mark.parametrize(
    "text, expected",
    [
        ("0.6.0", (0, 6, 0)),
        ("v0.6.0", (0, 6, 0)),
        ("V1.2.3", (1, 2, 3)),
        ("2.0", (2, 0)),
    ],
)
def test_parse_version(text, expected):
    assert checker.parse_version(text) == expected


@pytest.mark.parametrize(
    "current, candidate, expected",
    [
        ("0.5.1", "0.6.0", True),
        ("0.5.1", "v0.6.0", True),
        ("0.6.0", "0.6.0", False),
        ("0.6.0", "0.5.9", False),
        ("0.5.1", "no-es-version", False),
        ("0.5.1", "", False),
    ],
)
def test_is_newer(current, candidate, expected):
    assert checker.is_newer(current, candidate) is expected


# --- check_for_update ----------------------------------------------------------

def _fake_response(payload_dict):
    body = json.dumps(payload_dict).encode("utf-8")

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return body

    return _Resp()


def test_check_for_update_returns_info_when_newer_release_available():
    payload = {
        "tag_name": "v0.6.0",
        "assets": [{"name": "SistemaPAE.exe", "browser_download_url": "https://example.com/SistemaPAE.exe"}],
    }
    with patch("app.update.checker.urllib.request.urlopen", return_value=_fake_response(payload)):
        info = checker.check_for_update("0.5.1")
    assert info == checker.UpdateInfo(version="0.6.0", download_url="https://example.com/SistemaPAE.exe")


def test_check_for_update_returns_none_when_already_latest():
    payload = {
        "tag_name": "v0.5.1",
        "assets": [{"name": "SistemaPAE.exe", "browser_download_url": "https://example.com/SistemaPAE.exe"}],
    }
    with patch("app.update.checker.urllib.request.urlopen", return_value=_fake_response(payload)):
        assert checker.check_for_update("0.5.1") is None


def test_check_for_update_returns_none_on_malformed_json():
    class _BadResp:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"esto no es json"

    with patch("app.update.checker.urllib.request.urlopen", return_value=_BadResp()):
        assert checker.check_for_update("0.5.1") is None


def test_check_for_update_returns_none_on_network_error():
    with patch("app.update.checker.urllib.request.urlopen", side_effect=OSError("sin conexión")):
        assert checker.check_for_update("0.5.1") is None


def test_check_for_update_returns_none_when_asset_missing():
    payload = {"tag_name": "v0.6.0", "assets": [{"name": "otra_cosa.exe", "browser_download_url": "https://x"}]}
    with patch("app.update.checker.urllib.request.urlopen", return_value=_fake_response(payload)):
        assert checker.check_for_update("0.5.1") is None


# --- download_update -------------------------------------------------------------

def test_download_update_writes_final_file(tmp_path):
    dest = tmp_path / "SistemaPAE_nuevo.exe"
    content = b"contenido de prueba" * 1000

    class _Resp:
        def __init__(self, data):
            self._data = data
            self._sent = False
            self.headers = {"Content-Length": str(len(data))}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self, n):
            if self._sent:
                return b""
            self._sent = True
            return self._data

    calls = []
    with patch("app.update.installer.urllib.request.urlopen", return_value=_Resp(content)):
        installer.download_update(
            "https://example.com/x", dest, progress_callback=lambda read, total: calls.append((read, total))
        )

    assert dest.read_bytes() == content
    assert not dest.with_suffix(dest.suffix + ".part").exists()
    assert calls == [(len(content), len(content))]


def test_download_update_does_not_leave_final_file_on_failure(tmp_path):
    dest = tmp_path / "SistemaPAE_nuevo.exe"

    with patch("app.update.installer.urllib.request.urlopen", side_effect=OSError("cortado")):
        with pytest.raises(OSError):
            installer.download_update("https://example.com/x", dest)

    assert not dest.exists()


# --- flow.run_update_check --------------------------------------------------------

def test_run_update_check_does_nothing_when_no_update(qapp):
    with patch("app.update.flow.checker.check_for_update", return_value=None), patch(
        "app.update.flow.QMessageBox.question"
    ) as mock_question:
        flow.run_update_check(None)
    mock_question.assert_not_called()


def test_run_update_check_declines_does_not_download(qapp):
    info = checker.UpdateInfo(version="0.6.0", download_url="https://example.com/x")
    with patch("app.update.flow.checker.check_for_update", return_value=info), patch(
        "app.update.flow.QMessageBox.question", return_value=None
    ) as mock_question, patch("app.update.flow.installer.download_update") as mock_download:
        from PySide6.QtWidgets import QMessageBox

        mock_question.return_value = QMessageBox.StandardButton.No
        flow.run_update_check(None)
    mock_download.assert_not_called()


def test_run_update_check_warns_and_stops_when_updater_exe_missing(qapp, tmp_path):
    info = checker.UpdateInfo(version="0.6.0", download_url="https://example.com/x")
    from PySide6.QtWidgets import QMessageBox

    with patch("app.update.flow.checker.check_for_update", return_value=info), patch(
        "app.update.flow.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes
    ), patch("app.update.flow.QMessageBox.warning") as mock_warning, patch(
        "app.update.flow.paths.updater_exe_path", return_value=tmp_path / "no_existe" / "updater.exe"
    ), patch("app.update.flow.installer.download_update") as mock_download:
        flow.run_update_check(None)

    mock_warning.assert_called_once()
    mock_download.assert_not_called()


def test_run_update_check_downloads_and_hands_off_to_updater(qapp, tmp_path, monkeypatch):
    from app.utils import paths as paths_module

    monkeypatch.setattr(paths_module, "base_dir", lambda: tmp_path)
    updater_exe = tmp_path / "updater.exe"
    updater_exe.write_bytes(b"x")

    info = checker.UpdateInfo(version="0.6.0", download_url="https://example.com/x")
    from PySide6.QtWidgets import QMessageBox

    with patch("app.update.flow.checker.check_for_update", return_value=info), patch(
        "app.update.flow.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes
    ), patch("app.update.flow.installer.download_update") as mock_download, patch(
        "app.update.flow.installer.launch_updater_and_exit"
    ) as mock_launch:
        flow.run_update_check(None)

    mock_download.assert_called_once()
    mock_launch.assert_called_once()
    called_updater, called_target, called_new = mock_launch.call_args[0]
    assert called_updater == updater_exe
    assert called_target == tmp_path / "SistemaPAE.exe"
