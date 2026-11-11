from sqlalchemy import select

from backend import validation as v
from backend.audit import audit
from backend.db import db, utcnow
from backend.errors import APIError
from backend.models import (
    AreaConhecimento,
    Curso,
    Estudante,
    Perfil,
    Professor,
    Usuario,
    UsuarioPerfil,
)
from backend.security import hash_password, revoke_sessions, verify_password

SIGNUP_FIELDS = {
    "nome_usuario",
    "email_usuario",
    "senha",
    "cpf_usuario",
    "telefone_usuario",
    "tipo_cadastro",
    "titulacao_professor",
    "tipo_professor",
    "instituicao_origem_professor",
    "url_lattes_professor",
    "areas_interesse",
    "matricula_estudante",
    "id_curso",
}
# RF20.1: general data shared by every user (both optional).
CONTACT_FIELDS = {"cpf_usuario", "telefone_usuario"}
PROFILE_FIELDS = {
    "nome_usuario",
    "email_usuario",
    "cpf_usuario",
    "telefone_usuario",
    "titulacao_professor",
    "url_lattes_professor",
    "areas_interesse",
    "instituicao_origem_professor",
    "senha_atual",
}
# RF20.2.1 and ck_professor_titulacao.
TITLES = ("Especialista", "Mestre", "Doutor")


def title(value, field="titulacao_professor"):
    """Accept any letter case and store the dictionary spelling."""
    canonical = {t.lower(): t for t in TITLES}
    key = value.strip().lower() if isinstance(value, str) else None
    return v.choice(canonical.get(key, value), field, TITLES)


def require_institution(teacher):
    """ck_professor_instituicao_externo: external professors need their institution."""
    if teacher.tipo_professor == "externo" and not teacher.instituicao_origem_professor:
        raise APIError(
            422,
            "UC_01_M02",
            "Preencha todos os campos obrigatórios.",
            {"instituicao_origem_professor": "Obrigatório para professor externo."},
        )


def unique_cpf(value, user_id=None):
    if value and db.session.scalar(
        select(Usuario.id_usuario).where(
            Usuario.cpf_usuario == value, Usuario.id_usuario != (user_id or 0)
        )
    ):
        raise APIError(
            409, "CPF_DUPLICADO", "Este CPF já está cadastrado.", {"cpf_usuario": "Já cadastrado."}
        )
    return value


def areas(values):
    if not isinstance(values, list) or len(values) > 20:
        raise APIError(422, "VALIDACAO", "Informe até 20 áreas de interesse.")
    result = []
    for name in dict.fromkeys(v.text(s, "areas_interesse", 150) for s in values):
        existing = db.session.scalar(
            select(AreaConhecimento).where(AreaConhecimento.nome_area_conhecimento == name)
        )
        if existing is None:
            # A savepoint resolves concurrent creation without losing the registration.
            from sqlalchemy.exc import IntegrityError

            try:
                with db.session.begin_nested():
                    existing = AreaConhecimento(nome_area_conhecimento=name)
                    db.session.add(existing)
                    db.session.flush()
            except IntegrityError:
                existing = db.session.scalar(
                    select(AreaConhecimento).where(AreaConhecimento.nome_area_conhecimento == name)
                )
        result.append(existing)
    return result


