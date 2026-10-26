import re
from datetime import datetime

from flask import current_app, g
from sqlalchemy import exists, func, or_, select

from backend import validation as v
from backend.academic_models import Reuniao
from backend.audit import audit
from backend.db import db, utcnow
from backend.defense_models import Etapa, Matricula, Orientacao, Trabalho
from backend.errors import APIError
from backend.models import Turma
from backend.security import roles
from backend.serialization import iso
from backend.services import academic_mail, classes


def teacher_classes():
    if (
        g.user.docente
        and g.user.docente.ativo_docente
        and g.user.docente.tipo_docente == "interno"
        and set(roles(g.user.id_usuario)) & {"professor_disciplina", "coordenador"}
    ):
        return classes.visible_classes().with_only_columns(Turma.id_turma)
    return select(Turma.id_turma).where(Turma.id_turma < 0)


def visible_stages():
    advisor = exists(
        select(Orientacao.id_orientacao).where(
            Orientacao.id_trabalho == Trabalho.id_trabalho,
            Orientacao.id_docente == g.user.id_usuario,
            Orientacao.situacao_aceite_orientacao == "aceito",
            Orientacao.data_encerramento_orientacao.is_(None),
        )
    )
    if not g.user.docente or not g.user.docente.ativo_docente:
        advisor = False
    return (
        select(Etapa)
        .join(Trabalho, Etapa.id_trabalho == Trabalho.id_trabalho)
        .join(Matricula, Etapa.id_matricula_turma == Matricula.id_matricula_turma)
        .where(
            or_(
                Trabalho.id_aluno == g.user.id_usuario,
                advisor,
                Matricula.id_turma.in_(teacher_classes()),
            )
        )
    )


def can_register(stage):
    membership = stage.matricula
    linked = stage.trabalho.id_aluno == g.user.id_usuario or bool(
        g.user.docente
        and g.user.docente.ativo_docente
        and db.session.scalar(
            select(Orientacao.id_orientacao).where(
                Orientacao.id_trabalho == stage.id_trabalho,
                Orientacao.id_docente == g.user.id_usuario,
                Orientacao.situacao_aceite_orientacao == "aceito",
                Orientacao.data_encerramento_orientacao.is_(None),
            )
        )
    )
    responsible = current_advisor(stage)
    return bool(
        linked
        and responsible
        and membership.situacao_matricula_turma == "ativa"
        and membership.turma.ativa_turma
        and stage.situacao_etapa_trabalho == "em_andamento"
    )


def current_advisor(stage):
    records = db.session.scalars(
        select(Orientacao).where(
            Orientacao.id_trabalho == stage.id_trabalho,
            Orientacao.papel_orientacao == "orientador",
            Orientacao.situacao_aceite_orientacao == "aceito",
            Orientacao.data_encerramento_orientacao.is_(None),
        )
    )
    return next(
        (o for o in records if o.docente.ativo_docente and o.docente.usuario.ativo_usuario), None
    )


