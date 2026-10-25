from flask import Blueprint, g, jsonify, request
from sqlalchemy import select

from backend import validation as v
from backend.db import db
from backend.errors import APIError
from backend.models import Curso, Docente, DocenteCurso, PeriodoLetivo, Usuario
from backend.security import authenticated
from backend.services.classes import course_scope, current_link, manager

bp = Blueprint("catalogs", __name__, url_prefix="/api/v1")


def page_response(query, serializer):
    page, size = v.pagination()
    result = db.paginate(query, page=page, per_page=size, max_per_page=100, error_out=False)
    return jsonify(
        data=[serializer(item) for item in result.items],
        meta={"page": page, "per_page": size, "total": result.total, "pages": result.pages},
    )


@bp.get("/cursos")
def courses():
    query = select(Curso).where(Curso.ativo_curso.is_(True)).order_by(Curso.nome_curso)
    return page_response(
        query,
        lambda c: {
            "id_curso": c.id_curso,
            "codigo_curso": c.codigo_curso,
            "nome_curso": c.nome_curso,
        },
    )


@bp.get("/periodos-letivos")
@authenticated()
def periods():
    return page_response(
        select(PeriodoLetivo).order_by(
            PeriodoLetivo.ano_periodo_letivo.desc(), PeriodoLetivo.semestre_periodo_letivo.desc()
        ),
        lambda p: {
            "id_periodo_letivo": p.id_periodo_letivo,
            "periodo_letivo": f"{p.ano_periodo_letivo}/{p.semestre_periodo_letivo}",
        },
    )


@bp.get("/docentes")
@authenticated()
def teachers():
    profiles = manager()
    try:
        course_id = v.integer(int(request.args.get("id_curso", "")), "id_curso")
    except ValueError:
        raise APIError(422, "VALIDACAO", "Informe id_curso para consultar os docentes.") from None
    coordinator_courses = list(db.session.scalars(course_scope(g.user.id_usuario, True)))
    if "coordenador" not in profiles or course_id not in coordinator_courses:
        if course_id not in list(db.session.scalars(course_scope(g.user.id_usuario))):
            raise APIError(403, "ACESSO_NEGADO", "Você não possui vínculo com o curso.")
        only_self = True
    else:
        only_self = False
    query = (
        select(Docente)
        .join(Usuario)
        .join(DocenteCurso)
        .where(
            Docente.ativo_docente.is_(True),
            Docente.tipo_docente == "interno",
            Usuario.ativo_usuario.is_(True),
            DocenteCurso.id_curso == course_id,
            current_link(),
        )
    )
    if only_self:
        query = query.where(Docente.id_docente == g.user.id_usuario)
    # Only teachers with an effective professor role can be responsible for a class.
    from sqlalchemy import exists, or_

    from backend.db import utcnow
    from backend.models import Perfil, UsuarioPerfil

    query = query.where(
        exists(
            select(UsuarioPerfil.id_usuario)
            .join(Perfil)
            .where(
                UsuarioPerfil.id_usuario == Docente.id_docente,
                Perfil.codigo_perfil == "professor_disciplina",
                UsuarioPerfil.data_concessao_usuario_perfil <= utcnow(),
                or_(
                    UsuarioPerfil.data_expiracao_usuario_perfil.is_(None),
                    UsuarioPerfil.data_expiracao_usuario_perfil > utcnow(),
                ),
            )
        )
    )
    query = query.order_by(Docente.id_docente)
    return page_response(
        query,
        lambda d: {
            "id_docente": d.id_docente,
            "nome_usuario": d.usuario.nome_usuario,
            "titulacao_docente": d.titulacao_docente,
        },
    )
