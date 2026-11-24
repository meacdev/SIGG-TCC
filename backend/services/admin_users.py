"""UC14 Manter Usuários: management of accounts and permissions by the Administrator."""

from collections import defaultdict
from datetime import UTC, datetime

from flask import current_app, g
from sqlalchemy import exists, or_, select
from sqlalchemy.orm import selectinload

from backend import validation as v
from backend.audit import audit
from backend.db import db, utcnow
from backend.defense_models import Banca, Matricula, Membro, Orientacao
from backend.errors import APIError
from backend.models import (
    Curso,
    Estudante,
    Perfil,
    Professor,
    ProfessorCurso,
    TokenUsuario,
    Turma,
    Usuario,
    UsuarioPerfil,
)
from backend.security import revoke_sessions, roles
from backend.serialization import check_version, iso
from backend.services import invites
from backend.services.classes import clear_course_role, course_role_column, has_course_role
from backend.services.mail import require_mail
from backend.services.users import TITLES, title

MESSAGES = {
    1: "Usuário pré-cadastrado com sucesso! O convite foi enviado por e-mail.",
    2: "Preencha todos os campos obrigatórios.",
    3: "Verifique o formato dos campos destacados.",
    4: "Este endereço de e-mail já está cadastrado.",
    5: "Já existe um usuário com este CPF ou matrícula.",
    6: "Seu perfil não permite esta operação.",
    7: "Este perfil exige um docente interno ativo e um curso ativo.",
    8: "Informe o departamento/unidade do coordenador.",
    9: "Informe a justificativa da operação.",
    10: "A data de expiração deve ser posterior à data atual.",
    11: "Você não pode inativar a própria conta nem remover o próprio perfil de administrador.",
    12: (
        "Não é possível inativar: o usuário possui vínculos acadêmicos ativos. "
        "Transfira-os antes de continuar."
    ),
    14: "Este registro foi alterado por outro usuário. Atualize a página e tente novamente.",
    15: "Dados do usuário atualizados com sucesso!",
    16: "Perfil de acesso atualizado com sucesso!",
    17: "Situação da conta atualizada com sucesso!",
    18: "Convite reenviado com sucesso!",
}
INVITE_NOT_SENT = "Usuário pré-cadastrado, mas o convite não foi enviado. Reenvie o convite."
CREATE_FIELDS = {
    "nome_usuario",
    "email_usuario",
    "cpf_usuario",
    "telefone_usuario",
    "tipo_cadastro",
    "matricula_estudante",
    "id_curso",
    "tipo_professor",
    "titulacao_professor",
    "instituicao_origem_professor",
}
UPDATE_FIELDS = CREATE_FIELDS - {"tipo_cadastro"}
STUDENT_FIELDS = {"matricula_estudante", "id_curso"}
TEACHER_FIELDS = {"tipo_professor", "titulacao_professor", "instituicao_origem_professor"}
INSTITUTIONAL_DOMAIN = "uea.edu.br"
STATUS_FIELDS = {"ativo_usuario", "justificativa"}
GRANT_FIELDS = {
    "codigo_perfil",
    "id_curso",
    "departamento_unidade",
    "data_expiracao",
    "justificativa",
}
REVOKE_FIELDS = {"codigo_perfil", "id_curso", "justificativa"}
COURSE_PROFILES = ("professor_disciplina", "coordenador")
MANAGED_PROFILES = ("administrador", *COURSE_PROFILES)


def fail(status, number, fields=None):
    raise APIError(status, f"UC_14_M{number:02d}", MESSAGES[number], fields)


def require_admin():
    if "administrador" not in roles(g.user.id_usuario):
        fail(403, 6)


def require_fields(data, names):
    missing = {k: "Obrigatório." for k in names if data.get(k) in (None, "")}
    if missing:
        fail(422, 2, missing)


