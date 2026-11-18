from io import BytesIO

from flask import Blueprint, g, jsonify, request, send_file
from sqlalchemy import select

from backend import validation as v
from backend.audit import audit
from backend.db import db, utcnow
from backend.defense_models import Banca, Etapa, Manuscrito, Matricula, Rubrica
from backend.document_models import ArquivoPDF
from backend.errors import APIError
from backend.models import Professor, Usuario
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
    return jsonify(
        data=management.rubric(class_id, v.body(RUBRIC_FIELDS, RUBRIC_FIELDS), identifier)
    ), 200 if identifier else 201


@bp.get("/turmas/<int:class_id>/bancas")
@authenticated()
def schedules(class_id):
    classes.get_class(class_id)
    stages = db.session.scalars(
        select(Etapa)
        .join(Matricula)
        .where(Matricula.id_turma == class_id, Matricula.situacao_matricula_turma == "ativa")
    )
    work = [
        {
            "id": e.id_etapa_trabalho,
            "titulo": e.trabalho.titulo_trabalho_tcc,
            "orientador": management.advisor(e),
            "manuscrito": management.latest_pdf(e) is not None,
        }
        for e in stages
        if e.trabalho.situacao_trabalho_tcc == "em_andamento"
    ]
    items = db.session.scalars(
        select(Banca)
        .join(Etapa)
        .join(Matricula)
        .where(Matricula.id_turma == class_id)
        .order_by(Banca.data_inicio_banca.desc())
    )
    return jsonify(data={"trabalhos": work, "bancas": [management.schedule_json(b) for b in items]})


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
    return jsonify(data={"disponivel": not management.has_overlap(start, end, ids, identifier)})


@bp.post("/turmas/<int:class_id>/bancas")
@bp.patch("/turmas/<int:class_id>/bancas/<int:identifier>")
@authenticated()
def save_schedule(class_id, identifier=None):
    return jsonify(
        data=management.schedule(
            class_id, v.body(SCHEDULE_FIELDS, SCHEDULE_FIELDS - {"local", "url"}), identifier
        )
    ), 200 if identifier else 201


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
    file = db.session.get(ArquivoPDF, item.id_arquivo_pdf_manuscrito)
    return send_file(
        BytesIO(pdf_storage.read(file)),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=file.nome_original_arquivo_pdf,
    )
