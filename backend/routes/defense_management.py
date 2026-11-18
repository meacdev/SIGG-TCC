from flask import Blueprint, jsonify
from sqlalchemy import select

from backend import document_models  # noqa: F401
from backend import validation as v
from backend.db import db
from backend.defense_models import Rubrica
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
    return jsonify(
        data=management.rubric(class_id, v.body(RUBRIC_FIELDS, RUBRIC_FIELDS), identifier)
    ), 200 if identifier else 201
