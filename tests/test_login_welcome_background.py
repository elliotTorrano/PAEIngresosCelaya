from PySide6.QtWidgets import QLabel

from app.ui.login.login_window import WELCOME_SUBTITLE, WELCOME_TITLE, LoginWindow
from app.ui.widgets.background_widget import BackgroundWidget


def test_login_window_shows_welcome_text_and_background_widget(qapp, db):
    window = LoginWindow()

    labels_text = [label.text() for label in window.findChildren(QLabel)]
    assert any(WELCOME_TITLE in text for text in labels_text)
    assert any(WELCOME_SUBTITLE in text for text in labels_text)
    assert len(window.findChildren(BackgroundWidget)) == 1
