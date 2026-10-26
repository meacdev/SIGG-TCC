from flask import Blueprint, g, jsonify
from flask_jwt_extended import decode_token, get_jwt
from sqlalchemy import update

from backend import validation as v
from backend.audit import audit
from backend.db import db, utcnow
from backend.errors import APIError
from backend.models import Sessao
from backend.security import authenticated, limiter, tokens
from backend.serialization import user_json
from backend.services import auth

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@bp.post("/login")
@limiter.limit("10 per minute; 100 per hour")
def login():
    data = v.body({"email_usuario", "senha"}, ("email_usuario", "senha"))
    user, result = auth.login(data)
    result["usuario"] = user_json(user)
    return jsonify(data=result, code="UC_01_M01", message="Login realizado com sucesso!")


@bp.post("/refresh")
@limiter.limit("30 per minute")
@authenticated(refresh=True)
def refresh():
    claims = get_jwt()
    result = tokens(g.user.id_usuario, claims["sid"], refresh=True)
    # Compare-and-swap prevents two concurrent requests reusing the same refresh token.
    changed = db.session.execute(
        update(Sessao)
        .where(
            Sessao.id_sessao == claims["sid"],
            Sessao.refresh_jti == claims["jti"],
            Sessao.revogada_em.is_(None),
            Sessao.expira_em > utcnow(),
        )
        .values(refresh_jti=decode_token(result["refresh_token"])["jti"])
    )
    if changed.rowcount != 1:
        raise APIError(401, "SESSAO_REVOGADA", "Token de renovação já utilizado.")
    db.session.commit()
    return jsonify(data=result)


@bp.delete("/logout")
@authenticated(any_token=True)
def logout():
    db.session.execute(
        update(Sessao).where(Sessao.id_sessao == get_jwt()["sid"]).values(revogada_em=utcnow())
    )
    audit(g.user.id_usuario, "logout", "usuario", g.user.id_usuario)
    db.session.commit()
    return "", 204


@bp.post("/recuperacao-senha")
@limiter.limit("3 per hour; 1 per minute")
def request_reset():
    data = v.body({"email_usuario"}, ("email_usuario",))
    recovery_id = auth.request_reset(data["email_usuario"])
    return jsonify(
        data={"id_recuperacao": recovery_id},
        code="RECUPERACAO_SOLICITADA",
        message="Se houver uma conta ativa, enviaremos o código por e-mail.",
    ), 202


@bp.post("/recuperacao-senha/verificar")
@limiter.limit("10 per minute")
def verify_reset():
    data = v.body({"id_recuperacao", "codigo"}, ("id_recuperacao", "codigo"))
    return jsonify(data={"token_redefinicao": auth.verify_reset(data)})


@bp.post("/recuperacao-senha/redefinir")
@limiter.limit("10 per minute")
def reset_password():
    fields = {"id_recuperacao", "token_redefinicao", "nova_senha", "confirmacao_senha"}
    auth.reset_password(v.body(fields, fields))
    return jsonify(code="UC_01_M02", message="Senha redefinida com sucesso!")
