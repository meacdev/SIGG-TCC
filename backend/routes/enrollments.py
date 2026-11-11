from flask import Blueprint, g, request
from sqlalchemy import or_, select

from backend import validation as v
from backend.db import db
from backend.defense_models import Matricula
from backend.errors import APIError
from backend.models import Aluno, Usuario
from backend.routes.catalogs import page_response
from backend.security import authenticated, limiter
from backend.serialization import check_version, resource_response
from backend.services import classes, enrollments

bp = Blueprint("enrollments", __name__, url_prefix="/api/v1")


@bp.get("/turmas/<int:class_id>/estudantes")
@authenticated()
def search(class_id):
    turma = classes.get_class(class_id)
    query = v.text(request.args.get("q"), "q", 100, 2)
    # Escape LIKE wildcards so a search cannot accidentally enumerate the entire course.
    term = "%" + query.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_") + "%"
    students = (
        select(Aluno)
        .join(Usuario)
        .where(
            Aluno.id_curso == turma.id_curso,
            Usuario.ativo_usuario.is_(True),
            or_(
                Usuario.nome_usuario.ilike(term, escape="\\"),
                Aluno.matricula_aluno.ilike(term, escape="\\"),
                Usuario.email_usuario.ilike(term, escape="\\"),
            ),
        )
    )
    return page_response(
        students.order_by(Usuario.nome_usuario, Aluno.id_aluno),
        lambda a: {
            "id_aluno": a.id_aluno,
            "nome": a.usuario.nome_usuario,
            "matricula": a.matricula_aluno,
        },
    )


@bp.get("/turmas/<int:class_id>/matriculas")
@bp.post("/turmas/<int:class_id>/matriculas")
@authenticated()
def manage(class_id):
    turma = classes.get_class(class_id, lock=request.method == "POST")
    if request.method == "POST":
        data = v.body({"id_aluno"}, {"id_aluno"})
        item = enrollments.enroll(turma, v.integer(data["id_aluno"], "id_aluno"))
        return resource_response(
            item,
            enrollments.serialize(item),
            201,
            "UC_04_M01",
            "Estudante matriculado com sucesso!",
        )
    return page_response(
        select(Matricula)
        .where(Matricula.id_turma == class_id, Matricula.situacao_matricula_turma == "ativa")
        .order_by(Matricula.id_matricula_turma),
        enrollments.serialize,
    )


@bp.delete("/turmas/<int:class_id>/matriculas/<int:enrollment_id>")
@authenticated()
def remove(class_id, enrollment_id):
    classes.get_class(class_id, lock=True)
    item = db.session.scalar(
        select(Matricula)
        .where(Matricula.id_matricula_turma == enrollment_id, Matricula.id_turma == class_id)
        .with_for_update()
    )
    if not item:
        raise APIError(404, "MATRICULA_AUSENTE", "Matrícula não encontrada.")
    check_version(item)
    data = v.body({"confirmacao", "motivo"}, {"confirmacao", "motivo"})
    result = enrollments.remove(item, data["confirmacao"], v.text(data["motivo"], "motivo", 2000))
    return resource_response(
        item, result, code="UC_04_M04", message="O estudante foi removido da turma com sucesso!"
    )


@bp.get("/matriculas/<int:enrollment_id>")
@authenticated()
def detail(enrollment_id):
    item = db.session.get(Matricula, enrollment_id)
    if not item:
        raise APIError(404, "MATRICULA_AUSENTE", "Matrícula não encontrada.")
    if item.id_aluno != g.user.id_usuario:
        classes.get_class(item.id_turma)
    return resource_response(item, enrollments.serialize(item))


@bp.get("/minhas-matriculas")
@authenticated()
def mine():
    return page_response(
        select(Matricula)
        .where(
            Matricula.id_aluno == g.user.id_usuario, Matricula.situacao_matricula_turma == "ativa"
        )
        .order_by(Matricula.id_matricula_turma),
        enrollments.serialize,
    )


@bp.post("/matriculas/autoinscricao")
@authenticated()
@limiter.limit("10 per minute; 30 per hour")
def signup():
    data = v.body({"codigo_acesso"}, {"codigo_acesso"})
    item = enrollments.self_enroll(data["codigo_acesso"])
    return resource_response(
        item, enrollments.serialize(item), 201, "UC_04_M01", "Estudante matriculado com sucesso!"
    )
