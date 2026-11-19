from flask import Blueprint, current_app, jsonify
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend import document_models  # noqa: F401
from backend import validation as v
from backend.db import db
from backend.defense_models import Rubrica
from backend.errors import APIError
from backend.security import authenticated
from backend.services import classes
from backend.services import defense_management as management

bp = Blueprint("defense_management", __name__, url_prefix="/api/v1")
RUBRIC_FIELDS = {"nome", "situacao", "criterios"}


@bp.get("/turmas/<int:class_id>/rubricas")
@authenticated()
def rubrics(class_id):
    classes.get_class(class_id)
    items = db.session.scalars(
        select(Rubrica).where(Rubrica.id_turma == class_id).order_by(Rubrica.id_rubrica.desc())
    )
    return jsonify(data=[management.rubric_json(r) for r in items])


@bp.post("/turmas/<int:class_id>/rubricas")
@bp.patch("/turmas/<int:class_id>/rubricas/<int:identifier>")
@authenticated()
def save_rubric(class_id, identifier=None):
    data = v.body(RUBRIC_FIELDS | {"substituir"}, RUBRIC_FIELDS, "UC_08_M03")
    try:
        result = management.rubric(class_id, data, identifier)
    except SQLAlchemyError as error:
        raise rubric_save_error(error) from error
    return rubric_response(result, 200 if identifier else 201)


@bp.get("/turmas/<int:class_id>/rubricas/anteriores")
@authenticated()
def prior_rubrics(class_id):
    items = management.prior_rubrics(class_id)
    if not items:
        return jsonify(data=[], code="UC_08_M07", message="Nenhuma rubrica anterior deste curso.")
    return jsonify(data=items)


@bp.post("/turmas/<int:class_id>/rubricas/importacoes")
@authenticated()
def import_rubric(class_id):
    data = v.body({"origem"}, {"origem"})
    try:
        result = management.import_rubric(class_id, v.integer(data["origem"], "origem"))
    except SQLAlchemyError as error:
        raise rubric_save_error(error) from error
    return rubric_response(result, 201)


def rubric_save_error(error):
    current_app.logger.error("Falha ao salvar rubrica: %s", type(error).__name__)
    return APIError(503, "UC_08_M11", "Não foi possível salvar a rubrica. Tente novamente.")


def rubric_response(item, status):
    if item["situacao"] == "rascunho":
        return jsonify(data=item, code="UC_08_M05", message="Rubrica salva como rascunho."), status
    return jsonify(data=item, code="UC_08_M01", message="Rubrica salva com sucesso."), status
