import re
import smtplib
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from backend.db import db
from backend.models import RecuperacaoSenha


@pytest.mark.parametrize("ssl", [False, True])
def test_reset_email_uses_configured_smtp(app, client, signup, monkeypatch, ssl):
    user = signup()
    smtp = MagicMock()
    monkeypatch.setattr(
        "backend.services.mail.smtplib.SMTP_SSL" if ssl else "backend.services.mail.smtplib.SMTP",
        smtp,
    )
    app.config.update(
        MAIL_SENDER=None,
        SMTP_HOST="smtp.example.com",
        SMTP_PORT=465 if ssl else 587,
        SMTP_FROM="sigg@example.com",
        SMTP_USERNAME="sigg",
        SMTP_PASSWORD="test-secret",
        SMTP_SSL=ssl,
        SMTP_STARTTLS=not ssl,
    )
    response = client.post(
        "/api/v1/auth/recuperacao-senha", json={"email_usuario": user["email_usuario"]}
    )
    assert response.status_code == 202
    connection = smtp.return_value.__enter__.return_value
    connection.login.assert_called_once_with("sigg", "test-secret")
    assert connection.starttls.called is not ssl
    message = connection.send_message.call_args.args[0]
    assert message["To"] == user["email_usuario"]
    assert message["From"] == "sigg@example.com"
    assert re.search(r"é: [0-9]{10}\n", message.get_content())
    assert "test-secret" not in message.get_content()


def test_smtp_failure_does_not_persist_recovery_or_expose_password(
    app, client, signup, monkeypatch
):
    user = signup()
    app.config.update(MAIL_SENDER=None, SMTP_HOST="smtp.example.com", SMTP_FROM="sigg@example.com")
    monkeypatch.setattr(
        "backend.services.mail.smtplib.SMTP",
        MagicMock(side_effect=smtplib.SMTPException("private-password")),
    )
    response = client.post(
        "/api/v1/auth/recuperacao-senha", json={"email_usuario": user["email_usuario"]}
    )
    assert response.status_code == 503
    assert "private-password" not in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.scalar(select(RecuperacaoSenha)) is None
