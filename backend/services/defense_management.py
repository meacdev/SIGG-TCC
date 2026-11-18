"""Scheduling and rubric rules for the scoped academic management interface."""

from decimal import Decimal

from flask import g
from sqlalchemy import func, select, tuple_

from backend import validation as v
from backend.audit import audit
from backend.db import db, utcnow
from backend.defense_models import Avaliacao, Banca, Criterio, Membro, Rubrica
from backend.errors import APIError
from backend.models import PeriodoLetivo, Turma
from backend.services import classes, defenses


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
