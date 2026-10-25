from sqlalchemy import select

from backend import validation as v
from backend.audit import audit
from backend.db import db, utcnow
from backend.errors import APIError
from backend.models import Aluno, AreaConhecimento, Curso, Docente, Perfil, Usuario, UsuarioPerfil
from backend.security import hash_password, revoke_sessions, verify_password

SIGNUP_FIELDS = {
    "nome_usuario",
    "email_usuario",
    "senha",
    "tipo_cadastro",
    "titulacao_docente",
    "tipo_docente",
    "instituicao_origem_docente",
    "url_lattes_docente",
    "areas_interesse",
    "matricula_aluno",
    "id_curso",
}
PROFILE_FIELDS = {
    "nome_usuario",
    "email_usuario",
    "titulacao_docente",
    "url_lattes_docente",
    "areas_interesse",
    "instituicao_origem_docente",
    "senha_atual",
}
TITLES = ("especialista", "mestre", "doutor")


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
    name = v.text(data["nome_usuario"], "nome_usuario")
    address = v.email(data["email_usuario"], "UC_01_M03")
    secret = v.password(data["senha"])
    kind = v.choice(data.get("tipo_cadastro", "docente"), "tipo_cadastro", ("docente", "aluno"))
    if db.session.scalar(select(Usuario.id_usuario).where(Usuario.email_usuario == address)):
        raise APIError(409, "UC_01_M04", "Este endereço de e-mail já está cadastrado.")
    user = Usuario(
        nome_usuario=name, email_usuario=address, hash_senha_usuario=hash_password(secret)
    )
    db.session.add(user)
    db.session.flush()
    if kind == "docente":
        if not data.get("titulacao_docente"):
            raise APIError(
                422,
                "UC_01_M02",
                "Preencha todos os campos obrigatórios.",
                {"titulacao_docente": "Obrigatório para docente."},
            )
        if {"matricula_aluno", "id_curso"}.intersection(data):
            raise APIError(
                422, "VALIDACAO", "Campos de estudante não pertencem ao cadastro docente."
            )
        teacher = Docente(
            id_docente=user.id_usuario,
            tipo_docente=v.choice(
                data.get("tipo_docente", "interno"), "tipo_docente", ("interno", "externo")
            ),
            titulacao_docente=v.choice(data["titulacao_docente"], "titulacao_docente", TITLES),
            url_lattes_docente=v.lattes(data.get("url_lattes_docente")),
            instituicao_origem_docente=(
                v.text(data["instituicao_origem_docente"], "instituicao_origem_docente")
                if data.get("instituicao_origem_docente")
                else None
            ),
        )
        db.session.add(teacher)
        teacher.areas = areas(data.get("areas_interesse", []))
    else:
        if any(
            k in data
            for k in {
                "titulacao_docente",
                "tipo_docente",
                "areas_interesse",
                "url_lattes_docente",
                "instituicao_origem_docente",
            }
        ):
            raise APIError(
                422, "VALIDACAO", "Campos docentes não pertencem ao cadastro de estudante."
            )
        course_id = v.integer(data.get("id_curso"), "id_curso")
        course = db.session.get(Curso, course_id)
        if not course or not course.ativo_curso:
            raise APIError(422, "CURSO_INVALIDO", "Selecione um curso ativo.")
        enrollment = v.text(data.get("matricula_aluno"), "matricula_aluno", 30)
        if db.session.scalar(select(Aluno.id_aluno).where(Aluno.matricula_aluno == enrollment)):
            raise APIError(409, "MATRICULA_DUPLICADA", "Matrícula já cadastrada.")
        db.session.add(
            Aluno(id_aluno=user.id_usuario, matricula_aluno=enrollment, id_curso=course_id)
        )
        profile = db.session.scalar(select(Perfil).where(Perfil.codigo_perfil == "aluno"))
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
        name = v.text(data["nome_usuario"], "nome_usuario")
        changes["nome_usuario"] = (user.nome_usuario, name)
        user.nome_usuario = name
    teacher_fields = set(data) - {"email_usuario", "nome_usuario", "senha_atual"}
    if teacher_fields and not user.docente:
        raise APIError(422, "VALIDACAO", "Dados acadêmicos de docente não se aplicam ao estudante.")
    teacher = user.docente
    for field in teacher_fields:
        if field == "areas_interesse":
            old = ", ".join(a.nome_area_conhecimento for a in teacher.areas)
            teacher.areas = areas(data[field])
            changes[field] = (old, ", ".join(a.nome_area_conhecimento for a in teacher.areas))
            continue
        if field == "titulacao_docente":
            value = v.choice(data[field], field, TITLES)
        elif field == "url_lattes_docente":
            value = v.lattes(data[field])
        else:
            value = v.text(data[field], field) if data[field] else None
        changes[field] = (getattr(teacher, field), value)
        setattr(teacher, field, value)
    user.data_atualizacao_usuario = utcnow()
    audit(user.id_usuario, "atualizacao_cadastro", "usuario", user.id_usuario, changes)
    db.session.commit()


def deactivate(user, secret):
    if not verify_password(user.hash_senha_usuario, secret):
        raise APIError(401, "CREDENCIAIS_INVALIDAS", "Confirme sua senha atual.")
    user.ativo_usuario = False
    if user.docente:
        user.docente.ativo_docente = False
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