def formatted(field, parser, *args):
    """Report the existing validators with the UC14 format message and the field to highlight."""
    try:
        return parser(*args)
    except APIError as error:
        if error.status != 422:
            raise
        fail(422, 3, {field: error.message})


def require_institutional(address):
    """UC14 attribute 3: only external teachers may use a non-institutional address."""
    if not address.endswith(f"@{INSTITUTIONAL_DOMAIN}"):
        fail(422, 3, {"email_usuario": f"Use um e-mail @{INSTITUTIONAL_DOMAIN}."})


def reject_fields(data, names):
    present = {k: "Não se aplica ao tipo de cadastro." for k in names if k in data}
    if present:
        fail(422, 3, present)


def justification(data):
    value = data.get("justificativa")
    if not isinstance(value, str) or not value.strip():
        fail(422, 9, {"justificativa": "Obrigatório."})
    return formatted("justificativa", v.text, value, "justificativa", 1000)


def today():
    return utcnow().astimezone(current_app.config["ACADEMIC_TIMEZONE"]).date()


def account_status(user):
    if not user.ativo_usuario:
        return "inativo"
    return "ativo" if user.hash_senha_usuario else "pendente"


def registration_type(user):
    if user.estudante:
        return "estudante"
    return "docente" if user.professor else "administrativo"


def describe(users):
    """Serialize a page with batched lookups; never exposes grades, documents or secrets."""
    ids = [user.id_usuario for user in users]
    now = utcnow()
    grants, links, invitations = defaultdict(list), defaultdict(list), {}
    rows = db.session.execute(
        select(UsuarioPerfil, Perfil.codigo_perfil)
        .join(Perfil)
        .where(UsuarioPerfil.id_usuario.in_(ids))
        .order_by(Perfil.codigo_perfil)
    )
    for association, code in rows:
        expiration = association.data_expiracao_usuario_perfil
        if association.data_concessao_usuario_perfil <= now and (
            expiration is None or expiration > now
        ):
            grants[association.id_usuario].append(
                {
                    "codigo_perfil": code,
                    "data_concessao": iso(association.data_concessao_usuario_perfil),
                    "data_expiracao": iso(expiration),
                }
            )
    rows = db.session.execute(
        select(ProfessorCurso, Curso.nome_curso)
        .join(Curso, ProfessorCurso.id_curso == Curso.id_curso)
        .where(
            ProfessorCurso.id_professor.in_(ids),
            or_(
                ProfessorCurso.data_fim_professor_curso.is_(None),
                ProfessorCurso.data_fim_professor_curso >= today(),
            ),
        )
        .order_by(Curso.nome_curso)
    )
    for link, course_name in rows:
        links[link.id_professor].append(
            {
                "id_curso": link.id_curso,
                "nome_curso": course_name,
                "professor_disciplina": link.professor_disciplina_professor_curso,
                "coordenador": link.coordenador_professor_curso,
                "departamento_unidade": link.departamento_unidade_professor_curso,
                "data_inicio": link.data_inicio_professor_curso.isoformat(),
                "data_fim": (
                    link.data_fim_professor_curso.isoformat()
                    if link.data_fim_professor_curso
                    else None
                ),
            }
        )
    rows = db.session.execute(
        select(TokenUsuario.id_usuario, TokenUsuario.data_expiracao_token_usuario).where(
            TokenUsuario.id_usuario.in_(ids),
            TokenUsuario.finalidade_token_usuario == invites.INVITE,
            TokenUsuario.data_consumo_token_usuario.is_(None),
        )
    )
    invitations = dict(rows.all())
    result = []
    for user in users:
        item = {
            "id_usuario": user.id_usuario,
            "nome_usuario": user.nome_usuario,
            "email_usuario": user.email_usuario,
            "cpf_usuario": user.cpf_usuario,
            "telefone_usuario": user.telefone_usuario,
            "ativo_usuario": user.ativo_usuario,
            "situacao_conta": account_status(user),
            "tipo_cadastro": registration_type(user),
            "data_criacao_usuario": iso(user.data_criacao_usuario),
            "data_atualizacao_usuario": iso(user.data_atualizacao_usuario),
            "perfis": [grant["codigo_perfil"] for grant in grants[user.id_usuario]],
            "concessoes": grants[user.id_usuario],
            "vinculos_curso": links[user.id_usuario],
            "data_expiracao_convite": (
                iso(invitations.get(user.id_usuario)) if not user.hash_senha_usuario else None
            ),
        }
        if user.estudante:
            item["estudante"] = {
                "matricula_estudante": user.estudante.matricula_estudante,
                "id_curso": user.estudante.id_curso,
            }
        if user.professor:
            item["professor"] = {
                "tipo_professor": user.professor.tipo_professor,
                "titulacao_professor": user.professor.titulacao_professor,
                "instituicao_origem_professor": user.professor.instituicao_origem_professor,
                "ativo_professor": user.professor.ativo_professor,
            }
        result.append(item)
    return result


