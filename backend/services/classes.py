import hashlib
import secrets
import string
from datetime import timedelta

from flask import current_app, g
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.exc import IntegrityError

from backend import validation as v
from backend.audit import audit
from backend.db import db, utcnow
from backend.errors import APIError
from backend.models import Curso, Docente, DocenteCurso, PeriodoLetivo, Turma, Usuario
from backend.security import roles

CREATE_FIELDS = {
    "periodo_letivo",
    "codigo_turma",
    "nivel_turma",
    "id_curso",
    "id_docente_responsavel",
}
UPDATE_FIELDS = CREATE_FIELDS | {"ativa_turma", "autoinscricao_ativa_turma"}


def current_link():
    today = utcnow().astimezone(current_app.config["ACADEMIC_TIMEZONE"]).date()
    return and_(
        DocenteCurso.data_inicio_docente_curso <= today,
        or_(
            DocenteCurso.data_fim_docente_curso.is_(None),
            DocenteCurso.data_fim_docente_curso >= today,
        ),
    )


def course_scope(user_id, coordinator=False):
    query = select(DocenteCurso.id_curso).where(DocenteCurso.id_docente == user_id, current_link())
    if coordinator:
        query = query.where(DocenteCurso.coordenador_docente_curso.is_(True))
    return query


def manager():
    teacher = db.session.get(Docente, g.user.id_usuario)
    profiles = set(roles(g.user.id_usuario))
    if (
        not teacher
        or not teacher.ativo_docente
        or teacher.tipo_docente != "interno"
        or not profiles & {"professor_disciplina", "coordenador"}
    ):
        raise APIError(403, "ACESSO_NEGADO", "Esta operação exige um docente autorizado.")
    return profiles


def visible_classes():
    profiles = manager()
    conditions = []
    if "professor_disciplina" in profiles:
        conditions.append(
            and_(
                Turma.id_docente_responsavel == g.user.id_usuario,
                Turma.id_curso.in_(course_scope(g.user.id_usuario)),
            )
        )
    if "coordenador" in profiles:
        conditions.append(Turma.id_curso.in_(course_scope(g.user.id_usuario, coordinator=True)))
    return select(Turma).where(or_(*conditions))


def get_class(class_id, lock=False):
    v.integer(class_id, "id_turma")
    query = visible_classes().where(Turma.id_turma == class_id)
    if lock:
        # The period relationship is joined; PostgreSQL must lock only the turma row.
        query = query.with_for_update(of=Turma)
    item = db.session.scalar(query.execution_options(populate_existing=True))
    if not item:
        raise APIError(404, "TURMA_NAO_ENCONTRADA", "Turma não encontrada.")
    return item


def validate_assignment(course_id, teacher_id):
    profiles = manager()
    course = db.session.get(Curso, v.integer(course_id, "id_curso"))
    if not course or not course.ativo_curso:
        raise APIError(422, "CURSO_INVALIDO", "Selecione um curso ativo.")
    coordinator = "coordenador" in profiles and db.session.scalar(
        select(
            exists().where(
                DocenteCurso.id_docente == g.user.id_usuario,
                DocenteCurso.id_curso == course_id,
                DocenteCurso.coordenador_docente_curso.is_(True),
                current_link(),
            )
        )
    )
    if not coordinator:
        linked = db.session.scalar(
            select(
                exists().where(
                    DocenteCurso.id_docente == g.user.id_usuario,
                    DocenteCurso.id_curso == course_id,
                    current_link(),
                )
            )
        )
        if "professor_disciplina" not in profiles or teacher_id != g.user.id_usuario or not linked:
            raise APIError(403, "ACESSO_NEGADO", "Você não pode gerenciar turmas neste curso.")
    teacher_id = v.integer(teacher_id, "id_docente_responsavel")
    teacher = db.session.get(Docente, teacher_id)
    identity = db.session.get(Usuario, teacher_id)
    linked = db.session.scalar(
        select(
            exists().where(
                DocenteCurso.id_docente == teacher_id,
                DocenteCurso.id_curso == course_id,
                current_link(),
            )
        )
    )
    if (
        not teacher
        or not identity
        or not identity.ativo_usuario
        or not teacher.ativo_docente
        or (
            teacher.tipo_docente != "interno"
            or not linked
            or "professor_disciplina" not in roles(teacher_id)
        )
    ):
        raise APIError(422, "DOCENTE_INVALIDO", "Selecione um professor ativo vinculado ao curso.")


def get_period(value):
    year, semester = v.period(value)
    query = select(PeriodoLetivo).where(
        PeriodoLetivo.ano_periodo_letivo == year, PeriodoLetivo.semestre_periodo_letivo == semester
    )
    result = db.session.scalar(query)
    if result:
        return result
    try:
        with db.session.begin_nested():
            result = PeriodoLetivo(ano_periodo_letivo=year, semestre_periodo_letivo=semester)
            db.session.add(result)
            db.session.flush()
    except IntegrityError:
        result = db.session.scalar(query)
    return result


def generate_code(item):
    code = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24))
    # 142 bits of entropy; SHA-256 fits the existing VARCHAR(128).
    item.hash_codigo_acesso_turma = hashlib.sha256(code.encode()).hexdigest()
    item.data_expiracao_acesso_turma = utcnow() + timedelta(
        days=current_app.config["CLASS_CODE_DAYS"]
    )
    item.autoinscricao_ativa_turma = True
    return code


