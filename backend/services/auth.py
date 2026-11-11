import hmac
import secrets
from datetime import timedelta
from uuid import uuid4

from flask import current_app
from sqlalchemy import select, update

from backend import validation as v
from backend.audit import audit
from backend.db import db, utcnow
from backend.errors import APIError
from backend.models import RecuperacaoSenha, Usuario
from backend.security import (
    hash_password,
    hasher,
    new_session,
    revoke_sessions,
    secret_digest,
    verify_password,
)
from backend.services.mail import require_mail, send_reset_email


def login(data):
    address = v.email(data["email_usuario"])
    secret = data["senha"]
    v.text(secret, "senha", 128)
    # Serializes account changes and session creation (including password reset).
    user = db.session.scalar(
        select(Usuario).where(Usuario.email_usuario == address).with_for_update()
    )
    valid = verify_password(user.hash_senha_usuario if user else None, secret)
    if not user:
        raise APIError(
            401,
            "UC_02_M03",
            "Conta não cadastrada, entre em contato com a secretaria.",
        )
    if not valid:
        raise APIError(401, "CREDENCIAIS_INVALIDAS", "E-mail ou senha inválidos.")
    if not user.ativo_usuario:
        raise APIError(403, "CONTA_INATIVA", "A conta está inativa.")
    if hasher.check_needs_rehash(user.hash_senha_usuario):
        user.hash_senha_usuario = hash_password(secret)
    result = new_session(user)
    audit(user.id_usuario, "login", "usuario", user.id_usuario)
    db.session.commit()
    return user, result


def request_reset(address):
    require_mail()
    address = v.email(address)
    recovery_id = str(uuid4())
    user = db.session.scalar(
        select(Usuario)
        .where(Usuario.email_usuario == address, Usuario.ativo_usuario.is_(True))
        .with_for_update()
    )
    if user:
        now = utcnow()
        db.session.execute(
            update(RecuperacaoSenha)
            .where(
                RecuperacaoSenha.id_usuario == user.id_usuario, RecuperacaoSenha.usada_em.is_(None)
            )
            .values(usada_em=now)
        )
        code = "".join(secrets.choice("0123456789") for _ in range(10))
        db.session.add(
            RecuperacaoSenha(
                id_recuperacao=recovery_id,
                id_usuario=user.id_usuario,
                hash_codigo=secret_digest(f"{recovery_id}:{code}"),
                expira_em=now + timedelta(minutes=current_app.config["RESET_CODE_MINUTES"]),
            )
        )
        db.session.flush()
        send_reset_email(address, code)
        audit(user.id_usuario, "solicitacao_recuperacao_senha", "usuario", user.id_usuario)
        db.session.commit()
    return recovery_id


def recovery(data):
    recovery_id = v.text(data["id_recuperacao"], "id_recuperacao", 36, 36)
    record = db.session.scalar(
        select(RecuperacaoSenha)
        .where(RecuperacaoSenha.id_recuperacao == recovery_id)
        .with_for_update()
    )
    if not record or record.usada_em or record.expira_em <= utcnow() or record.tentativas >= 5:
        raise APIError(422, "RECUPERACAO_INVALIDA", "Recuperação inválida ou expirada.")
    user = db.session.get(Usuario, record.id_usuario)
    if not user or not user.ativo_usuario:
        raise APIError(422, "RECUPERACAO_INVALIDA", "Recuperação inválida ou expirada.")
    return record


def verify_reset(data):
    record = recovery(data)
    code = v.text(data["codigo"], "codigo", 10, 10)
    if record.hash_token_redefinicao:
        raise APIError(422, "RECUPERACAO_INVALIDA", "O código já foi utilizado.")
    if not hmac.compare_digest(
        record.hash_codigo, secret_digest(f"{record.id_recuperacao}:{code}")
    ):
        record.tentativas += 1
        db.session.commit()
        raise APIError(422, "CODIGO_INVALIDO", "Código inválido ou expirado.")
    token = secrets.token_urlsafe(32)
    record.hash_token_redefinicao = secret_digest(token)
    db.session.commit()
    return token


def reset_password(data):
    recovery_id = v.text(data["id_recuperacao"], "id_recuperacao", 36, 36)
    secret = v.password(data["nova_senha"])
    if secret != data["confirmacao_senha"]:
        raise APIError(422, "SENHAS_DIFERENTES", "A confirmação da senha não confere.")
    token = v.text(data["token_redefinicao"], "token_redefinicao", 128)
    # Lock the user before the recovery row, consistently with request_reset/login.
    user_id = db.session.scalar(
        select(RecuperacaoSenha.id_usuario).where(RecuperacaoSenha.id_recuperacao == recovery_id)
    )
    user = (
        db.session.scalar(select(Usuario).where(Usuario.id_usuario == user_id).with_for_update())
        if user_id
        else None
    )
    record = recovery(data)
    if (
        not user
        or not user.ativo_usuario
        or not record.hash_token_redefinicao
        or not hmac.compare_digest(record.hash_token_redefinicao, secret_digest(token))
    ):
        raise APIError(422, "RECUPERACAO_INVALIDA", "Recuperação inválida ou expirada.")
    user.hash_senha_usuario = hash_password(secret)
    user.data_atualizacao_usuario = utcnow()
    db.session.execute(
        update(RecuperacaoSenha)
        .where(RecuperacaoSenha.id_usuario == user.id_usuario, RecuperacaoSenha.usada_em.is_(None))
        .values(usada_em=utcnow())
    )
    revoke_sessions(user.id_usuario)
    audit(user.id_usuario, "redefinicao_senha", "usuario", user.id_usuario)
    db.session.commit()
