"""Scheduling and rubric rules for the scoped academic management interface."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from flask import g
from sqlalchemy import func, select

from backend import official_rubric as official
from backend import validation as v
from backend.audit import audit
from backend.db import db, utcnow
from backend.defense_models import (
    Avaliador,
    Banca,
    Criterio,
    Etapa,
    Manuscrito,
    Membro,
    Orientacao,
    Rubrica,
)
from backend.errors import APIError
from backend.models import Professor, Usuario
from backend.serialization import iso
from backend.services import academic_mail, classes, defense_agenda, users


def scoped_stage(class_id, stage_id, lock=False):
    query = select(Etapa).where(Etapa.id_etapa_trabalho == stage_id)
    if lock:
        query = query.with_for_update()
    stage = db.session.scalar(query)
    if not stage or stage.matricula.id_turma != class_id:
        raise APIError(404, "ETAPA_AUSENTE", "Selecione um trabalho da turma.")
    return stage


def advisor(stage):
    return db.session.scalar(
        select(Orientacao.id_professor).where(
            Orientacao.id_trabalho_tcc == stage.id_trabalho_tcc,
            Orientacao.papel_orientacao == "orientador",
            Orientacao.situacao_aceite_orientacao == "aceito",
            Orientacao.data_encerramento_orientacao.is_(None),
        )
    )


def latest_pdf(stage):
    return db.session.scalar(
        select(Manuscrito)
        .where(Manuscrito.id_etapa_trabalho == stage.id_etapa_trabalho)
        .order_by(Manuscrito.versao_manuscrito_trabalho.desc())
        .limit(1)
    )


def register_external(class_id, data):
    classes.get_class(class_id)
    try:
        name = v.name(data["nome"], "nome")
        address = v.email(data["email"], "UC_07_M05")
        title = users.title(data["titulacao"], "titulacao")
        institution = v.text(data["instituicao"], "instituicao", 200)
    except APIError as error:
        raise APIError(
            422, "UC_07_M05", "Informe nome, e-mail válido, titulação e instituição.", error.fields
        ) from error
    if db.session.scalar(select(Usuario.id_usuario).where(Usuario.email_usuario == address)):
        raise APIError(409, "UC_01_M04", "E-mail já cadastrado. Busque pelo nome do avaliador.")
    user = Usuario(nome_usuario=name, email_usuario=address)
    db.session.add(user)
    db.session.flush()
    db.session.add(
        Professor(
            id_professor=user.id_usuario,
            tipo_professor="externo",
            titulacao_professor=title,
            instituicao_origem_professor=institution,
        )
    )
    db.session.flush()
    db.session.add(
        Avaliador(
            id_avaliador=user.id_usuario,
            tipo_avaliador="externo",
            titulacao_avaliador=title,
            instituicao_avaliador=institution,
        )
    )
    audit(g.user.id_usuario, "avaliador_externo_cadastrado", "usuario", user.id_usuario)
    db.session.commit()
    return {
        "id": user.id_usuario,
        "nome": name,
        "tipo": "externo",
        "titulacao": title,
        "instituicao": institution,
    }


def official_rubric(class_id):
    """Return the turma's row of the fixed official rubric, provisioning it when needed.

    The rubric is not parametrizable (UC08 is read-only). A per-turma row keeps the
    relational links of banca, criteria and grades; a legacy active rubric is retired.
    """
    active = db.session.scalar(
        select(Rubrica)
        .where(Rubrica.id_turma == class_id, Rubrica.situacao_rubrica == "ativa")
        .with_for_update()
    )
    if (
        active
        and [
            official.criterion_signature(
                c.nome_criterio_rubrica,
                c.componente_criterio_rubrica,
                c.peso_criterio_rubrica,
                c.descritores_criterio_rubrica,
            )
            for c in active.criterios
        ]
        == official.OFFICIAL_SIGNATURE
    ):
        return active
    if active:
        active.situacao_rubrica = "inativa"
        active.data_modificacao_rubrica_avaliacao = utcnow()
        audit(g.user.id_usuario, "rubrica_inativada", "rubrica_avaliacao", active.id_rubrica)
        db.session.flush()
    version = db.session.scalar(
        select(func.max(Rubrica.versao_rubrica)).where(
            Rubrica.id_turma == class_id, Rubrica.nome_rubrica == official.RUBRIC_NAME
        )
    )
    item = Rubrica(
        id_turma=class_id,
        id_usuario_criacao=g.user.id_usuario,
        nome_rubrica=official.RUBRIC_NAME,
        versao_rubrica=(version or 0) + 1,
        situacao_rubrica="ativa",
        criterios=[
            Criterio(
                nome_criterio_rubrica=c["nome"],
                descricao_criterio_rubrica=c["descricao"],
                componente_criterio_rubrica=c["componente"],
                descritores_criterio_rubrica=c["descritores"],
                peso_criterio_rubrica=Decimal(c["peso"]),
                pontuacao_maxima_criterio_rubrica=official.MAXIMUM_GRADE,
                ordem_criterio_rubrica=order,
            )
            for order, c in enumerate(official.CRITERIA, 1)
        ],
    )
    db.session.add(item)
    db.session.flush()
    audit(g.user.id_usuario, "rubrica_oficial_vinculada", "rubrica_avaliacao", item.id_rubrica)
    return item


def timestamp(value):
    try:
        result = datetime.fromisoformat(value)
        if result.tzinfo is None:
            raise ValueError
        return result.astimezone(UTC)
    except (ValueError, TypeError, OverflowError):
        raise APIError(422, "UC_07_M06", "Informe uma data e um horário com fuso válido.") from None


def schedule_json(banca):
    return {
        "id": banca.id_banca,
        "etapa": banca.id_etapa_trabalho,
        "titulo": banca.etapa.trabalho.titulo_trabalho_tcc,
        "rubrica": banca.id_rubrica,
        "tempo_apresentacao": official.presentation_minutes(
            banca.etapa.matricula.turma.nivel_turma
        ),
        "inicio": iso(banca.data_inicio_banca),
        "fim": iso(banca.data_fim_banca),
        "modalidade": banca.modalidade_banca_defesa,
        "local": banca.local_defesa_banca,
        "url": banca.url_defesa_banca_defesa,
        "situacao": banca.situacao_banca,
        "membros": [
            {
                "id": m.id_docente,
                "papel": m.papel_membro_banca,
                "nome": m.avaliador.usuario.nome_usuario,
            }
            for m in banca.membros
        ],
    }


def overlapping_members(start, end, ids, identifier=None):
    return list(
        db.session.scalars(
            select(Membro.id_docente)
            .join(Banca)
            .where(
                Banca.id_banca != (identifier or 0),
                Banca.situacao_banca != "cancelada",
                Banca.data_inicio_banca < end,
                Banca.data_fim_banca > start,
                Membro.id_docente.in_(ids),
            )
            .distinct()
            .order_by(Membro.id_docente)
        )
    )


def schedule(class_id, data, identifier=None):
    turma = classes.get_class(class_id, lock=True)
    stage = scoped_stage(class_id, v.integer(data["etapa"], "etapa"), lock=True)
    president = advisor(stage)
    if (
        not turma.ativa_turma
        or stage.situacao_etapa_trabalho != "em_andamento"
        or stage.trabalho.situacao_trabalho_tcc != "em_andamento"
        or stage.matricula.situacao_matricula_turma != "ativa"
        or not president
    ):
        raise APIError(
            422, "TRABALHO_INELEGIVEL", "Selecione um TCC ativo com matrícula e orientação aceitas."
        )
    pdf = latest_pdf(stage)
    if not pdf:
        raise APIError(
            422,
            "UC_07_M04",
            "O estudante precisa enviar o manuscrito antes do agendamento.",
        )
    roles = {
        "presidente": [president],
        "examinador": data["titulares"],
        "suplente": data["suplentes"],
    }
    if not isinstance(roles["examinador"], list) or not isinstance(roles["suplente"], list):
        raise APIError(422, "UC_07_M03", "Selecione titulares e suplentes.")
    if len(roles["examinador"]) < 2 or len(roles["suplente"]) < 1:
        raise APIError(
            422, "UC_07_M03", "Selecione dois titulares além do orientador e um suplente."
        )
    ids = [v.integer(i, "membro") for group in roles.values() for i in group]
    if len(ids) > 20 or len(ids) != len(set(ids)):
        raise APIError(422, "BANCA_INVALIDA", "Selecione até 20 pessoas distintas.")
    start, end = timestamp(data["inicio"]), timestamp(data["fim"])
    if not utcnow() < start < end:
        raise APIError(422, "UC_07_M06", "Informe início futuro e término posterior ao início.")
    try:
        mode = v.choice(data["modalidade"], "modalidade", ("presencial", "remota", "hibrida"))
        url = v.url(data.get("url"), "url") if mode != "presencial" else None
        local = v.text(data.get("local"), "local", 2000) if mode != "remota" else url
    except APIError as error:
        raise APIError(
            422, "UC_07_M06", "Verifique o local e o link da defesa.", error.fields
        ) from error
    if mode != "presencial" and not url:
        raise APIError(422, "UC_07_M06", "Informe o link da reunião.")
    # Lock participants in a stable order to serialize overlapping bookings.
    people = {
        u.id_usuario: u
        for u in db.session.scalars(
            select(Usuario)
            .where(Usuario.id_usuario.in_(ids), Usuario.ativo_usuario.is_(True))
            .order_by(Usuario.id_usuario)
            .with_for_update(of=Usuario)
        )
    }
    for user_id in ids:
        teacher = db.session.get(Professor, user_id)
        if (
            user_id not in people
            or not teacher
            or not teacher.ativo_professor
            or not teacher.titulacao_professor
        ):
            raise APIError(422, "AVALIADOR_INVALIDO", "Selecione avaliadores ativos com titulação.")
        if not db.session.get(Avaliador, user_id):
            db.session.add(
                Avaliador(
                    id_avaliador=user_id,
                    tipo_avaliador=teacher.tipo_professor,
                    titulacao_avaliador=teacher.titulacao_professor,
                    instituicao_avaliador=teacher.instituicao_origem_professor or "UEA",
                )
            )
    item = (
        db.session.scalar(
            select(Banca)
            .where(Banca.id_banca == identifier, Banca.id_etapa_trabalho == stage.id_etapa_trabalho)
            .with_for_update()
        )
        if identifier
        else None
    )
    if identifier and not item:
        raise APIError(404, "BANCA_AUSENTE", "A banca não pertence a este trabalho.")
    if item and (item.snapshot_avaliacao_banca is not None or item.situacao_banca != "agendada"):
        raise APIError(409, "BANCA_BLOQUEADA", "A banca possui avaliações ou não está agendada.")
    conflicts = overlapping_members(start, end, ids, identifier)
    # Provision before the banca is added, so autoflush never sees a banca without rubric.
    rubric = official_rubric(class_id)
    if conflicts:
        names = ", ".join(people[person].nome_usuario for person in conflicts)
        raise APIError(
            409,
            "UC_07_M02",
            f"Já existe defesa neste horário para: {names}. Escolha outro intervalo.",
        )
    if item is None:
        if db.session.scalar(
            select(Banca.id_banca).where(
                Banca.id_etapa_trabalho == stage.id_etapa_trabalho,
                Banca.situacao_banca != "cancelada",
            )
        ):
            raise APIError(
                409,
                "BANCA_EXISTENTE",
                "O trabalho já tem uma banca. Edite o agendamento existente.",
            )
        item = Banca(
            id_etapa_trabalho=stage.id_etapa_trabalho,
            id_usuario_agendamento=g.user.id_usuario,
            uid_calendario_banca=f"{uuid4().hex}@sigg-tcc",
        )
        db.session.add(item)
    else:
        item.versao_banca += 1
    item.id_rubrica = rubric.id_rubrica
    item.id_arquivo_pdf_manuscrito = pdf.id_arquivo_pdf
    item.data_inicio_banca, item.data_fim_banca = start, end
    item.modalidade_banca_defesa, item.local_defesa_banca, item.url_defesa_banca_defesa = (
        mode,
        local,
        url,
    )
    db.session.flush()
    update_members(item, roles, end)
    recipients = [*people.values(), stage.trabalho.estudante.usuario]
    messages = defense_agenda.enqueue(item, recipients, identifier is not None)
    audit(
        g.user.id_usuario,
        "banca_atualizada" if identifier else "banca_agendada",
        "banca_defesa",
        item.id_banca,
    )
    db.session.flush()
    notification_ids = [notification.id_notificacao for notification in messages]
    db.session.commit()
    academic_mail.deliver(notification_ids)
    db.session.expire_all()
    return schedule_json(item), all(n.situacao_notificacao == "enviada" for n in messages)


def update_members(item, roles, end):
    desired = {person: role for role, group in roles.items() for person in group}
    retained = {}
    for member in item.membros:
        role = desired.get(member.id_docente)
        if role is None:
            db.session.delete(member)
        else:
            retained[member.id_docente] = member
            if member.papel_membro_banca == "presidente":
                member.papel_membro_banca = role
    # Release the unique presidency before assigning it to another retained member.
    db.session.flush()
    now = utcnow()
    for person, role in desired.items():
        member = retained.get(person)
        if member is None:
            member = Membro(
                id_banca=item.id_banca,
                id_docente=person,
                situacao_convite_membro_banca="aceito",
                data_resposta_membro_banca=now,
                data_inicio_acesso_membro_banca=now,
            )
            db.session.add(member)
        member.papel_membro_banca = role
        member.data_fim_acesso_membro_banca = end + timedelta(days=180)