def duplicate_check(period_id, code, exclude=None):
    query = select(Turma.id_turma).where(
        Turma.id_periodo_letivo == period_id, Turma.codigo_turma == code
    )
    if exclude:
        query = query.where(Turma.id_turma != exclude)
    if db.session.scalar(query):
        raise APIError(409, "TURMA_DUPLICADA", "Já existe uma turma com esse código no período.")


def create_class(data):
    validate_assignment(data["id_curso"], data["id_docente_responsavel"])
    period = get_period(data["periodo_letivo"])
    code = v.class_code(data["codigo_turma"])
    level = v.integer(data["nivel_turma"], "nivel_turma", 1, 2)
    duplicate_check(period.id_periodo_letivo, code)
    item = Turma(
        id_periodo_letivo=period.id_periodo_letivo,
        codigo_turma=code,
        nivel_turma=level,
        id_curso=data["id_curso"],
        id_docente_responsavel=data["id_docente_responsavel"],
    )
    access_code = generate_code(item)
    db.session.add(item)
    db.session.flush()
    audit(
        g.user.id_usuario,
        "cadastro_turma",
        "turma",
        item.id_turma,
        {
            k: (None, getattr(item, k))
            for k in (
                "id_curso",
                "id_periodo_letivo",
                "id_docente_responsavel",
                "codigo_turma",
                "nivel_turma",
            )
        },
    )
    db.session.commit()
    return item, access_code


def update_class(item, data):
    course_id = data.get("id_curso", item.id_curso)
    teacher_id = data.get("id_docente_responsavel", item.id_docente_responsavel)
    validate_assignment(course_id, teacher_id)
    values = {"id_curso": course_id, "id_docente_responsavel": teacher_id}
    if "periodo_letivo" in data:
        values["id_periodo_letivo"] = get_period(data["periodo_letivo"]).id_periodo_letivo
    if "codigo_turma" in data:
        values["codigo_turma"] = v.class_code(data["codigo_turma"])
    if "nivel_turma" in data:
        values["nivel_turma"] = v.integer(data["nivel_turma"], "nivel_turma", 1, 2)
    for field in ("ativa_turma", "autoinscricao_ativa_turma"):
        if field in data:
            if type(data[field]) is not bool:
                raise APIError(422, "VALIDACAO", "Informe true ou false.", {field: "Booleano."})
            values[field] = data[field]
    active = values.get("ativa_turma", item.ativa_turma)
    signup = values.get("autoinscricao_ativa_turma", item.autoinscricao_ativa_turma)
    if not active:
        values["autoinscricao_ativa_turma"] = False
        values["hash_codigo_acesso_turma"] = None
        values["data_expiracao_acesso_turma"] = None
    elif signup and (
        not item.hash_codigo_acesso_turma
        or not item.data_expiracao_acesso_turma
        or item.data_expiracao_acesso_turma <= utcnow()
    ):
        raise APIError(422, "CODIGO_EXPIRADO", "Gere um novo código de acesso.")
    duplicate_check(
        values.get("id_periodo_letivo", item.id_periodo_letivo),
        values.get("codigo_turma", item.codigo_turma),
        item.id_turma,
    )
    # Changing academic identity after enrollment would invalidate later UC workflows.
    structural = {"id_curso", "id_periodo_letivo", "nivel_turma"}
    if any(k in values and values[k] != getattr(item, k) for k in structural):
        from sqlalchemy import text

        enrolled = db.session.scalar(
            text("SELECT count(*) FROM matricula_turma WHERE id_turma = :id"), {"id": item.id_turma}
        )
        if enrolled:
            raise APIError(
                409,
                "TURMA_COM_MATRICULAS",
                "Não altere curso, período ou nível de uma turma com matrículas.",
            )
    changes = {
        k: (getattr(item, k), value)
        for k, value in values.items()
        if k != "hash_codigo_acesso_turma"
    }
    for field, value in values.items():
        setattr(item, field, value)
    item.data_atualizacao_turma = utcnow()
    audit(g.user.id_usuario, "atualizacao_turma", "turma", item.id_turma, changes)
    db.session.commit()
    db.session.refresh(item)


def deactivate_class(item):
    changes = {
        "ativa_turma": (item.ativa_turma, False),
        "autoinscricao_ativa_turma": (item.autoinscricao_ativa_turma, False),
    }
    item.ativa_turma = False
    item.autoinscricao_ativa_turma = False
    item.hash_codigo_acesso_turma = None
    item.data_expiracao_acesso_turma = None
    item.data_atualizacao_turma = utcnow()
    audit(g.user.id_usuario, "inativacao_turma", "turma", item.id_turma, changes)
    db.session.commit()


def rotate_code(item):
    if not item.ativa_turma:
        raise APIError(409, "TURMA_INATIVA", "Reative a turma antes de gerar um código.")
    code = generate_code(item)
    item.data_atualizacao_turma = utcnow()
    audit(g.user.id_usuario, "rotacao_codigo_turma", "turma", item.id_turma)
    db.session.commit()
    return code
