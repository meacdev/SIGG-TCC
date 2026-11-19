"""Scheduling and rubric rules for the scoped academic management interface."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from flask import g
from sqlalchemy import func, select, tuple_

from backend import validation as v
from backend.audit import audit
from backend.db import db, utcnow
from backend.defense_models import (
    Avaliacao,
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
from backend.models import PeriodoLetivo, Professor, Turma, Usuario
from backend.serialization import iso
from backend.services import academic_mail, classes, defense_agenda, defenses, users


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


def rubric_json(item):
    return {
        "id": item.id_rubrica,
        "nome": item.nome_rubrica,
        "situacao": item.situacao_rubrica,
        "versao": item.versao_rubrica,
        "bloqueada": item.data_bloqueio_rubrica_avaliacao is not None,
        "criterios": [
            {
                "nome": c.nome_criterio_rubrica,
                "descricao": c.descricao_criterio_rubrica,
                "peso": format(c.peso_criterio_rubrica, ".3f"),
            }
            for c in item.criterios
        ],
    }


def prior_query(turma):
    return (
        select(Rubrica, PeriodoLetivo)
        .join(Turma, Turma.id_turma == Rubrica.id_turma)
        .join(PeriodoLetivo, PeriodoLetivo.id_periodo_letivo == Turma.id_periodo_letivo)
        .where(
            Turma.id_curso == turma.id_curso,
            tuple_(PeriodoLetivo.ano_periodo_letivo, PeriodoLetivo.semestre_periodo_letivo)
            < (turma.periodo.ano_periodo_letivo, turma.periodo.semestre_periodo_letivo),
        )
    )


def prior_rubrics(class_id):
    turma = classes.get_class(class_id)
    query = prior_query(turma).order_by(
        PeriodoLetivo.ano_periodo_letivo.desc(),
        PeriodoLetivo.semestre_periodo_letivo.desc(),
        Rubrica.id_rubrica.desc(),
    )
    return [
        {
            "id": item.id_rubrica,
            "nome": item.nome_rubrica,
            "versao": item.versao_rubrica,
            "periodo": f"{period.ano_periodo_letivo}.{period.semestre_periodo_letivo}",
        }
        for item, period in db.session.execute(query)
    ]


def import_rubric(class_id, source_id):
    turma = classes.get_class(class_id, lock=True)
    source = db.session.scalar(
        prior_query(turma).where(Rubrica.id_rubrica == source_id).with_for_update(of=Rubrica)
    )
    if not source:
        raise APIError(404, "RUBRICA_AUSENTE", "Selecione uma rubrica anterior deste curso.")
    item = new_rubric(class_id, source.nome_rubrica)
    item.criterios = [
        Criterio(
            nome_criterio_rubrica=c.nome_criterio_rubrica,
            descricao_criterio_rubrica=c.descricao_criterio_rubrica,
            peso_criterio_rubrica=c.peso_criterio_rubrica,
            pontuacao_maxima_criterio_rubrica=c.pontuacao_maxima_criterio_rubrica,
            ordem_criterio_rubrica=c.ordem_criterio_rubrica,
        )
        for c in source.criterios
    ]
    db.session.flush()
    audit(g.user.id_usuario, "rubrica_importada", "rubrica_avaliacao", item.id_rubrica)
    db.session.commit()
    return rubric_json(item)


def next_rubric_version(class_id, name):
    version = db.session.scalar(
        select(func.max(Rubrica.versao_rubrica)).where(
            Rubrica.id_turma == class_id, Rubrica.nome_rubrica == name
        )
    )
    return (version or 0) + 1


def new_rubric(class_id, name):
    item = Rubrica(
        id_turma=class_id,
        id_usuario_criacao=g.user.id_usuario,
        nome_rubrica=name,
        versao_rubrica=next_rubric_version(class_id, name),
    )
    db.session.add(item)
    return item


def ensure_rubric_editable(item, deactivating=False):
    if item.data_bloqueio_rubrica_avaliacao or db.session.scalar(
        select(Avaliacao.id_avaliacao)
        .join(Membro)
        .join(Banca)
        .where(Banca.id_rubrica == item.id_rubrica)
        .limit(1)
    ):
        raise APIError(409, "UC_08_M04", "Uma avaliação já usa esta rubrica.")
    if deactivating and db.session.scalar(
        select(Banca.id_banca)
        .where(Banca.id_rubrica == item.id_rubrica, Banca.situacao_banca != "cancelada")
        .limit(1)
    ):
        raise APIError(409, "RUBRICA_EM_USO", "A rubrica está vinculada a uma banca vigente.")


def required_rubric_text(value, field, maximum):
    try:
        return v.text(value, field, maximum)
    except APIError as error:
        raise APIError(
            422, "UC_08_M03", "Preencha o nome e a descrição dos critérios.", error.fields
        ) from error


def rubric(class_id, data, identifier=None):
    classes.get_class(class_id, lock=True)
    status = v.choice(data["situacao"], "situacao", ("rascunho", "ativa", "inativa"))
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
    if item:
        ensure_rubric_editable(item)
        if item.situacao_rubrica == "ativa" and status != "ativa":
            raise APIError(409, "UC_08_M08", "Ative uma substituta antes de inativar esta rubrica.")
    name = required_rubric_text(data["nome"], "nome", 150)
    raw = data["criterios"]
    if not isinstance(raw, list) or not 1 <= len(raw) <= 50:
        raise APIError(422, "UC_08_M03", "Informe de 1 a 50 critérios.")
    fields = []
    for entry in raw:
        if not isinstance(entry, dict) or set(entry) != {"nome", "descricao", "peso"}:
            raise APIError(422, "UC_08_M03", "Informe nome, descrição e peso de cada critério.")
        if entry["peso"] is None or entry["peso"] == "":
            raise APIError(422, "UC_08_M03", "Informe o peso de cada critério.")
        fields.append(
            (
                required_rubric_text(entry["nome"], "nome", 150),
                required_rubric_text(entry["descricao"], "descricao", 4000),
                entry["peso"],
            )
        )
    criteria = []
    for order, (name_criterion, description, value) in enumerate(fields, 1):
        try:
            weight = defenses.number(value, "peso", 3, "100")
        except APIError as error:
            raise APIError(422, "UC_08_M06", "Informe um peso positivo de até 100.") from error
        if weight <= 0:
            raise APIError(422, "UC_08_M06", "Os pesos devem ser positivos.")
        criteria.append(
            Criterio(
                nome_criterio_rubrica=name_criterion,
                descricao_criterio_rubrica=description,
                peso_criterio_rubrica=weight,
                pontuacao_maxima_criterio_rubrica=Decimal(10),
                ordem_criterio_rubrica=order,
            )
        )
    if len({c.nome_criterio_rubrica.casefold() for c in criteria}) != len(criteria):
        raise APIError(422, "CRITERIO_DUPLICADO", "Use nomes distintos para cada critério.")
    total = sum(c.peso_criterio_rubrica for c in criteria)
    if status == "ativa" and total not in {10, 100}:
        raise APIError(422, "UC_08_M02", f"Os pesos devem somar 100 ou 10. Soma atual: {total:f}.")
    replacement = data.get("substituir")
    if replacement is not None:
        replacement = v.integer(replacement, "substituir")
    if status == "ativa":
        active = db.session.scalar(
            select(Rubrica)
            .where(
                Rubrica.id_turma == class_id,
                Rubrica.situacao_rubrica == "ativa",
                Rubrica.id_rubrica != (identifier or 0),
            )
            .with_for_update()
        )
        if active:
            if replacement != active.id_rubrica:
                raise APIError(409, "RUBRICA_ATIVA", "Confirme a substituição da rubrica ativa.")
            ensure_rubric_editable(active, deactivating=True)
            active.situacao_rubrica = "inativa"
            active.data_modificacao_rubrica_avaliacao = utcnow()
            audit(g.user.id_usuario, "rubrica_inativada", "rubrica_avaliacao", active.id_rubrica)
            db.session.flush()
    if item is None:
        item = new_rubric(class_id, name)
    else:
        if item.nome_rubrica != name:
            item.versao_rubrica = next_rubric_version(class_id, name)
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
        raise APIError(422, "UC_07_M06", "Informe uma data e um horário com fuso válido.") from None


def schedule_json(banca):
    return {
        "id": banca.id_banca,
        "etapa": banca.id_etapa_trabalho,
        "titulo": banca.etapa.trabalho.titulo_trabalho_tcc,
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
    item.id_rubrica = rubric_id
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
