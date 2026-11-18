"""Scheduling and rubric rules for the scoped academic management interface."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from flask import g
from sqlalchemy import func, select

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
from backend.services import classes, defenses


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


def rubric_json(item):
    return {
        "id": item.id_rubrica,
        "nome": item.nome_rubrica,
        "situacao": item.situacao_rubrica,
        "bloqueada": item.data_bloqueio_rubrica_avaliacao is not None,
        "criterios": [
            {
                "nome": c.nome_criterio_rubrica,
                "descricao": c.descricao_criterio_rubrica,
                "peso": str(c.peso_criterio_rubrica),
            }
            for c in item.criterios
        ],
    }


def rubric(class_id, data, identifier=None):
    classes.get_class(class_id, lock=True)
    status = v.choice(data["situacao"], "situacao", ("rascunho", "ativa", "inativa"))
    name = v.text(data["nome"], "nome", 150)
    raw = data["criterios"]
    if not isinstance(raw, list) or not 1 <= len(raw) <= 50:
        raise APIError(422, "CRITERIOS_INVALIDOS", "Informe de 1 a 50 critérios.")
    criteria = []
    for order, entry in enumerate(raw, 1):
        if not isinstance(entry, dict) or set(entry) != {"nome", "descricao", "peso"}:
            raise APIError(
                422, "CRITERIO_INVALIDO", "Informe nome, descrição e peso de cada critério."
            )
        weight = defenses.number(entry["peso"], "peso", 3, "100")
        if weight <= 0:
            raise APIError(422, "PESO_INVALIDO", "Os pesos devem ser positivos.")
        criteria.append(
            Criterio(
                nome_criterio_rubrica=v.text(entry["nome"], "nome", 150),
                descricao_criterio_rubrica=v.text(entry["descricao"], "descricao", 4000),
                peso_criterio_rubrica=weight,
                pontuacao_maxima_criterio_rubrica=Decimal(10),
                ordem_criterio_rubrica=order,
            )
        )
    if len({c.nome_criterio_rubrica.casefold() for c in criteria}) != len(criteria):
        raise APIError(422, "CRITERIO_DUPLICADO", "Use nomes distintos para cada critério.")
    if status == "ativa" and sum(c.peso_criterio_rubrica for c in criteria) not in {10, 100}:
        raise APIError(422, "PESO_TOTAL", "Para ativar, os pesos devem somar 100% ou 10.")
    item = (
        db.session.scalar(
            select(Rubrica)
            .where(Rubrica.id_rubrica == identifier, Rubrica.id_turma == class_id)
            .with_for_update()
        )
        if identifier
        else None
    )
    if identifier and not item:
        raise APIError(404, "RUBRICA_AUSENTE", "A rubrica não pertence à turma.")
    if item and item.data_bloqueio_rubrica_avaliacao:
        raise APIError(
            409,
            "RUBRICA_BLOQUEADA",
            "Uma avaliação já usa esta rubrica. Duplique-a para outra turma.",
        )
    if status == "ativa" and db.session.scalar(
        select(Rubrica.id_rubrica).where(
            Rubrica.id_turma == class_id,
            Rubrica.situacao_rubrica == "ativa",
            Rubrica.id_rubrica != (identifier or 0),
        )
    ):
        raise APIError(409, "RUBRICA_ATIVA", "Já existe uma rubrica ativa na turma.")
    if (
        item
        and status != "ativa"
        and db.session.scalar(
            select(Banca.id_banca)
            .where(Banca.id_rubrica == identifier, Banca.situacao_banca != "cancelada")
            .limit(1)
        )
    ):
        raise APIError(409, "RUBRICA_EM_USO", "A rubrica está vinculada a uma banca vigente.")
    if item is None:
        version = (
            db.session.scalar(
                select(func.max(Rubrica.versao_rubrica)).where(
                    Rubrica.id_turma == class_id, Rubrica.nome_rubrica == name
                )
            )
            or 0
        )
        item = Rubrica(
            id_turma=class_id, id_usuario_criacao=g.user.id_usuario, versao_rubrica=version + 1
        )
        db.session.add(item)
    else:
        item.criterios.clear()
        db.session.flush()
    item.nome_rubrica = name
    item.situacao_rubrica = status
    item.criterios = criteria
    item.data_modificacao_rubrica_avaliacao = utcnow()
    db.session.flush()
    audit(g.user.id_usuario, "rubrica_salva", "rubrica_avaliacao", item.id_rubrica)
    db.session.commit()
    return rubric_json(item)


def timestamp(value):
    try:
        result = datetime.fromisoformat(value)
        if result.tzinfo is None:
            raise ValueError
        return result.astimezone(UTC)
    except ValueError, TypeError, OverflowError:
        raise APIError(
            422, "DATA_INVALIDA", "Informe uma data e um horário com fuso válido."
        ) from None


def schedule_json(banca):
    return {
        "id": banca.id_banca,
        "etapa": banca.id_etapa_trabalho,
        "rubrica": banca.id_rubrica,
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


def has_overlap(start, end, ids, identifier=None):
    return (
        db.session.scalar(
            select(Banca.id_banca)
            .join(Membro)
            .where(
                Banca.id_banca != (identifier or 0),
                Banca.situacao_banca != "cancelada",
                Banca.data_inicio_banca < end,
                Banca.data_fim_banca > start,
                Membro.id_docente.in_(ids),
            )
            .limit(1)
        )
        is not None
    )


def schedule(class_id, data, identifier=None):
    turma = classes.get_class(class_id, lock=True)
    stage = scoped_stage(class_id, v.integer(data["etapa"], "etapa"), lock=True)
    president = advisor(stage)
    if (
        not turma.ativa_turma
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
            "MANUSCRITO_AUSENTE",
            "O estudante precisa enviar o manuscrito antes do agendamento.",
        )
    rubric_id = v.integer(data["rubrica"], "rubrica")
    active = db.session.scalar(
        select(Rubrica).where(
            Rubrica.id_rubrica == rubric_id,
            Rubrica.id_turma == class_id,
            Rubrica.situacao_rubrica == "ativa",
        )
    )
    if not active:
        raise APIError(
            422, "RUBRICA_AUSENTE", "Ative uma rubrica desta turma antes do agendamento."
        )
    start, end = timestamp(data["inicio"]), timestamp(data["fim"])
    if not utcnow() < start < end:
        raise APIError(422, "DATA_INVALIDA", "Informe início futuro e término posterior ao início.")
    mode = v.choice(data["modalidade"], "modalidade", ("presencial", "remota", "hibrida"))
    url = v.url(data.get("url"), "url") if mode != "presencial" else None
    if mode != "presencial" and not url:
        raise APIError(422, "LINK_OBRIGATORIO", "Informe o link da reunião.")
    local = v.text(data.get("local"), "local", 2000) if mode != "remota" else url
    roles = {
        "presidente": [president],
        "examinador": data["titulares"],
        "suplente": data["suplentes"],
    }
    if not isinstance(roles["examinador"], list) or not isinstance(roles["suplente"], list):
        raise APIError(422, "BANCA_INCOMPLETA", "Selecione titulares e suplentes.")
    if len(roles["examinador"]) < 2 or len(roles["suplente"]) < 1:
        raise APIError(
            422, "BANCA_INCOMPLETA", "Selecione dois titulares além do orientador e um suplente."
        )
    ids = [v.integer(i, "membro") for group in roles.values() for i in group]
    if len(ids) > 20 or len(ids) != len(set(ids)):
        raise APIError(422, "BANCA_INVALIDA", "Selecione até 20 pessoas distintas.")
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
    if has_overlap(start, end, ids, identifier):
        raise APIError(
            409,
            "HORARIO_OCUPADO",
            "Um integrante já tem defesa neste horário. Escolha outro intervalo.",
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
        for member in item.membros:
            db.session.delete(member)
        db.session.flush()
        item.versao_banca += 1
    item.id_rubrica = rubric_id
    item.id_arquivo_pdf_manuscrito = pdf.id_arquivo_pdf
    item.data_inicio_banca, item.data_fim_banca = start, end
    item.modalidade_banca_defesa, item.local_defesa_banca, item.url_defesa_banca_defesa = (
        mode,
        local,
        url,
    )
    db.session.flush()
    for role, group in roles.items():
        for person in group:
            db.session.add(
                Membro(
                    id_banca=item.id_banca,
                    id_docente=person,
                    papel_membro_banca=role,
                    situacao_convite_membro_banca="aceito",
                    data_resposta_membro_banca=utcnow(),
                    data_inicio_acesso_membro_banca=utcnow(),
                    data_fim_acesso_membro_banca=end + timedelta(days=180),
                )
            )
    from backend.services import defense_agenda

    recipients = [*people.values(), stage.trabalho.estudante.usuario]
    defense_agenda.enqueue(item, recipients, identifier is not None)
    audit(
        g.user.id_usuario,
        "banca_atualizada" if identifier else "banca_agendada",
        "banca_defesa",
        item.id_banca,
    )
    db.session.commit()
    db.session.expire_all()
    return schedule_json(item)