def describe_one(user):
    return describe([user])[0]


def list_query(args):
    query = select(Usuario).options(
        selectinload(Usuario.estudante), selectinload(Usuario.professor)
    )
    term = (args.get("busca") or "").strip()
    if term:
        if len(term) > 100:
            fail(422, 3, {"busca": "Use até 100 caracteres."})
        query = query.where(
            or_(
                Usuario.nome_usuario.icontains(term, autoescape=True),
                Usuario.email_usuario.icontains(term, autoescape=True),
                exists().where(
                    Estudante.id_estudante == Usuario.id_usuario,
                    Estudante.matricula_estudante.icontains(term, autoescape=True),
                ),
            )
        )
    status = args.get("situacao")
    if status:
        formatted("situacao", v.choice, status, "situacao", ("ativo", "pendente", "inativo"))
        if status == "inativo":
            query = query.where(Usuario.ativo_usuario.is_(False))
        else:
            password = Usuario.hash_senha_usuario
            query = query.where(
                Usuario.ativo_usuario.is_(True),
                password.is_not(None) if status == "ativo" else password.is_(None),
            )
    kind = args.get("tipo_cadastro")
    student = exists().where(Estudante.id_estudante == Usuario.id_usuario)
    teacher = exists().where(Professor.id_professor == Usuario.id_usuario)
    if kind:
        formatted(
            "tipo_cadastro",
            v.choice,
            kind,
            "tipo_cadastro",
            ("estudante", "docente", "administrativo"),
        )
        query = query.where(
            {"estudante": student, "docente": ~student & teacher}.get(kind, ~student & ~teacher)
        )
    profile = args.get("perfil")
    if profile:
        now = utcnow()
        query = query.where(
            exists()
            .where(
                UsuarioPerfil.id_usuario == Usuario.id_usuario,
                UsuarioPerfil.id_perfil == Perfil.id_perfil,
                Perfil.codigo_perfil == profile,
                UsuarioPerfil.data_concessao_usuario_perfil <= now,
                or_(
                    UsuarioPerfil.data_expiracao_usuario_perfil.is_(None),
                    UsuarioPerfil.data_expiracao_usuario_perfil > now,
                ),
            )
            .correlate(Usuario)
        )
    course = args.get("id_curso")
    if course:
        if not course.isascii() or not course.isdigit() or len(course) > 18:
            fail(422, 3, {"id_curso": "Informe um curso válido."})
        course = int(course)
        query = query.where(
            or_(
                exists().where(
                    Estudante.id_estudante == Usuario.id_usuario, Estudante.id_curso == course
                ),
                exists().where(
                    ProfessorCurso.id_professor == Usuario.id_usuario,
                    ProfessorCurso.id_curso == course,
                    or_(
                        ProfessorCurso.data_fim_professor_curso.is_(None),
                        ProfessorCurso.data_fim_professor_curso >= today(),
                    ),
                ),
            )
        )
    return query.order_by(Usuario.nome_usuario, Usuario.id_usuario)


