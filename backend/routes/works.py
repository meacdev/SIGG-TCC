from flask import Blueprint, g, jsonify, request
from sqlalchemy import exists, select

from backend import validation as v
from backend.db import db
from backend.defense_models import Orientacao, TrabalhoTcc
from backend.errors import APIError
from backend.models import Professor, Usuario
from backend.routes.catalogs import page_response
from backend.security import authenticated
from backend.serialization import resource_response
from backend.services import works

bp = Blueprint("works", __name__, url_prefix="/api/v1")


@bp.get("/meu-trabalho")
@bp.put("/meu-trabalho")
@authenticated()
def mine():
    if request.method == "GET":
        item = works.own_work()
        return resource_response(item, works.serialize(item)) if item else jsonify(data=None)
    data = v.body(works.FIELDS, works.REQUIRED, code="UC_06_M02")
    item, created = works.save(data)
    return resource_response(
        item,
        works.serialize(item),
        201 if created else 200,
        "UC_06_M01",
        "Trabalho registrado com sucesso!",
    )


@bp.get("/professores-orientacao")
@authenticated()
def teachers():
    if not g.user.estudante:
        raise APIError(
            403, "ACESSO_NEGADO", "O catálogo de orientação exige uma conta de estudante."
        )
    query = (
        select(Professor)
        .join(Usuario)
        .where(Professor.ativo_professor.is_(True), Usuario.ativo_usuario.is_(True))
        .order_by(Usuario.nome_usuario, Professor.id_professor)
    )
    return page_response(
        query,
        lambda d: {
            "id_professor": d.id_professor,
            "nome": d.usuario.nome_usuario,
            "titulacao": d.titulacao_professor,
        },
    )


@bp.get("/orientacoes")
@authenticated()
def assigned():
    if not g.user.professor or not g.user.professor.ativo_professor:
        raise APIError(403, "ACESSO_NEGADO", "Esta consulta exige docente ativo.")
    query = (
        select(TrabalhoTcc)
        .where(
            exists(
                select(Orientacao.id_orientacao).where(
                    Orientacao.id_trabalho_tcc == TrabalhoTcc.id_trabalho_tcc,
                    Orientacao.id_professor == g.user.id_usuario,
                    Orientacao.data_encerramento_orientacao.is_(None),
                )
            )
        )
        .order_by(TrabalhoTcc.id_trabalho_tcc)
    )
    return page_response(query, works.serialize)


@bp.get("/orientacoes/<int:work_id>")
@authenticated()
def detail(work_id):
    item = db.session.get(TrabalhoTcc, work_id)
    if (
        not item
        or not g.user.professor
        or not g.user.professor.ativo_professor
        or not any(o.id_professor == g.user.id_usuario for o in works.orientations(item))
    ):
        raise APIError(404, "TRABALHO_AUSENTE", "Trabalho não encontrado para seu vínculo.")
    return resource_response(item, works.serialize(item))


@bp.post("/orientacoes/<int:orientation_id>/resposta")
@authenticated()
def respond(orientation_id):
    record = db.session.get(Orientacao, orientation_id)
    if not record:
        raise APIError(404, "ORIENTACAO_AUSENTE", "Vínculo não encontrado.")
    item = db.session.scalar(
        select(TrabalhoTcc)
        .where(TrabalhoTcc.id_trabalho_tcc == record.id_trabalho_tcc)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    record = db.session.scalar(
        select(Orientacao)
        .where(Orientacao.id_orientacao == orientation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    data = v.body({"decisao"}, {"decisao"})
    works.respond(item, record, data["decisao"])
    return resource_response(
        item,
        works.serialize(item),
        code="ORIENTACAO_RESPONDIDA",
        message="Resposta de orientação registrada.",
    )
