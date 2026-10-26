import re
import secrets
from datetime import timedelta

import pytest
from flask_jwt_extended import create_access_token, decode_token
from sqlalchemy import select

from backend.db import db, utcnow
from backend.models import RecuperacaoSenha, Sessao
from tests.conftest import headers


def test_login_errors(client, signup, password):
    user = signup()
    assert client.post("/api/v1/auth/login", json={}).status_code == 422
    response = client.post(
        "/api/v1/auth/login", json={"email_usuario": "missing@example.com", "senha": password}
    )
    assert response.status_code == 401
    assert response.json["error"]["code"] == "UC_02_M03"
    assert (
        client.post(
            "/api/v1/auth/login", json={"email_usuario": user["email_usuario"], "senha": "errada"}
        ).status_code
        == 401
    )


def test_refresh_rotation_and_logout(client, signup, login):
    tokens = login(signup())
    assert tokens["expires_in"] == 1200
    assert client.post(
        "/api/v1/auth/refresh", headers=headers(tokens["access_token"])
    ).status_code in {401, 422}
    refreshed = client.post("/api/v1/auth/refresh", headers=headers(tokens["refresh_token"]))
    assert refreshed.status_code == 200, refreshed.json
    new_tokens = refreshed.json["data"]
    assert (
        client.post("/api/v1/auth/refresh", headers=headers(tokens["refresh_token"])).status_code
        == 401
    )
    assert (
        client.delete(
            "/api/v1/auth/logout", headers=headers(new_tokens["refresh_token"])
        ).status_code
        == 204
    )
    for token in (tokens["access_token"], new_tokens["access_token"]):
        assert client.get("/api/v1/usuarios/me", headers=headers(token)).status_code == 401


def test_missing_tampered_expired_orphan_tokens(app, client, signup):
    user = signup()
    assert client.get("/api/v1/usuarios/me").status_code == 401
    assert client.get("/api/v1/usuarios/me", headers=headers("tampered")).status_code == 401
    with app.app_context():
        expired = create_access_token(str(user["id_usuario"]), expires_delta=timedelta(seconds=-1))
        orphan = create_access_token(str(user["id_usuario"]))
    assert client.get("/api/v1/usuarios/me", headers=headers(expired)).status_code == 401
    assert client.get("/api/v1/usuarios/me", headers=headers(orphan)).status_code == 401


def test_idle_timeout(app, client, signup, login):
    tokens = login(signup())
    with app.app_context():
        sid = decode_token(tokens["access_token"])["sid"]
        db.session.get(Sessao, sid).ultima_atividade_em = utcnow() - timedelta(minutes=21)
        db.session.commit()
    response = client.get("/api/v1/usuarios/me", headers=headers(tokens["access_token"]))
    assert response.status_code == 401
    assert response.json["error"]["code"] == "SESSAO_EXPIRADA"
    assert (
        client.post("/api/v1/auth/refresh", headers=headers(tokens["refresh_token"])).status_code
        == 401
    )


def request_recovery(client, app, user):
    response = client.post(
        "/api/v1/auth/recuperacao-senha", json={"email_usuario": user["email_usuario"]}
    )
    assert response.status_code == 202, response.json
    recovery_id = response.json["data"]["id_recuperacao"]
    code = re.search(r"é: ([0-9]{10})\n", app.outbox[-1][2]).group(1)
    return recovery_id, code


def test_full_recovery_flow(app, client, signup, login, password):
    user = signup()
    tokens = login(user)
    recovery_id, code = request_recovery(client, app, user)
    with app.app_context():
        assert db.session.get(RecuperacaoSenha, recovery_id).hash_codigo != code
    response = client.post(
        "/api/v1/auth/recuperacao-senha/verificar",
        json={"id_recuperacao": recovery_id, "codigo": code},
    )
    assert response.status_code == 200
    reset_token = response.json["data"]["token_redefinicao"]
    assert (
        client.post(
            "/api/v1/auth/recuperacao-senha/verificar",
            json={"id_recuperacao": recovery_id, "codigo": code},
        ).status_code
        == 422
    )
    new_password = secrets.token_urlsafe(18)
    data = {
        "id_recuperacao": recovery_id,
        "token_redefinicao": reset_token,
        "nova_senha": new_password,
        "confirmacao_senha": "diferente",
    }
    assert client.post("/api/v1/auth/recuperacao-senha/redefinir", json=data).status_code == 422
    data["confirmacao_senha"] = new_password
    reset_result = client.post("/api/v1/auth/recuperacao-senha/redefinir", json=data)
    assert reset_result.status_code == 200
    assert reset_result.json["code"] == "UC_01_M02"
    assert client.post("/api/v1/auth/recuperacao-senha/redefinir", json=data).status_code == 422
    assert (
        client.get("/api/v1/usuarios/me", headers=headers(tokens["access_token"])).status_code
        == 401
    )
    assert (
        client.post("/api/v1/auth/refresh", headers=headers(tokens["refresh_token"])).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login", json={"email_usuario": user["email_usuario"], "senha": password}
        ).status_code
        == 401
    )
    assert login(user, new_password)["access_token"]