def signup(data):
    name = v.name(data["nome_usuario"])
    address = v.email(data["email_usuario"], "UC_01_M03")
    secret = v.password(data["senha"])
    kind = v.choice(
        data.get("tipo_cadastro", "professor"), "tipo_cadastro", ("professor", "estudante")
    )
    document = v.cpf(data.get("cpf_usuario"))
    phone = v.phone(data.get("telefone_usuario"))
    if db.session.scalar(select(Usuario.id_usuario).where(Usuario.email_usuario == address)):
        raise APIError(409, "UC_01_M04", "Este endereço de e-mail já está cadastrado.")
    user = Usuario(
        nome_usuario=name,
        email_usuario=address,
        hash_senha_usuario=hash_password(secret),
        cpf_usuario=unique_cpf(document),
        telefone_usuario=phone,
    )
    db.session.add(user)
    db.session.flush()
    if kind == "professor":
        if not data.get("titulacao_professor"):
            raise APIError(
                422,
                "UC_01_M02",
                "Preencha todos os campos obrigatórios.",
                {"titulacao_professor": "Obrigatório para professor."},
            )
        if {"matricula_estudante", "id_curso"}.intersection(data):
            raise APIError(
                422, "VALIDACAO", "Campos de estudante não pertencem ao cadastro de professor."
            )
        teacher = Professor(
            id_professor=user.id_usuario,
            tipo_professor=v.choice(
                data.get("tipo_professor", "interno"), "tipo_professor", ("interno", "externo")
            ),
            titulacao_professor=title(data["titulacao_professor"]),
            url_lattes_professor=v.lattes(data.get("url_lattes_professor")),
            instituicao_origem_professor=(
                v.text(data["instituicao_origem_professor"], "instituicao_origem_professor")
                if data.get("instituicao_origem_professor")
                else None
            ),
        )
        require_institution(teacher)
        db.session.add(teacher)
        teacher.areas = areas(data.get("areas_interesse", []))
    else:
        if any(
            k in data
            for k in {
                "titulacao_professor",
                "tipo_professor",
                "areas_interesse",
                "url_lattes_professor",
                "instituicao_origem_professor",
            }
        ):
            raise APIError(
                422, "VALIDACAO", "Campos de professor não pertencem ao cadastro de estudante."
            )
        course_id = v.integer(data.get("id_curso"), "id_curso")
        course = db.session.get(Curso, course_id)
        if not course or not course.ativo_curso:
            raise APIError(422, "CURSO_INVALIDO", "Selecione um curso ativo.")
        enrollment = v.text(data.get("matricula_estudante"), "matricula_estudante", 30)
        if db.session.scalar(
            select(Estudante.id_estudante).where(Estudante.matricula_estudante == enrollment)
        ):
            raise APIError(409, "MATRICULA_DUPLICADA", "Matrícula já cadastrada.")
        db.session.add(
            Estudante(
                id_estudante=user.id_usuario, matricula_estudante=enrollment, id_curso=course_id
            )
        )
        profile = db.session.scalar(select(Perfil).where(Perfil.codigo_perfil == "estudante"))
        if not profile:
            raise APIError(503, "CONFIGURACAO_PENDENTE", "Inicialize os perfis do sistema.")
        db.session.add(UsuarioPerfil(id_usuario=user.id_usuario, id_perfil=profile.id_perfil))
    audit(user.id_usuario, "cadastro", "usuario", user.id_usuario)
    db.session.commit()
    # Expire relationships possibly read before their dependent rows were flushed.
    db.session.refresh(user)
    return user


def update_profile(user, data):
    changes = {}
    if "email_usuario" in data:
        if not verify_password(user.hash_senha_usuario, data.get("senha_atual", "")):
            raise APIError(401, "CREDENCIAIS_INVALIDAS", "Confirme sua senha atual.")
        address = v.email(data["email_usuario"], "UC_01_M03")
        duplicate = db.session.scalar(
            select(Usuario.id_usuario).where(
                Usuario.email_usuario == address, Usuario.id_usuario != user.id_usuario
            )
        )
        if duplicate:
            raise APIError(409, "UC_01_M04", "Este endereço de e-mail já está cadastrado.")
        changes["email_usuario"] = (user.email_usuario, address)
        user.email_usuario = address
        revoke_sessions(user.id_usuario)
    if "nome_usuario" in data:
        name = v.name(data["nome_usuario"])
        changes["nome_usuario"] = (user.nome_usuario, name)
        user.nome_usuario = name
    if "cpf_usuario" in data:
        document = unique_cpf(v.cpf(data["cpf_usuario"]), user.id_usuario)
        changes["cpf_usuario"] = (user.cpf_usuario, document)
        user.cpf_usuario = document
    if "telefone_usuario" in data:
        phone = v.phone(data["telefone_usuario"])
        changes["telefone_usuario"] = (user.telefone_usuario, phone)
        user.telefone_usuario = phone
    teacher_fields = set(data) - {"email_usuario", "nome_usuario", "senha_atual"} - CONTACT_FIELDS
    if teacher_fields and not user.professor:
        raise APIError(
            422, "VALIDACAO", "Dados acadêmicos de professor não se aplicam ao estudante."
        )
    teacher = user.professor
    for field in teacher_fields:
        if field == "areas_interesse":
            old = ", ".join(a.nome_area_conhecimento for a in teacher.areas)
            teacher.areas = areas(data[field])
            changes[field] = (old, ", ".join(a.nome_area_conhecimento for a in teacher.areas))
            continue
        if field == "titulacao_professor":
            value = title(data[field])
        elif field == "url_lattes_professor":
            value = v.lattes(data[field])
        else:
            value = v.text(data[field], field) if data[field] else None
        changes[field] = (getattr(teacher, field), value)
        setattr(teacher, field, value)
    if teacher_fields:
        require_institution(teacher)
    user.data_atualizacao_usuario = utcnow()
    audit(user.id_usuario, "atualizacao_cadastro", "usuario", user.id_usuario, changes)
    db.session.commit()


def deactivate(user, secret):
    if not verify_password(user.hash_senha_usuario, secret):
        raise APIError(401, "CREDENCIAIS_INVALIDAS", "Confirme sua senha atual.")
    user.ativo_usuario = False
    if user.professor:
        user.professor.ativo_professor = False
    user.data_atualizacao_usuario = utcnow()
    revoke_sessions(user.id_usuario)
    audit(
        user.id_usuario,
        "inativacao_cadastro",
        "usuario",
        user.id_usuario,
        {"ativo_usuario": (True, False)},
    )
    db.session.commit()
