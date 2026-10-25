"""Persistent academic notifications; delivery failure does not undo academic records."""

import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage

from flask import current_app
from sqlalchemy import or_, select, update

from backend.academic_models import NotificacaoAcademica as Notification
from backend.db import db, utcnow


def enqueue(user, kind, subject, content, key, **links):
    item = Notification(
        id_usuario_destinatario=user.id_usuario,
        email_destino_notificacao=user.email_usuario,
        tipo_notificacao=kind,
        assunto_notificacao=subject,
        corpo_notificacao=content,
        chave_idempotencia_notificacao=key,
        **links,
    )
    db.session.add(item)
    return item


def send(item):
    config = current_app.config
    if config.get("MAIL_SENDER"):
        config["MAIL_SENDER"](
            item.email_destino_notificacao, item.assunto_notificacao, item.corpo_notificacao
        )
        return
    if not config["SMTP_HOST"] or not config["SMTP_FROM"]:
        raise RuntimeError("SMTP não configurado")
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = (
        config["SMTP_FROM"],
        item.email_destino_notificacao,
        item.assunto_notificacao,
    )
    message.set_content(item.corpo_notificacao)
    transport = smtplib.SMTP_SSL if config["SMTP_SSL"] else smtplib.SMTP
    options = {"timeout": 5}
    if config["SMTP_SSL"]:
        options["context"] = ssl.create_default_context()
    with transport(config["SMTP_HOST"], config["SMTP_PORT"], **options) as smtp:
        if config["SMTP_STARTTLS"] and not config["SMTP_SSL"]:
            smtp.starttls(context=ssl.create_default_context())
        if config["SMTP_USERNAME"]:
            smtp.login(config["SMTP_USERNAME"], config["SMTP_PASSWORD"])
        smtp.send_message(message)


def deliver(ids=None):
    eligible = or_(
        Notification.situacao_notificacao.in_(["pendente", "falha"]),
        (Notification.situacao_notificacao == "enviando")
        & (Notification.data_tentativa_notificacao < utcnow() - timedelta(minutes=10)),
    )
    query = select(Notification.id_notificacao).where(
        Notification.tipo_notificacao.in_(
            ["remocao_matricula", "convite_orientacao", "ata_reuniao"]
        ),
        eligible,
        Notification.tentativas_notificacao < 10,
    )
    if ids is not None:
        query = query.where(Notification.id_notificacao.in_(ids))
    for identifier in list(db.session.scalars(query.limit(100))):
        claim = db.session.execute(
            update(Notification)
            .where(
                Notification.id_notificacao == identifier,
                eligible,
                Notification.tentativas_notificacao < 10,
            )
            .values(
                situacao_notificacao="enviando",
                data_tentativa_notificacao=utcnow(),
                tentativas_notificacao=Notification.tentativas_notificacao + 1,
            )
        )
        db.session.commit()
        if claim.rowcount != 1:
            continue
        item = db.session.get(Notification, identifier)
        db.session.refresh(item)
        try:
            send(item)
            item.situacao_notificacao = "enviada"
            item.data_envio_notificacao = utcnow()
            item.ultimo_erro_notificacao = None
        except Exception as error:
            item.situacao_notificacao = "falha"
            item.ultimo_erro_notificacao = type(error).__name__
        db.session.commit()
