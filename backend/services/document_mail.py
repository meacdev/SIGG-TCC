import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage

from flask import current_app
from sqlalchemy import or_, select, update

from backend.academic_models import NotificacaoAcademica as NotificacaoDocumento
from backend.db import db, utcnow
from backend.services import pdf_storage


def send(address, subject, content, attachment):
    config = current_app.config
    if config.get("DOCUMENT_MAIL_SENDER"):
        config["DOCUMENT_MAIL_SENDER"](address, subject, content, attachment)
        return
    if not config["SMTP_HOST"] or not config["SMTP_FROM"]:
        raise RuntimeError("SMTP indisponível")
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = config["SMTP_FROM"], address, subject
    message.set_content(content)
    message.add_attachment(
        attachment, maintype="application", subtype="pdf", filename="declaracao-participacao.pdf"
    )
    transport = smtplib.SMTP_SSL if config["SMTP_SSL"] else smtplib.SMTP
    kwargs = {"timeout": 5}
    if config["SMTP_SSL"]:
        kwargs["context"] = ssl.create_default_context()
    with transport(config["SMTP_HOST"], config["SMTP_PORT"], **kwargs) as smtp:
        if config["SMTP_STARTTLS"] and not config["SMTP_SSL"]:
            smtp.starttls(context=ssl.create_default_context())
        if config["SMTP_USERNAME"]:
            smtp.login(config["SMTP_USERNAME"], config["SMTP_PASSWORD"])
        smtp.send_message(message)


def deliver(defense_id=None):
    cutoff = utcnow() - timedelta(minutes=10)
    eligible = or_(
        NotificacaoDocumento.situacao_notificacao.in_(["pendente", "falha"]),
        (NotificacaoDocumento.situacao_notificacao == "enviando")
        & (NotificacaoDocumento.data_tentativa_notificacao < cutoff),
    )
    query = (
        select(NotificacaoDocumento.id_notificacao)
        .where(
            NotificacaoDocumento.tipo_notificacao == "declaracao_banca",
            eligible,
            NotificacaoDocumento.tentativas_notificacao < 10,
        )
        .order_by(NotificacaoDocumento.id_notificacao)
        .limit(100)
    )
    if defense_id is not None:
        query = query.where(NotificacaoDocumento.id_banca == defense_id)
    ids = list(db.session.scalars(query))
    for identifier in ids:
        claimed = db.session.execute(
            update(NotificacaoDocumento)
            .where(
                NotificacaoDocumento.id_notificacao == identifier,
                eligible,
            )
            .values(
                situacao_notificacao="enviando",
                data_tentativa_notificacao=utcnow(),
                tentativas_notificacao=NotificacaoDocumento.tentativas_notificacao + 1,
            )
        )
        db.session.commit()
        if claimed.rowcount != 1:
            continue
        notification = db.session.get(NotificacaoDocumento, identifier)
        db.session.refresh(notification)
        try:
            document = notification.documento
            if document.data_revogacao_documento_oficial:
                notification.situacao_notificacao = "cancelada"
            else:
                send(
                    notification.email_destino_notificacao,
                    notification.assunto_notificacao,
                    notification.corpo_notificacao,
                    pdf_storage.read(document.arquivo),
                )
                notification.situacao_notificacao = "enviada"
                notification.data_envio_notificacao = utcnow()
                notification.ultimo_erro_notificacao = None
        except Exception as error:
            notification.situacao_notificacao = "falha"
            # Store only the failure class, never transport credentials or message bodies.
            notification.ultimo_erro_notificacao = type(error).__name__
        db.session.commit()
    return len(ids)
