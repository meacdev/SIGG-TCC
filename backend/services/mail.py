import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app

from backend.errors import APIError


def require_mail():
    config = current_app.config
    if not config.get("MAIL_SENDER") and not (config["SMTP_HOST"] and config["SMTP_FROM"]):
        raise APIError(503, "EMAIL_INDISPONIVEL", "A recuperação por e-mail está indisponível.")


def send_reset_email(address, code):
    """The recovery secret is never persisted or written to logs."""
    config = current_app.config
    content = (
        f"Seu código de recuperação do SIGG-TCC é: {code}\n"
        f"Válido por {config['RESET_CODE_MINUTES']} minutos. "
        "Se você não solicitou, ignore esta mensagem."
    )
    if config.get("MAIL_SENDER"):
        config["MAIL_SENDER"](address, "Recuperação de senha SIGG-TCC", content)
        return
    message = EmailMessage()
    message["From"], message["To"] = config["SMTP_FROM"], address
    message["Subject"] = "Recuperação de senha SIGG-TCC"
    message.set_content(content)
    client = smtplib.SMTP_SSL if config["SMTP_SSL"] else smtplib.SMTP
    try:
        kwargs = {"timeout": 10}
        if config["SMTP_SSL"]:
            kwargs["context"] = ssl.create_default_context()
        with client(config["SMTP_HOST"], config["SMTP_PORT"], **kwargs) as smtp:
            if config["SMTP_STARTTLS"] and not config["SMTP_SSL"]:
                smtp.starttls(context=ssl.create_default_context())
            if config["SMTP_USERNAME"]:
                smtp.login(config["SMTP_USERNAME"], config["SMTP_PASSWORD"])
            smtp.send_message(message)
    except OSError, smtplib.SMTPException:
        raise APIError(
            503, "EMAIL_INDISPONIVEL", "Não foi possível enviar o e-mail agora."
        ) from None