def get_user(user_id):
    user = db.session.get(Usuario, user_id)
    if not user:
        raise APIError(404, "USUARIO_NAO_ENCONTRADO", "Usuário não encontrado.")
    return user


def lock_target(user_id):
    """Lock actor and target in id order, so two admins cannot remove each other at once."""
    rows = db.session.scalars(
        select(Usuario)
        .where(Usuario.id_usuario.in_({user_id, g.user.id_usuario}))
        .order_by(Usuario.id_usuario)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()
    by_id = {user.id_usuario: user for user in rows}
    actor = by_id.get(g.user.id_usuario)
    if not actor or not actor.ativo_usuario:
        fail(403, 6)
    require_admin()
    if user_id not in by_id:
        raise APIError(404, "USUARIO_NAO_ENCONTRADO", "Usuário não encontrado.")
    user = by_id[user_id]
    try:
        check_version(user)
    except APIError as error:
        if error.status != 412:
            raise
        fail(409, 14)
    return user


def active_course(value, field="id_curso"):
    course_id = formatted(field, v.integer, value, field)
    course = db.session.get(Curso, course_id)
    return course if course and course.ativo_curso else None


def unique_identity(address=None, document=None, enrollment=None, user_id=0):
    if address and db.session.scalar(
        select(Usuario.id_usuario).where(
            Usuario.email_usuario == address, Usuario.id_usuario != user_id
        )
    ):
        fail(409, 4, {"email_usuario": "Já cadastrado."})
    if document and db.session.scalar(
        select(Usuario.id_usuario).where(
            Usuario.cpf_usuario == document, Usuario.id_usuario != user_id
        )
    ):
        fail(409, 5, {"cpf_usuario": "Já cadastrado."})
    if enrollment and db.session.scalar(
        select(Estudante.id_estudante).where(
            Estudante.matricula_estudante == enrollment, Estudante.id_estudante != user_id
        )
    ):
        fail(409, 5, {"matricula_estudante": "Já cadastrada."})


def optional_text(data, field, maximum=200):
    if data.get(field) in (None, ""):
        return None
    return formatted(field, v.text, data[field], field, maximum)


def teacher_kind(value):
    return formatted("tipo_professor", v.choice, value, "tipo_professor", ("interno", "externo"))


def teacher_title(value):
    if not isinstance(value, str):
        fail(422, 3, {"titulacao_professor": ", ".join(TITLES)})
    return formatted("titulacao_professor", title, value)


def pre_register(data):
    require_fields(data, ("nome_usuario", "email_usuario", "tipo_cadastro"))
    kind = formatted(
        "tipo_cadastro",
        v.choice,
        data["tipo_cadastro"],
        "tipo_cadastro",
        ("estudante", "docente", "administrativo"),
    )
    if kind == "estudante":
        require_fields(data, STUDENT_FIELDS)
        reject_fields(data, TEACHER_FIELDS)
    elif kind == "docente":
        require_fields(data, ("tipo_professor", "titulacao_professor"))
        reject_fields(data, STUDENT_FIELDS)
        if data["tipo_professor"] == "externo":
            require_fields(data, ("instituicao_origem_professor",))
    else:
        reject_fields(data, STUDENT_FIELDS | TEACHER_FIELDS)
    name = formatted("nome_usuario", v.name, data["nome_usuario"])
    address = formatted("email_usuario", v.email, data["email_usuario"])
    if not (kind == "docente" and data["tipo_professor"] == "externo"):
        require_institutional(address)
    document = formatted("cpf_usuario", v.cpf, data.get("cpf_usuario"))
    phone = formatted("telefone_usuario", v.phone, data.get("telefone_usuario"))
    enrollment = None
    if kind == "estudante":
        enrollment = formatted(
            "matricula_estudante",
            v.text,
            data["matricula_estudante"],
            "matricula_estudante",
            30,
        )
        if not active_course(data["id_curso"]):
            fail(422, 3, {"id_curso": "Selecione um curso ativo."})
    teacher = None
    if kind == "docente":
        teacher = {
            "tipo_professor": teacher_kind(data["tipo_professor"]),
            "titulacao_professor": teacher_title(data["titulacao_professor"]),
            "instituicao_origem_professor": optional_text(data, "instituicao_origem_professor"),
        }
    unique_identity(address, document, enrollment)
    user = Usuario(
        nome_usuario=name,
        email_usuario=address,
        hash_senha_usuario=None,
        cpf_usuario=document,
        telefone_usuario=phone,
    )
    db.session.add(user)
    db.session.flush()
    if kind == "estudante":
        profile = db.session.scalar(select(Perfil).where(Perfil.codigo_perfil == "estudante"))
        if not profile:
            raise APIError(503, "CONFIGURACAO_PENDENTE", "Inicialize os perfis do sistema.")
        db.session.add(
            Estudante(
                id_estudante=user.id_usuario,
                matricula_estudante=enrollment,
                id_curso=data["id_curso"],
            )
        )
        db.session.add(UsuarioPerfil(id_usuario=user.id_usuario, id_perfil=profile.id_perfil))
    elif teacher:
        db.session.add(Professor(id_professor=user.id_usuario, **teacher))
    raw = invites.issue_invite(user)
    audit(
        g.user.id_usuario,
        "pre_cadastro_usuario",
        "usuario",
        user.id_usuario,
        {
            "nome_usuario": (None, name),
            "email_usuario": (None, address),
            "cpf_usuario": (None, document),
            "telefone_usuario": (None, phone),
            "tipo_cadastro": (None, kind),
        },
    )
    db.session.commit()
    db.session.refresh(user)
    return user, invites.try_send(invites.send_invite, address, raw)


def resend_invite(user_id):
    require_mail()
    user = lock_target(user_id)
    if account_status(user) != "pendente":
        raise APIError(409, "CONVITE_INDISPONIVEL", "Esta conta não possui convite pendente.")
    raw = invites.issue_invite(user)
    user.data_atualizacao_usuario = utcnow()
    audit(g.user.id_usuario, "reenvio_convite", "usuario", user.id_usuario)
    db.session.commit()
    invites.send_invite(user.email_usuario, raw)
    return user


def update_user(user_id, data):
    user = lock_target(user_id)
    changes = {}
    pending_email = None
    if "nome_usuario" in data:
        require_fields(data, ("nome_usuario",))
        changes["nome_usuario"] = formatted("nome_usuario", v.name, data["nome_usuario"])
    if "cpf_usuario" in data:
        changes["cpf_usuario"] = formatted("cpf_usuario", v.cpf, data["cpf_usuario"])
    if "telefone_usuario" in data:
        changes["telefone_usuario"] = formatted(
            "telefone_usuario", v.phone, data["telefone_usuario"]
        )
    if "email_usuario" in data:
        require_fields(data, ("email_usuario",))
        address = formatted("email_usuario", v.email, data["email_usuario"])
        if address != user.email_usuario:
            pending_email = address
    student_changes = update_student_values(user, data)
    teacher_changes = update_teacher_values(user, data)
    previous_kind = user.professor.tipo_professor if user.professor else None
    final_kind = teacher_changes.get("tipo_professor", previous_kind)
    # Legacy addresses stay valid until the e-mail or the teacher type actually changes.
    became_internal = previous_kind == "externo" and final_kind == "interno"
    checked_address = pending_email or (user.email_usuario if became_internal else None)
    if checked_address and final_kind != "externo":
        require_institutional(checked_address)
    unique_identity(
        pending_email,
        changes.get("cpf_usuario"),
        student_changes.get("matricula_estudante"),
        user.id_usuario,
    )
    if pending_email:
        require_mail()
    log = {}
    for target, values in ((user, changes), (user.estudante, student_changes)):
        for field, value in values.items():
            log[field] = (getattr(target, field), value)
            setattr(target, field, value)
    for field, value in teacher_changes.items():
        log[field] = (getattr(user.professor, field), value)
        setattr(user.professor, field, value)
    raw = invites.issue_email_change(user, pending_email) if pending_email else None
    if pending_email:
        log["novo_email_solicitado"] = (None, pending_email)
    user.data_atualizacao_usuario = utcnow()
    audit(g.user.id_usuario, "atualizacao_usuario_admin", "usuario", user.id_usuario, log)
    db.session.commit()
    sent = invites.try_send(invites.send_change, pending_email, raw) if raw else None
    return user, {"novo_email": pending_email, "enviado": sent} if pending_email else None


def update_student_values(user, data):
    present = STUDENT_FIELDS & set(data)
    if not present:
        return {}
    if not user.estudante:
        reject_fields(data, STUDENT_FIELDS)
    values = {}
    if "matricula_estudante" in data:
        require_fields(data, ("matricula_estudante",))
        values["matricula_estudante"] = formatted(
            "matricula_estudante",
            v.text,
            data["matricula_estudante"],
            "matricula_estudante",
            30,
        )
    if "id_curso" in data:
        require_fields(data, ("id_curso",))
        course = active_course(data["id_curso"])
        if not course:
            fail(422, 3, {"id_curso": "Selecione um curso ativo."})
        if course.id_curso != user.estudante.id_curso and db.session.scalar(
            select(Matricula.id_matricula_turma).where(
                Matricula.id_estudante == user.id_usuario,
                Matricula.situacao_matricula_turma == "ativa",
            )
        ):
            raise APIError(
                409,
                "ESTUDANTE_COM_MATRICULA",
                "Não altere o curso de um estudante com matrícula ativa.",
                {"id_curso": "Matrícula ativa."},
            )
        values["id_curso"] = course.id_curso
    return values


def update_teacher_values(user, data):
    present = TEACHER_FIELDS & set(data)
    if not present:
        return {}
    if not user.professor:
        reject_fields(data, TEACHER_FIELDS)
    teacher = user.professor
    values = {}
    if "tipo_professor" in data:
        values["tipo_professor"] = teacher_kind(data["tipo_professor"])
    if "titulacao_professor" in data:
        values["titulacao_professor"] = teacher_title(data["titulacao_professor"])
    if "instituicao_origem_professor" in data:
        values["instituicao_origem_professor"] = optional_text(data, "instituicao_origem_professor")
    kind = values.get("tipo_professor", teacher.tipo_professor)
    institution = values.get("instituicao_origem_professor", teacher.instituicao_origem_professor)
    if kind == "externo" and not institution:
        fail(422, 2, {"instituicao_origem_professor": "Obrigatório para professor externo."})
    if kind == "externo" and any(has_course_role(user.id_usuario, p) for p in COURSE_PROFILES):
        fail(409, 7, {"tipo_professor": "Revogue antes os perfis por curso."})
    return values


def academic_blockers(user_id):
    """RN 10: only identifiers needed to transfer the links, without academic content."""
    blockers = [
        {"tipo": "turma", "id": item.id_turma, "descricao": item.codigo_turma}
        for item in db.session.execute(
            select(Turma.id_turma, Turma.codigo_turma).where(
                Turma.id_professor_responsavel == user_id, Turma.ativa_turma.is_(True)
            )
        )
    ]
    blockers += [
        {"tipo": "orientacao", "id": item.id_orientacao, "descricao": item.papel_orientacao}
        for item in db.session.execute(
            select(Orientacao.id_orientacao, Orientacao.papel_orientacao).where(
                Orientacao.id_professor == user_id,
                Orientacao.data_encerramento_orientacao.is_(None),
                Orientacao.situacao_aceite_orientacao != "recusado",
            )
        )
    ]
    blockers += [
        {"tipo": "banca", "id": item.id_banca, "descricao": iso(item.data_inicio_banca)}
        for item in db.session.execute(
            select(Banca.id_banca, Banca.data_inicio_banca)
            .join(Membro, Membro.id_banca == Banca.id_banca)
            .where(Membro.id_docente == user_id, Banca.situacao_banca == "agendada")
        )
    ]
    return blockers


def change_status(user_id, data):
    if type(data.get("ativo_usuario")) is not bool:
        require_fields(data, ("ativo_usuario",))
        fail(422, 3, {"ativo_usuario": "Informe true ou false."})
    reason = justification(data)
    active = data["ativo_usuario"]
    user = lock_target(user_id)
    if not active and user.id_usuario == g.user.id_usuario:
        fail(409, 11)
    if not active:
        blockers = academic_blockers(user.id_usuario)
        if blockers:
            fail(409, 12, {"vinculos": blockers})
    if user.ativo_usuario != active:
        log = {"ativo_usuario": (user.ativo_usuario, active)}
        user.ativo_usuario = active
        if user.professor:
            log["ativo_professor"] = (user.professor.ativo_professor, active)
            user.professor.ativo_professor = active
        if not active:
            revoke_sessions(user.id_usuario)
        user.data_atualizacao_usuario = utcnow()
        audit(
            g.user.id_usuario,
            "ativacao_usuario" if active else "inativacao_usuario",
            "usuario",
            user.id_usuario,
            log,
            reason=reason,
        )
    db.session.commit()
    return user


def parse_expiration(value):
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError
    except TypeError, ValueError:
        fail(422, 3, {"data_expiracao": "Use ISO 8601 com fuso horário."})
    parsed = parsed.astimezone(UTC)
    if parsed <= utcnow():
        fail(422, 10, {"data_expiracao": "Informe uma data futura."})
    return parsed


def managed_profile(value):
    profile = formatted(
        "codigo_perfil", v.choice, value, "codigo_perfil", MANAGED_PROFILES
    )  # RN 06: derived roles are not accepted here.
    item = db.session.scalar(select(Perfil).where(Perfil.codigo_perfil == profile))
    if not item:
        raise APIError(503, "CONFIGURACAO_PENDENTE", "Inicialize os perfis do sistema.")
    return item


def is_effective(association):
    if not association:
        return False
    now = utcnow()
    expiration = association.data_expiracao_usuario_perfil
    return association.data_concessao_usuario_perfil <= now and (
        expiration is None or expiration > now
    )


def current_course_link(user_id, course_id):
    return db.session.scalar(
        select(ProfessorCurso)
        .where(
            ProfessorCurso.id_professor == user_id,
            ProfessorCurso.id_curso == course_id,
            or_(
                ProfessorCurso.data_fim_professor_curso.is_(None),
                ProfessorCurso.data_fim_professor_curso >= today(),
            ),
        )
        .order_by(ProfessorCurso.data_inicio_professor_curso.desc())
        .with_for_update()
    )


def grant_profile(user_id, data):
    require_fields(data, ("codigo_perfil",))
    profile = managed_profile(data["codigo_perfil"])
    code = profile.codigo_perfil
    if code in COURSE_PROFILES:
        require_fields(data, ("id_curso",))
    elif {"id_curso", "departamento_unidade"} & set(data):
        reject_fields(data, {"id_curso", "departamento_unidade"})
    reason = justification(data)
    expiration = parse_expiration(data.get("data_expiracao"))
    if code == "administrador" and expiration:
        fail(422, 3, {"data_expiracao": "O perfil de administrador não possui expiração."})
    user = lock_target(user_id)
    if not user.ativo_usuario:
        if code == "administrador":
            raise APIError(409, "CONTA_INATIVA", "O perfil exige uma conta ativa.")
        fail(422, 7)
    log = {}
    department = None
    if code in COURSE_PROFILES:
        course = active_course(data["id_curso"])
        teacher = user.professor
        if (
            not course
            or not teacher
            or not teacher.ativo_professor
            or teacher.tipo_professor != "interno"
        ):
            fail(422, 7)
        link = current_course_link(user.id_usuario, course.id_curso)
        department = optional_text(data, "departamento_unidade") or (
            link.departamento_unidade_professor_curso if link else None
        )
        if code == "coordenador" and not department:
            fail(422, 8, {"departamento_unidade": "Obrigatório para coordenador."})
    association = db.session.get(
        UsuarioPerfil, (user.id_usuario, profile.id_perfil), with_for_update=True
    )
    effective = is_effective(association)
    if code in COURSE_PROFILES:
        if not effective:
            clear_course_role(user.id_usuario, code)
            if link:
                db.session.refresh(link)
        if not link:
            link = ProfessorCurso(
                id_professor=user.id_usuario,
                id_curso=course.id_curso,
                data_inicio_professor_curso=today(),
            )
            db.session.add(link)
        column = course_role_column(code).key
        log[f"curso_{course.id_curso}_{code}"] = (getattr(link, column, False), True)
        setattr(link, column, True)
        if department:
            log["departamento_unidade"] = (link.departamento_unidade_professor_curso, department)
            link.departamento_unidade_professor_curso = department
    previous_expiration = association.data_expiracao_usuario_perfil if association else None
    if not association:
        association = UsuarioPerfil(id_usuario=user.id_usuario, id_perfil=profile.id_perfil)
        db.session.add(association)
    if not effective:
        association.data_concessao_usuario_perfil = utcnow()
    association.data_expiracao_usuario_perfil = expiration
    log[f"perfil_{code}"] = (effective, True)
    log[f"expiracao_{code}"] = (iso(previous_expiration) if effective else None, iso(expiration))
    user.data_atualizacao_usuario = utcnow()
    audit(g.user.id_usuario, "concessao_perfil", "usuario", user.id_usuario, log, reason=reason)
    db.session.commit()
    return user


def revoke_profile(user_id, data):
    require_fields(data, ("codigo_perfil",))
    profile = managed_profile(data["codigo_perfil"])
    code = profile.codigo_perfil
    if code in COURSE_PROFILES:
        require_fields(data, ("id_curso",))
        course_id = formatted("id_curso", v.integer, data["id_curso"], "id_curso")
    else:
        reject_fields(data, {"id_curso"})
        course_id = None
    reason = justification(data)
    user = lock_target(user_id)
    if code == "administrador" and user.id_usuario == g.user.id_usuario:
        fail(409, 11)
    association = db.session.get(
        UsuarioPerfil, (user.id_usuario, profile.id_perfil), with_for_update=True
    )
    if not is_effective(association):
        raise APIError(404, "PERFIL_NAO_CONCEDIDO", "Este perfil não está concedido ao usuário.")
    log = {}
    remains = False
    if code in COURSE_PROFILES:
        link = current_course_link(user.id_usuario, course_id)
        column = course_role_column(code).key
        if not link or not getattr(link, column):
            raise APIError(
                404, "VINCULO_NAO_ENCONTRADO", "O usuário não possui este perfil no curso."
            )
        setattr(link, column, False)
        db.session.flush()
        log[f"curso_{course_id}_{code}"] = (True, False)
        remains = has_course_role(user.id_usuario, code)
    if not remains:
        association.data_expiracao_usuario_perfil = utcnow()
    log[f"perfil_{code}"] = (True, remains)
    user.data_atualizacao_usuario = utcnow()
    audit(g.user.id_usuario, "revogacao_perfil", "usuario", user.id_usuario, log, reason=reason)
    db.session.commit()
    return user
