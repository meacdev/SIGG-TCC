from flask import Blueprint, request
from sqlalchemy import select

from backend import validation as v
from backend.academic_models import Reuniao
from backend.defense_models import Etapa, Matricula
from backend.routes.catalogs import page_response
from backend.security import authenticated
from backend.serialization import resource_response
from backend.services import meetings

bp = Blueprint("meetings", __name__, url_prefix="/api/v1")


@bp.get("/trabalhos-reunioes")
@authenticated()
def stages():
    return page_response(
        meetings.visible_stages().order_by(Etapa.id_etapa_trabalho), meetings.stage_json
    )


@bp.get("/etapas/<int:stage_id>/reunioes")
@bp.post("/etapas/<int:stage_id>/reunioes")
@authenticated()
def records(stage_id):
    stage = meetings.get_stage(stage_id, lock=request.method == "POST")
    if request.method == "POST":
        data = v.body({"data_encontro", "resumo"}, {"data_encontro", "resumo"}, code="UC_05_M02")
        item = meetings.register(stage, data)
        return resource_response(
            stage.trabalho,
            meetings.serialize(item),
            201,
            "UC_05_M01",
            "Ata registrada com sucesso!",
        )
    return page_response(
        select(Reuniao)
        .where(Reuniao.id_etapa_trabalho == stage_id)
        .order_by(
            Reuniao.data_encontro_reuniao_orientacao.desc(), Reuniao.id_reuniao_orientacao.desc()
        ),
        meetings.serialize,
    )


@bp.get("/acompanhamento-reunioes")
@authenticated()
def attendance():
    query = (
        select(Matricula)
        .where(
            Matricula.id_turma.in_(meetings.teacher_classes()),
            Matricula.situacao_matricula_turma == "ativa",
        )
        .order_by(Matricula.id_turma, Matricula.id_matricula_turma)
    )
    return page_response(query, meetings.attendance)
