from unittest.mock import patch

from app.config import AUTH_TYPE_CERTIFICADO, ROLE_AGENTE_PAE
from app.db.repositories import users as users_repo
from app.ui.widgets.simple_account_view import SimpleAccountView


def _make_agente():
    return users_repo.create_user(
        username="agente1", role=ROLE_AGENTE_PAE, full_name="Agente Uno", email="viejo@example.com",
        auth_type=AUTH_TYPE_CERTIFICADO,
    )


def test_save_empty_email_warns_and_does_not_update(qapp, db):
    agente = _make_agente()
    view = SimpleAccountView(agente)
    view.email_input.setText("   ")

    with patch("app.ui.widgets.simple_account_view.QMessageBox.warning") as mock_warning, patch(
        "app.ui.widgets.simple_account_view.users_repo.update_email"
    ) as mock_update:
        view._on_save()

    mock_warning.assert_called_once()
    mock_update.assert_not_called()


def test_save_valid_email_updates_and_confirms(qapp, db):
    agente = _make_agente()
    view = SimpleAccountView(agente)
    view.email_input.setText("nuevo@example.com")

    with patch("app.ui.widgets.simple_account_view.QMessageBox.information") as mock_info:
        view._on_save()

    mock_info.assert_called_once()
    refreshed = users_repo.get_by_id(agente.id)
    assert refreshed.email == "nuevo@example.com"
    assert refreshed.username == "agente1"
    assert refreshed.full_name == "Agente Uno"
