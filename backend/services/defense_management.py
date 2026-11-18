"""Scheduling and rubric rules for the scoped academic management interface."""

from decimal import Decimal

from flask import g
from sqlalchemy import func, select

from backend import validation as v
from backend.audit import audit
from backend.db import db, utcnow
from backend.defense_models import (
    Banca,
    Criterio,
    Rubrica,
)
from backend.errors import APIError
from backend.services import classes, defenses


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
