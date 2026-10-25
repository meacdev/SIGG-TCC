from types import SimpleNamespace

import pytest

from backend.services import academic_mail


@pytest.mark.parametrize("use_ssl", [False, True])
def test_academic_notification_transport_tls_and_content(app, monkeypatch, use_ssl):
    calls = []

    class SMTP:
        def __init__(self, host, port, **options):
            calls.append(("connect", host, port, options))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self, **kwargs):
            calls.append(("starttls", kwargs))

        def login(self, *args):
            calls.append(("login", args))

        def send_message(self, message):
            calls.append(("message", message))

    monkeypatch.setattr(academic_mail.smtplib, "SMTP", SMTP)
    monkeypatch.setattr(academic_mail.smtplib, "SMTP_SSL", SMTP)
    app.config.update(
        MAIL_SENDER=None,
        SMTP_HOST="smtp.example.com",
        SMTP_FROM="sistema@example.com",
        SMTP_USERNAME="conta-teste",
        SMTP_PASSWORD="segredo-sintetico",
        SMTP_SSL=use_ssl,
        SMTP_STARTTLS=not use_ssl,
    )
    with app.app_context():
        academic_mail.send(
            SimpleNamespace(
                email_destino_notificacao="pessoa@example.com",
                assunto_notificacao="Ata de reunião",
                corpo_notificacao="Registro acadêmico preservado.",
            )
        )
    assert any(c[0] == "starttls" for c in calls) == (not use_ssl)
    assert ("context" in calls[0][3]) == use_ssl
    assert any(c[0] == "login" for c in calls)
    message = calls[-1][1]
    assert message["To"] == "pessoa@example.com"
    assert "Registro acadêmico preservado." in message.get_content()