def test_recovery_attempt_limit_and_superseded_requests(app, client, signup):
    user = signup()
    recovery_id, code = request_recovery(client, app, user)
    wrong = "0000000000" if code != "0000000000" else "1111111111"
    for _ in range(5):
        assert (
            client.post(
                "/api/v1/auth/recuperacao-senha/verificar",
                json={"id_recuperacao": recovery_id, "codigo": wrong},
            ).status_code
            == 422
        )
    assert (
        client.post(
            "/api/v1/auth/recuperacao-senha/verificar",
            json={"id_recuperacao": recovery_id, "codigo": code},
        ).status_code
        == 422
    )
    second, code2 = request_recovery(client, app, user)
    third, code3 = request_recovery(client, app, user)
    assert second != third
    assert (
        client.post(
            "/api/v1/auth/recuperacao-senha/verificar",
            json={"id_recuperacao": second, "codigo": code2},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/auth/recuperacao-senha/verificar",
            json={"id_recuperacao": third, "codigo": code3},
        ).status_code
        == 200
    )


def test_unknown_recovery_and_mail_unavailable(app, client, signup):
    user = signup()
    response = client.post(
        "/api/v1/auth/recuperacao-senha", json={"email_usuario": "missing@example.com"}
    )
    assert response.status_code == 202
    assert app.outbox == []
    assert (
        client.post(
            "/api/v1/auth/recuperacao-senha/verificar",
            json={
                "id_recuperacao": response.json["data"]["id_recuperacao"],
                "codigo": "0000000000",
            },
        ).status_code
        == 422
    )
    app.config["MAIL_SENDER"] = None
    assert (
        client.post(
            "/api/v1/auth/recuperacao-senha", json={"email_usuario": user["email_usuario"]}
        ).status_code
        == 503
    )


def test_recovery_expiration(app, client, signup):
    recovery_id, code = request_recovery(client, app, signup())
    with app.app_context():
        record = db.session.scalar(select(RecuperacaoSenha))
        record.expira_em = utcnow() - timedelta(seconds=1)
        db.session.commit()
    assert (
        client.post(
            "/api/v1/auth/recuperacao-senha/verificar",
            json={"id_recuperacao": recovery_id, "codigo": code},
        ).status_code
        == 422
    )


def test_reset_token_expires_with_recovery(app, client, signup, password):
    recovery_id, code = request_recovery(client, app, signup())
    response = client.post(
        "/api/v1/auth/recuperacao-senha/verificar",
        json={"id_recuperacao": recovery_id, "codigo": code},
    )
    with app.app_context():
        db.session.get(RecuperacaoSenha, recovery_id).expira_em = utcnow() - timedelta(seconds=1)
        db.session.commit()
    assert (
        client.post(
            "/api/v1/auth/recuperacao-senha/redefinir",
            json={
                "id_recuperacao": recovery_id,
                "token_redefinicao": response.json["data"]["token_redefinicao"],
                "nova_senha": password,
                "confirmacao_senha": password,
            },
        ).status_code
        == 422
    )


def test_inactive_account_cannot_login_or_receive_reset(app, client, signup, password):
    from backend.models import Usuario

    user = signup()
    with app.app_context():
        db.session.get(Usuario, user["id_usuario"]).ativo_usuario = False
        db.session.commit()
    response = client.post(
        "/api/v1/auth/login", json={"email_usuario": user["email_usuario"], "senha": password}
    )
    assert response.status_code == 403
    assert response.json["error"]["code"] == "CONTA_INATIVA"
    response = client.post(
        "/api/v1/auth/recuperacao-senha", json={"email_usuario": user["email_usuario"]}
    )
    assert response.status_code == 202
    assert app.outbox == []


@pytest.mark.parametrize("secret", [[], {}, 123, True])
def test_non_string_password(client, signup, secret):
    user = signup()
    assert (
        client.post(
            "/api/v1/auth/login", json={"email_usuario": user["email_usuario"], "senha": secret}
        ).status_code
        == 422
    )
