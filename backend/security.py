import hashlib
import hmac
import secrets
from datetime import timedelta
from functools import wraps
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from flask import current_app, g
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt,
    get_jwt_identity,
    verify_jwt_in_request,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import or_, select, update

from backend.db import db, utcnow
from backend.errors import APIError, error_response
from backend.models import Perfil, Sessao, Usuario, UsuarioPerfil

jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["300 per minute"])
hasher = PasswordHasher()
# Equalize password hashing work for unknown users; never an account credential.
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def hash_password(value):
    return hasher.hash(value)


def verify_password(encoded, value):
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
        return False
    try:
        return hasher.verify(encoded or DUMMY_HASH, value)
    except VerificationError, InvalidHashError:
        return False


def secret_digest(value):
    return hmac.new(
        current_app.config["JWT_SECRET_KEY"].encode(), value.encode(), hashlib.sha256
    ).hexdigest()


def roles(user_id):
    now = utcnow()
    return list(
        db.session.scalars(
            select(Perfil.codigo_perfil)
            .join(UsuarioPerfil)
            .where(
                UsuarioPerfil.id_usuario == user_id,
                UsuarioPerfil.data_concessao_usuario_perfil <= now,
                or_(
                    UsuarioPerfil.data_expiracao_usuario_perfil.is_(None),
                    UsuarioPerfil.data_expiracao_usuario_perfil > now,
                ),
            )
            .order_by(Perfil.codigo_perfil)
        )
    )


def require_roles(*allowed):
    if not set(roles(g.user.id_usuario)).intersection(allowed):
        raise APIError(403, "ACESSO_NEGADO", "Seu perfil não permite esta operação.")


def tokens(user_id, session_id, refresh=False):
    claims = {"sid": session_id}
    result = {
        "access_token": create_access_token(str(user_id), additional_claims=claims),
        "token_type": "Bearer",
        "expires_in": int(current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds()),
    }
    if refresh:
        result["refresh_token"] = create_refresh_token(str(user_id), additional_claims=claims)
    return result


def new_session(user):
    session_id = str(uuid4())
    result = tokens(user.id_usuario, session_id, refresh=True)
    db.session.add(
        Sessao(
            id_sessao=session_id,
            id_usuario=user.id_usuario,
            refresh_jti=decode_token(result["refresh_token"])["jti"],
            expira_em=utcnow() + timedelta(hours=current_app.config["SESSION_MAX_HOURS"]),
        )
    )
    return result


def revoke_sessions(user_id):
    db.session.execute(
        update(Sessao)
        .where(Sessao.id_usuario == user_id, Sessao.revogada_em.is_(None))
        .values(revogada_em=utcnow())
    )


def authenticated(refresh=False, any_token=False):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            verify_jwt_in_request(refresh=refresh, verify_type=not any_token)
            claims = get_jwt()
            try:
                user_id = int(get_jwt_identity())
            except ValueError, TypeError:
                raise APIError(401, "TOKEN_INVALIDO", "Token inválido.") from None
            g.user = db.session.get(Usuario, user_id)
            if not g.user or not g.user.ativo_usuario:
                raise APIError(401, "CONTA_INATIVA", "A conta está inativa.")
            now = utcnow()
            conditions = [
                Sessao.id_sessao == claims.get("sid"),
                Sessao.id_usuario == user_id,
                Sessao.revogada_em.is_(None),
                Sessao.expira_em > now,
                Sessao.ultima_atividade_em
                > now - timedelta(minutes=current_app.config["SESSION_IDLE_MINUTES"]),
            ]
            if claims["type"] == "refresh":
                conditions.append(Sessao.refresh_jti == claims["jti"])
            changed = db.session.execute(
                update(Sessao).where(*conditions).values(ultima_atividade_em=now)
            )
            if changed.rowcount != 1:
                raise APIError(401, "SESSAO_EXPIRADA", "Sessão expirada. Entre novamente.")
            db.session.commit()
            return view(*args, **kwargs)

        return wrapped

    return decorator


def register_jwt(app):
    jwt.init_app(app)

    @jwt.token_in_blocklist_loader
    def blocked(header, payload):
        session_id = payload.get("sid")
        if not isinstance(session_id, str):
            return True
        session = db.session.get(Sessao, session_id)
        if not session or str(session.id_usuario) != payload["sub"]:
            return True
        if session.revogada_em or session.expira_em <= utcnow():
            return True
        return payload["type"] == "refresh" and session.refresh_jti != payload["jti"]

    @jwt.expired_token_loader
    def expired(header, payload):
        return error_response(401, "TOKEN_EXPIRADO", "Token expirado.")

    @jwt.invalid_token_loader
    def invalid(reason):
        return error_response(401, "TOKEN_INVALIDO", "Token inválido.")

    @jwt.unauthorized_loader
    def missing(reason):
        return error_response(401, "AUTENTICACAO_OBRIGATORIA", "Informe um token de acesso.")

    @jwt.revoked_token_loader
    def revoked(header, payload):
        return error_response(401, "SESSAO_REVOGADA", "Sessão revogada. Entre novamente.")
