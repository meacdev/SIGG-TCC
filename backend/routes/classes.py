from flask import Blueprint, jsonify, request

from backend import validation as v
from backend.db import db
from backend.errors import APIError
from backend.models import PeriodoLetivo, Turma
from backend.security import authenticated
from backend.serialization import check_version, class_json, resource_response
from backend.services import classes

bp = Blueprint("classes", __name__, url_prefix="/api/v1/turmas")


@bp.post("")
@authenticated()
def create():
    data = v.body(classes.CREATE_FIELDS, classes.CREATE_FIELDS)
    item, code = classes.create_class(data)
    result = class_json(item) | {"codigo_acesso": code}
    response = resource_response(item, result, 201, "UC_02_M01", "Turma cadastrada com sucesso!")
    response.headers["Location"] = f"/api/v1/turmas/{item.id_turma}"
    return response


@bp.get("")
@authenticated()
def list_classes():
    page, size = v.pagination()
    query = classes.visible_classes()
    if "id_curso" in request.args:
        try:
            course_id = int(request.args["id_curso"])
        except ValueError:
            raise APIError(422, "VALIDACAO", "Curso inválido.") from None
        query = query.where(Turma.id_curso == v.integer(course_id, "id_curso"))
    if "periodo_letivo" in request.args:
        year, semester = v.period(request.args["periodo_letivo"])
        query = query.join(PeriodoLetivo).where(
            PeriodoLetivo.ano_periodo_letivo == year,
            PeriodoLetivo.semestre_periodo_letivo == semester,
        )
    if "nivel_turma" in request.args:
        try:
            level = int(request.args["nivel_turma"])
        except ValueError:
            raise APIError(422, "VALIDACAO", "Nível inválido.") from None
        query = query.where(Turma.nivel_turma == v.integer(level, "nivel_turma", 1, 2))
    if "ativa_turma" in request.args:
        active = request.args["ativa_turma"]
        if active not in {"true", "false"}:
            raise APIError(422, "VALIDACAO", "Informe ativa_turma=true ou false.")
        query = query.where(Turma.ativa_turma.is_(active == "true"))
    result = db.paginate(
        query.order_by(Turma.id_turma), page=page, per_page=size, max_per_page=100, error_out=False
    )
    return jsonify(
        data=[class_json(item) for item in result.items],
        meta={"page": page, "per_page": size, "total": result.total, "pages": result.pages},
    )


@bp.get("/<int:class_id>")
@authenticated()
def detail(class_id):
    item = classes.get_class(class_id)
    return resource_response(item, class_json(item))


@bp.patch("/<int:class_id>")
@bp.delete("/<int:class_id>")
@authenticated()
def modify(class_id):
    item = classes.get_class(class_id, lock=True)
    check_version(item)
    if request.method == "DELETE":
        classes.deactivate_class(item)
        return "", 204
    classes.update_class(item, v.body(classes.UPDATE_FIELDS))
    return resource_response(item, class_json(item))


@bp.post("/<int:class_id>/codigo-acesso")
@authenticated()
def rotate(class_id):
    item = classes.get_class(class_id, lock=True)
    check_version(item)
    code = classes.rotate_code(item)
    return resource_response(item, class_json(item) | {"codigo_acesso": code})
