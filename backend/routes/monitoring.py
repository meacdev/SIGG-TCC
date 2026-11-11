from flask import Blueprint, jsonify, request
from sqlalchemy import select

from backend import validation as v
from backend.academic_models import Reuniao
from backend.db import db
from backend.defense_models import Etapa, Matricula
from backend.errors import APIError
from backend.routes.catalogs import page_response
from backend.security import authenticated, limiter
from backend.services import meetings, monitoring

bp = Blueprint("monitoring", __name__, url_prefix="/api/v1/turmas")


@bp.get("/<int:class_id>/monitoramento")
@authenticated()
def overview(class_id):
    monitoring.get_class(class_id)
    status = request.args.get("status", "todos")
    if status not in {"todos", "inativos"}:
        raise APIError(422, "VALIDACAO", "Status deve ser todos ou inativos.")
    return jsonify(monitoring.overview(class_id, status == "inativos"))


@bp.get("/<int:class_id>/monitoramento/<int:enrollment_id>/atas")
@authenticated()
def history(class_id, enrollment_id):
    monitoring.get_class(class_id)
    member = db.session.get(Matricula, enrollment_id)
    if not member or member.id_turma != class_id or member.situacao_matricula_turma != "ativa":
        raise APIError(404, "MATRICULA_AUSENTE", "Estudante não encontrado na turma selecionada.")
    stage = db.session.scalar(select(Etapa).where(Etapa.id_matricula_turma == enrollment_id))
    return page_response(
        select(Reuniao)
        .where(Reuniao.id_etapa_trabalho == (stage.id_etapa_trabalho if stage else -1))
        .order_by(
            Reuniao.data_encontro_reuniao_orientacao.asc(), Reuniao.id_reuniao_orientacao.asc()
        ),
        meetings.serialize,
    )


@bp.post("/<int:class_id>/monitoramento/previa")
@authenticated()
@limiter.limit("10 per minute")
def preview(class_id):
    turma = monitoring.get_class(class_id)
    data = v.body({"ids_matriculas", "todos_inativos", "ids_excluidas"})
    return jsonify(data=monitoring.prepare(turma, data)), 201


@bp.post("/<int:class_id>/monitoramento/lotes/<string:batch_id>/confirmar")
@authenticated()
@limiter.limit("5 per minute; 30 per hour")
def confirm(class_id, batch_id):
    turma = monitoring.get_class(class_id, lock=True)
    v.body(set())
    result, code, message = monitoring.confirm(turma, batch_id)
    return jsonify(data=result, code=code, message=message)
