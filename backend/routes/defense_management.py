from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend import validation as v
from backend.audit import audit
from backend.db import db, utcnow
from backend.defense_models import (
    Banca,
    Etapa,
    Manuscrito,
    Matricula,
    Orientacao,
    Rubrica,
    TrabalhoTcc,
)
from backend.document_models import ArquivoPDF
from backend.errors import APIError
from backend.models import Professor, Usuario
from backend.routes.documents import pdf_response
from backend.security import authenticated
from backend.services import classes, pdf_storage
from backend.services import defense_management as management

bp = Blueprint("defense_management", __name__, url_prefix="/api/v1")
RUBRIC_FIELDS = {"nome", "situacao", "criterios"}
SCHEDULE_FIELDS = {
    "etapa",
    "rubrica",
    "inicio",
    "fim",
    "local",
    "modalidade",
    "url",
    "titulares",
    "suplentes",
}


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


@bp.get("/turmas/<int:class_id>/bancas")
@authenticated()
def schedules(class_id):
    turma = classes.get_class(class_id)
    stages = db.session.execute(
        select(Etapa, Usuario)
        .join(Matricula)
        .join(TrabalhoTcc)
        .join(Orientacao, Orientacao.id_trabalho_tcc == TrabalhoTcc.id_trabalho_tcc)
        .join(Usuario, Usuario.id_usuario == Orientacao.id_professor)
        .where(
            Matricula.id_turma == class_id,
            Matricula.situacao_matricula_turma == "ativa",
            Etapa.situacao_etapa_trabalho == "em_andamento",
            TrabalhoTcc.situacao_trabalho_tcc == "em_andamento",
            Orientacao.papel_orientacao == "orientador",
            Orientacao.situacao_aceite_orientacao == "aceito",
            Orientacao.data_encerramento_orientacao.is_(None),
        )
        .order_by(TrabalhoTcc.titulo_trabalho_tcc)
    )
    work = [
        {
            "id": e.id_etapa_trabalho,
            "titulo": e.trabalho.titulo_trabalho_tcc,
            "orientador": orientador.id_usuario,
            "nome_orientador": orientador.nome_usuario,
            "estudante": e.trabalho.estudante.usuario.nome_usuario,
            "nivel": turma.nivel_turma,
            "manuscrito": management.latest_pdf(e) is not None,
        }
        for e, orientador in stages
    ]
    items = db.session.scalars(
        select(Banca)
        .join(Etapa)
        .join(Matricula)
        .where(Matricula.id_turma == class_id, Banca.situacao_banca == "agendada")
        .order_by(Banca.data_inicio_banca.desc())
    )
    return jsonify(data={"trabalhos": work, "bancas": [management.schedule_json(b) for b in items]})


@bp.get("/turmas/<int:class_id>/bancas/<int:identifier>")
@authenticated()
def schedule_detail(class_id, identifier):
    classes.get_class(class_id)
    item = db.session.scalar(
        select(Banca)
        .join(Etapa)
        .join(Matricula)
        .where(Banca.id_banca == identifier, Matricula.id_turma == class_id)
    )
    if not item:
        raise APIError(404, "BANCA_AUSENTE", "Banca não encontrada nesta turma.")
    if item.situacao_banca != "agendada" or item.snapshot_avaliacao_banca is not None:
        raise APIError(409, "BANCA_BLOQUEADA", "A banca possui avaliações ou não está agendada.")
    return jsonify(data=management.schedule_json(item))


@bp.get("/turmas/<int:class_id>/avaliadores")
@authenticated()
def examiners(class_id):
    classes.get_class(class_id)
    term = request.args.get("q", "")[:100].strip()
    query = (
        select(Professor)
        .join(Usuario)
        .where(Professor.ativo_professor.is_(True), Usuario.ativo_usuario.is_(True))
    )
    if term:
        query = query.where(Usuario.nome_usuario.icontains(term, autoescape=True))
    return jsonify(
        data=[
            {
                "id": p.id_professor,
                "nome": p.usuario.nome_usuario,
                "tipo": p.tipo_professor,
                "titulacao": p.titulacao_professor,
                "instituicao": p.instituicao_origem_professor,
            }
            for p in db.session.scalars(query.order_by(Usuario.nome_usuario).limit(100))
        ]
    )


@bp.post("/turmas/<int:class_id>/avaliadores/externos")
@authenticated()
def register_external(class_id):
    fields = {"nome", "email", "titulacao", "instituicao"}
    data = v.body(fields, fields, "UC_07_M05")
    return jsonify(data=management.register_external(class_id, data)), 201


