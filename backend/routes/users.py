from flask import Blueprint, g, request
from sqlalchemy import select

from backend import validation as v
from backend.db import db
from backend.models import Usuario
from backend.security import authenticated, limiter
from backend.serialization import check_version, resource_response, user_json
from backend.services import users

bp = Blueprint("users", __name__, url_prefix="/api/v1/usuarios")


@bp.post("")
@limiter.limit("5 per minute; 30 per hour")
def signup():
    data = v.body(users.SIGNUP_FIELDS, ("nome_usuario", "email_usuario", "senha"), "UC_01_M02")
    user = users.signup(data)
    response = resource_response(
        user, user_json(user), 201, "UC_01_M01", "Cadastro realizado com sucesso!"
    )
    response.headers["Location"] = "/api/v1/usuarios/me"
    return response


@bp.get("/me")
@authenticated()
def me():
    return resource_response(g.user, user_json(g.user))


@bp.patch("/me")
@bp.delete("/me")
@authenticated()
def modify_me():
    user = db.session.scalar(
        select(Usuario)
        .where(Usuario.id_usuario == g.user.id_usuario)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    check_version(user)
    if request.method == "DELETE":
        data = v.body({"senha_atual"}, ("senha_atual",))
        users.deactivate(user, data["senha_atual"])
        return "", 204
    data = v.body(users.PROFILE_FIELDS)
    users.update_profile(user, data)
    return resource_response(user, user_json(user))
