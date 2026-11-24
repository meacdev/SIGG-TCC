"""Single-use tokens of UC14: registration invite and e-mail change (RN 03 and RN 12)."""

import secrets
from datetime import timedelta

from flask import current_app
from sqlalchemy import select, update

from backend import validation as v
from backend.audit import audit
from backend.db import db, utcnow
from backend.errors import APIError
from backend.models import TokenUsuario, Usuario
from backend.security import hash_password, revoke_sessions, secret_digest
from backend.services.auth import clear_lock
from backend.services.mail import send_email_change, send_invite_email

INVITE = "convite_cadastro"
EMAIL_CHANGE = "alterar_email"
INVITE_DAYS = 7
EMAIL_CHANGE_HOURS = 24
INVALID_INVITE = (
    "Este convite é inválido, expirou ou já foi utilizado. Solicite um novo à secretaria."
)
INVALID_EMAIL_TOKEN = "Este link de confirmação é inválido, expirou ou já foi utilizado."


def digest(purpose, raw):
    return secret_digest(f"{purpose}:{raw}")


def issue(user, purpose, lifetime, new_email=None):
    """Invalidate the previous token of the purpose and return the only copy of the new one."""
    now = utcnow()
    db.session.execute(
        update(TokenUsuario)
        .where(
            TokenUsuario.id_usuario == user.id_usuario,
            TokenUsuario.finalidade_token_usuario == purpose,
            TokenUsuario.data_consumo_token_usuario.is_(None),
        )
        .values(data_consumo_token_usuario=now)
        .execution_options(synchronize_session=False)
    )
    raw = secrets.token_urlsafe(32)
    db.session.add(
        TokenUsuario(
            id_usuario=user.id_usuario,
            hash_token_usuario=digest(purpose, raw),
            finalidade_token_usuario=purpose,
            novo_email_token_usuario=new_email,
            data_criacao_token_usuario=now,
            data_expiracao_token_usuario=now + lifetime,
        )
    )
    db.session.flush()
    return raw


def issue_invite(user):
    return issue(user, INVITE, timedelta(days=INVITE_DAYS))


def issue_email_change(user, address):
    return issue(user, EMAIL_CHANGE, timedelta(hours=EMAIL_CHANGE_HOURS), address)


def frontend_link(path, raw):
    # The fragment keeps the secret out of server logs and Referer headers.
    return f"{current_app.config['FRONTEND_URL'].rstrip('/')}/{path}#token={raw}"


def send_invite(address, raw):
    send_invite_email(address, frontend_link("aceitar-convite", raw), INVITE_DAYS)


def send_change(address, raw):
    send_email_change(address, frontend_link("confirmar-email", raw), EMAIL_CHANGE_HOURS)


def try_send(sender, address, raw):
    """The account is already committed, so a mail failure must not report a failed save."""
    try:
        sender(address, raw)
    except APIError:
        return False
    return True


def find(raw, purpose, error, lock=False):
    if not isinstance(raw, str) or not 20 <= len(raw) <= 128:
        raise error
    query = select(TokenUsuario).where(TokenUsuario.hash_token_usuario == digest(purpose, raw))
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    token = db.session.scalar(query)
    if (
        not token
        or token.finalidade_token_usuario != purpose
        or token.data_consumo_token_usuario
        or token.data_expiracao_token_usuario <= utcnow()
    ):
        raise error
    return token


def locked_owner(raw, purpose, error):
    """Lock the user before the token, in the same order used by login and password reset."""
    token = find(raw, purpose, error)
    user = db.session.scalar(
        select(Usuario)
        .where(Usuario.id_usuario == token.id_usuario)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    token = find(raw, purpose, error, lock=True)
    if not user or not user.ativo_usuario:
        raise error
    return user, token


def invite_error():
    return APIError(410, "UC_14_M13", INVALID_INVITE)


def validate_invite(raw):
    token = find(raw, INVITE, invite_error())
    user = db.session.get(Usuario, token.id_usuario)
    if not user or not user.ativo_usuario or user.hash_senha_usuario:
        raise invite_error()
    return {
        "nome_usuario": user.nome_usuario,
        "email_usuario": user.email_usuario,
        "data_expiracao_convite": token.data_expiracao_token_usuario,
    }


def accept_invite(data):
    user, token = locked_owner(data["token"], INVITE, invite_error())
    if user.hash_senha_usuario:
        raise invite_error()
    fields = {}
    try:
        secret = v.password(data["nova_senha"])
    except APIError as error:
        fields["nova_senha"] = error.message
        secret = None
    if data["confirmacao_senha"] != data["nova_senha"]:
        fields["confirmacao_senha"] = "A confirmação da senha não confere."
    if fields:
        raise APIError(422, "UC_14_M03", "Verifique o formato dos campos destacados.", fields)
    now = utcnow()
    user.hash_senha_usuario = hash_password(secret)
    user.email_validado_usuario = True
    user.data_atualizacao_usuario = now
    clear_lock(user)
    token.data_consumo_token_usuario = now
    audit(
        user.id_usuario,
        "aceite_convite",
        "usuario",
        user.id_usuario,
        {"email_validado_usuario": (False, True)},
    )
    db.session.commit()


def confirm_email_change(raw):
    error = APIError(410, "TOKEN_EMAIL_INVALIDO", INVALID_EMAIL_TOKEN)
    user, token = locked_owner(raw, EMAIL_CHANGE, error)
    address = token.novo_email_token_usuario
    if db.session.scalar(
        select(Usuario.id_usuario).where(
            Usuario.email_usuario == address, Usuario.id_usuario != user.id_usuario
        )
    ):
        raise APIError(409, "UC_14_M04", "Este endereço de e-mail já está cadastrado.")
    now = utcnow()
    previous = user.email_usuario
    user.email_usuario = address
    user.email_validado_usuario = True
    user.data_atualizacao_usuario = now
    token.data_consumo_token_usuario = now
    revoke_sessions(user.id_usuario)
    audit(
        user.id_usuario,
        "confirmacao_alteracao_email",
        "usuario",
        user.id_usuario,
        {"email_usuario": (previous, address)},
    )
    # A pending invite sent to the old address must not stay usable.
    invite = issue_invite(user) if not user.hash_senha_usuario else None
    db.session.commit()
    if invite:
        try_send(send_invite, address, invite)
