from functools import wraps

from flask import Blueprint, jsonify, request

from backend import validation as v
from backend.db import db
from backend.security import authenticated
from backend.serialization import resource_response
from backend.services import admin_users as service

bp = Blueprint("admin_users", __name__, url_prefix="/api/v1/admin/usuarios")


def administrator(view):
    """RN 01: every operation checks the session and the role on the server."""

    @wraps(view)
    @authenticated()
    def wrapped(*args, **kwargs):
        service.require_admin()
        return view(*args, **kwargs)

    return wrapped


def response(user, status=200, number=None, extra=None):
    db.session.refresh(user)
    data = service.describe_one(user)
    if extra:
        data.update(extra)
    code = f"UC_14_M{number:02d}" if number else None
    return resource_response(user, data, status, code, service.MESSAGES.get(number))


@bp.get("")
@administrator
def list_users():
    page, size = v.pagination()
    query = service.list_query(request.args)
    result = db.paginate(query, page=page, per_page=size, max_per_page=100, error_out=False)
    return jsonify(
        data=service.describe(result.items) if result.items else [],
        meta={"page": page, "per_page": size, "total": result.total, "pages": result.pages},
    )


@bp.post("")
@administrator
def pre_register():
    user, sent = service.pre_register(v.body(service.CREATE_FIELDS))
    result = response(user, 201, 1, {"convite_enviado": sent})
    if not sent:
        payload = result.get_json()
        payload.update(code="UC_14_CONVITE_PENDENTE", message=service.INVITE_NOT_SENT)
        result.set_data(jsonify(payload).get_data())
    result.headers["Location"] = f"/api/v1/admin/usuarios/{user.id_usuario}"
    return result


@bp.get("/<int:id_usuario>")
@administrator
def detail(id_usuario):
    return response(service.get_user(id_usuario))


@bp.patch("/<int:id_usuario>")
@administrator
def update(id_usuario):
    user, email_change = service.update_user(id_usuario, v.body(service.UPDATE_FIELDS))
    return response(user, 200, 15, {"alteracao_email": email_change})


@bp.post("/<int:id_usuario>/convite")
@administrator
def resend_invite(id_usuario):
    return response(service.resend_invite(id_usuario), 200, 18)


@bp.patch("/<int:id_usuario>/situacao")
@administrator
def change_status(id_usuario):
    data = v.body(service.STATUS_FIELDS)
    return response(service.change_status(id_usuario, data), 200, 17)


@bp.post("/<int:id_usuario>/perfis")
@administrator
def grant_profile(id_usuario):
    data = v.body(service.GRANT_FIELDS)
    return response(service.grant_profile(id_usuario, data), 200, 16)


@bp.post("/<int:id_usuario>/perfis/revogar")
@administrator
def revoke_profile(id_usuario):
    data = v.body(service.REVOKE_FIELDS)
    return response(service.revoke_profile(id_usuario, data), 200, 16)