@bp.post("/turmas/<int:class_id>/bancas/disponibilidade")
@authenticated()
def availability(class_id):
    classes.get_class(class_id)
    fields = {"etapa", "inicio", "fim", "membros", "banca"}
    payload = v.body(fields, fields - {"banca"})
    stage = management.scoped_stage(class_id, v.integer(payload["etapa"], "etapa"))
    start, end = management.timestamp(payload["inicio"]), management.timestamp(payload["fim"])
    if start >= end:
        raise APIError(422, "DATA_INVALIDA", "O horário de término deve ser posterior ao início.")
    members = payload["membros"]
    if not isinstance(members, list) or len(members) > 19:
        raise APIError(422, "BANCA_INVALIDA", "Selecione até 19 integrantes além do orientador.")
    ids = [v.integer(person, "membro") for person in members]
    orientador = management.advisor(stage)
    if orientador:
        ids.append(orientador)
    identifier = payload.get("banca")
    if identifier is not None:
        banca = db.session.get(Banca, v.integer(identifier, "banca"))
        if not banca or banca.id_etapa_trabalho != stage.id_etapa_trabalho:
            raise APIError(404, "BANCA_AUSENTE", "A banca não pertence a este trabalho.")
    conflicts = management.overlapping_members(start, end, ids, identifier)
    return jsonify(data={"disponivel": not conflicts, "conflitos": conflicts})


@bp.post("/turmas/<int:class_id>/bancas")
@bp.patch("/turmas/<int:class_id>/bancas/<int:identifier>")
@authenticated()
def save_schedule(class_id, identifier=None):
    payload = v.body(SCHEDULE_FIELDS, SCHEDULE_FIELDS - {"local", "url"})
    try:
        data, sent = management.schedule(class_id, payload, identifier)
    except SQLAlchemyError as error:
        current_app.logger.error("Falha ao confirmar agendamento: %s", type(error).__name__)
        raise APIError(
            503,
            "UC_07_M07",
            "Não foi possível confirmar. Consulte a lista de bancas antes de tentar novamente.",
        ) from error
    message = (
        "Banca salva e convites enviados."
        if sent
        else "Banca salva. Os avisos pendentes ficaram na fila para nova tentativa."
    )
    return jsonify(
        data=data, code="UC_07_M01" if sent else "CONVITES_PENDENTES", message=message
    ), 200 if identifier else 201


@bp.get("/turmas/<int:class_id>/etapas/<int:stage_id>/manuscrito")
@authenticated()
def preview_manuscript(class_id, stage_id):
    classes.get_class(class_id)
    stage = management.scoped_stage(class_id, stage_id)
    manuscript = management.latest_pdf(stage)
    if not manuscript:
        raise APIError(404, "UC_07_M04", "Este trabalho ainda não tem manuscrito.")
    return pdf_response(db.session.get(ArquivoPDF, manuscript.id_arquivo_pdf))


@bp.post("/etapas/<int:stage_id>/manuscritos")
@authenticated()
def upload(stage_id):
    stage = db.session.scalar(
        select(Etapa).where(Etapa.id_etapa_trabalho == stage_id).with_for_update()
    )
    if (
        not stage
        or stage.trabalho.id_estudante != g.user.id_usuario
        or stage.matricula.situacao_matricula_turma != "ativa"
        or stage.trabalho.situacao_trabalho_tcc != "em_andamento"
    ):
        raise APIError(404, "ETAPA_AUSENTE", "Trabalho ativo não encontrado.")
    request.max_content_length = pdf_storage.MAX_PDF_BYTES + 65536
    if set(request.files) != {"arquivo"} or len(request.files.getlist("arquivo")) != 1:
        raise APIError(422, "PDF_OBRIGATORIO", "Selecione um PDF do manuscrito.")
    attachment = request.files["arquivo"]
    previous = management.latest_pdf(stage)
    version = previous.versao_manuscrito_trabalho + 1 if previous else 1
    file = pdf_storage.save(
        attachment.read(pdf_storage.MAX_PDF_BYTES + 1),
        attachment.filename or "manuscrito.pdf",
        g.user.id_usuario,
    )
    try:
        db.session.add(
            Manuscrito(
                id_etapa_trabalho=stage_id,
                id_arquivo_pdf=file.id_arquivo_pdf,
                versao_manuscrito_trabalho=version,
            )
        )
        audit(g.user.id_usuario, "manuscrito_enviado", "etapa_trabalho", stage_id)
        db.session.commit()
    except Exception:
        pdf_storage.discard([file])
        db.session.rollback()
        raise
    return jsonify(data={"versao": version}), 201


@bp.get("/bancas/<int:identifier>/manuscrito")
@authenticated()
def manuscript(identifier):
    item = db.session.get(Banca, identifier)
    if not item or item.situacao_banca == "cancelada":
        raise APIError(404, "MANUSCRITO_AUSENTE", "Manuscrito não disponível.")
    now = utcnow()
    user = g.user.id_usuario
    eligible = any(
        m.id_docente == user
        and m.situacao_convite_membro_banca == "aceito"
        and m.data_inicio_acesso_membro_banca <= now <= m.data_fim_acesso_membro_banca
        for m in item.membros
    )
    if item.etapa.trabalho.id_estudante != user and not eligible:
        classes.get_class(item.etapa.matricula.id_turma)
    return pdf_response(db.session.get(ArquivoPDF, item.id_arquivo_pdf_manuscrito))