def get_stage(identifier, lock=False):
    stage = db.session.scalar(visible_stages().where(Etapa.id_etapa_trabalho == identifier))
    if not stage:
        raise APIError(404, "TRABALHO_AUSENTE", "Trabalho não encontrado para seu vínculo.")
    if lock:
        # Same ordering as work/enrollment writes, then orientation to serialize responses.
        db.session.scalar(
            select(Turma)
            .where(Turma.id_turma == stage.matricula.id_turma)
            .with_for_update(of=Turma)
        )
        db.session.scalar(
            select(Matricula)
            .where(Matricula.id_matricula_turma == stage.id_matricula_turma)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        db.session.scalar(
            select(Trabalho)
            .where(Trabalho.id_trabalho == stage.id_trabalho)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        list(
            db.session.scalars(
                select(Orientacao)
                .where(Orientacao.id_trabalho == stage.id_trabalho)
                .order_by(Orientacao.id_orientacao)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
    return stage


def stage_json(stage):
    return {
        "id_etapa": stage.id_etapa_trabalho,
        "id_trabalho": stage.id_trabalho,
        "titulo": stage.trabalho.titulo_trabalho,
        "aluno": stage.trabalho.aluno.usuario.nome_usuario,
        "codigo_turma": stage.matricula.turma.codigo_turma,
        "nivel_turma": stage.matricula.turma.nivel_turma,
        "pode_registrar": can_register(stage),
    }


def serialize(item):
    return {
        "id_reuniao": item.id_reuniao_orientacao,
        "id_etapa": item.id_etapa_trabalho,
        "data_encontro": item.data_encontro_reuniao_orientacao.strftime("%d/%m/%Y"),
        "resumo": item.resumo_encaminhamentos_reuniao_orientacao,
        "orientador": item.orientacao.docente.usuario.nome_usuario,
        "autor": item.autor.nome_usuario,
        "data_registro": iso(item.data_registro_reuniao_orientacao),
    }


def register(stage, data):
    if not can_register(stage):
        raise APIError(
            403,
            "REGISTRO_NAO_AUTORIZADO",
            "O registro exige estudante ou orientador vinculado, "
            "matrícula ativa e orientação aceita.",
        )
    value = data.get("data_encontro")
    try:
        if not isinstance(value, str) or not re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
            raise ValueError
        day = datetime.strptime(value, "%d/%m/%Y").date()
        if day > utcnow().astimezone(current_app.config["ACADEMIC_TIMEZONE"]).date():
            raise ValueError
    except ValueError:
        raise APIError(
            422,
            "UC_05_M03",
            "Informe uma data válida no formato DD/MM/AAAA, até hoje.",
            {"data_encontro": "Data inválida ou futura."},
        ) from None
    summary = v.text(data.get("resumo"), "resumo", 10000)
    advisor = current_advisor(stage)
    item = Reuniao(
        id_etapa_trabalho=stage.id_etapa_trabalho,
        id_orientacao=advisor.id_orientacao,
        data_encontro_reuniao_orientacao=day,
        resumo_encaminhamentos_reuniao_orientacao=summary,
        id_usuario_registro=g.user.id_usuario,
    )
    db.session.add(item)
    db.session.flush()
    notifications = []
    for user in (stage.trabalho.aluno.usuario, advisor.docente.usuario):
        notification = academic_mail.enqueue(
            user,
            "ata_reuniao",
            "Ata de reunião registrada - SIGG-TCC",
            f"Ata de reunião em {value} do trabalho {stage.trabalho.titulo_trabalho}.\n{summary}\n"
            f"Consulte o histórico em {current_app.config['FRONTEND_URL'].rstrip('/')}/#/reunioes",
            f"ata:{item.id_reuniao_orientacao}:{user.id_usuario}",
            id_reuniao_orientacao=item.id_reuniao_orientacao,
        )
        db.session.flush()
        notifications.append(notification.id_notificacao)
    audit(
        g.user.id_usuario, "registro_ata_reuniao", "reuniao_orientacao", item.id_reuniao_orientacao
    )
    db.session.commit()
    academic_mail.deliver(notifications)
    return item


def attendance(membership):
    stage = db.session.scalar(
        select(Etapa).where(Etapa.id_matricula_turma == membership.id_matricula_turma)
    )
    count, last = (
        db.session.execute(
            select(
                func.count(Reuniao.id_reuniao_orientacao),
                func.max(Reuniao.data_encontro_reuniao_orientacao),
            ).where(Reuniao.id_etapa_trabalho == stage.id_etapa_trabalho)
        ).one()
        if stage
        else (0, None)
    )
    baseline = (
        last
        or membership.data_matricula_matricula_turma.astimezone(
            current_app.config["ACADEMIC_TIMEZONE"]
        ).date()
    )
    days = max(
        0, (utcnow().astimezone(current_app.config["ACADEMIC_TIMEZONE"]).date() - baseline).days
    )
    return {
        "id_matricula": membership.id_matricula_turma,
        "id_etapa": stage.id_etapa_trabalho if stage else None,
        "aluno": membership.aluno.usuario.nome_usuario,
        "matricula": membership.aluno.matricula_aluno,
        "codigo_turma": membership.turma.codigo_turma,
        "titulo": stage.trabalho.titulo_trabalho if stage else None,
        "quantidade_reunioes": count,
        "ultimo_encontro": last.strftime("%d/%m/%Y") if last else None,
        "dias_sem_reuniao": days,
        "alerta_inatividade": days > 30,
    }
