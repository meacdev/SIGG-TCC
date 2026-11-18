from datetime import timedelta

from flask import current_app
from sqlalchemy import update

from backend.academic_models import NotificacaoAcademica
from backend.db import db, utcnow
from backend.services import academic_mail

KINDS = ("convite_banca", "reagendamento_banca", "lembrete_banca")


def enqueue(banca, recipients, changed):
    now = utcnow()
    db.session.execute(
        update(NotificacaoAcademica)
        .where(
            NotificacaoAcademica.id_banca == banca.id_banca,
            NotificacaoAcademica.tipo_notificacao.in_(KINDS),
            NotificacaoAcademica.situacao_notificacao.in_(("pendente", "falha")),
        )
        .values(situacao_notificacao="cancelada")
    )
    local = banca.data_inicio_banca.astimezone(current_app.config["ACADEMIC_TIMEZONE"])
    location = banca.url_defesa_banca_defesa or banca.local_defesa_banca
    base = current_app.config["FRONTEND_URL"].rstrip("/")
    portal = (
        f"{base}/#/bancas?manuscrito={banca.id_banca}" if base else "SIGG-TCC, em Minhas bancas"
    )
    body = (
        f"Defesa em {local:%d/%m/%Y às %H:%M %Z}. Local ou link: {location}. "
        f"Consulte o manuscrito em {portal}."
    )
    for user in recipients:
        for kind, date in [
            (KINDS[int(changed)], now),
            (KINDS[2], banca.data_inicio_banca - timedelta(hours=24)),
        ]:
            if kind == KINDS[2] and date <= now:
                continue
            item = academic_mail.enqueue(
                user,
                kind,
                "Agendamento de defesa de TCC",
                body,
                f"{kind}:{banca.id_banca}:{banca.versao_banca}:{user.id_usuario}",
                id_banca=banca.id_banca,
            )
            item.data_agendamento_notificacao = date


def calendar(banca):
    def escape(value):
        return (
            value.replace("\\", "\\\\")
            .replace("\r", "")
            .replace("\n", "\\n")
            .replace(",", "\\,")
            .replace(";", "\\;")
        )

    def fold(line):
        parts = []
        while len(line.encode()) > 72:
            size = 72
            while len(line[:size].encode()) > 72:
                size -= 1
            parts.append(line[:size])
            line = " " + line[size:]
        return "\r\n".join([*parts, line])

    location = banca.url_defesa_banca_defesa or banca.local_defesa_banca
    return "\r\n".join(
        map(
            fold,
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "PRODID:-//UEA//SIGG-TCC//PT",
                "METHOD:PUBLISH",
                "BEGIN:VEVENT",
                f"UID:{banca.uid_calendario_banca}",
                f"SEQUENCE:{banca.versao_banca - 1}",
                f"DTSTAMP:{utcnow():%Y%m%dT%H%M%SZ}",
                f"DTSTART:{banca.data_inicio_banca:%Y%m%dT%H%M%SZ}",
                f"DTEND:{banca.data_fim_banca:%Y%m%dT%H%M%SZ}",
                "SUMMARY:Defesa de TCC",
                f"LOCATION:{escape(location)}",
                "END:VEVENT",
                "END:VCALENDAR",
                "",
            ],
        )
    )
