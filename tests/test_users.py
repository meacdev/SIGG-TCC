import pytest
from sqlalchemy import func, select

from backend.db import db
from backend.models import Auditoria, Usuario
from backend.security import hasher
from tests.conftest import headers


def test_signup_hash_timestamp_and_optional_fields(app, signup, password):
    user = signup(
        email_usuario="PROFESSOR@example.com",
        areas_interesse=["IA", "IA", "Engenharia"],
        url_lattes_docente="https://lattes.cnpq.br/123",
    )
    assert user["email_usuario"] == "professor@example.com"
    assert user["perfis"] == []
    assert user["data_criacao_usuario"].endswith("Z")
    assert sorted(user["docente"]["areas_interesse"]) == ["Engenharia", "IA"]
    with app.app_context():
        row = db.session.get(Usuario, user["id_usuario"])
        assert row.hash_senha_usuario != password
        assert row.hash_senha_usuario.startswith("$argon2id$")
        assert hasher.verify(row.hash_senha_usuario, password)
        assert db.session.scalar(select(func.count()).select_from(Auditoria)) == 1


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("email_usuario", "inválido", "UC_01_M03"),
        ("nome_usuario", " ", "VALIDACAO"),
        ("senha", "curta", "SENHA_INVALIDA"),
        ("titulacao_docente", "graduado", "VALIDACAO"),
        ("titulacao_docente", None, "UC_01_M02"),
        ("url_lattes_docente", "javascript:alert(1)", "URL_INVALIDA"),
        ("url_lattes_docente", "https://", "URL_INVALIDA"),
        ("areas_interesse", "IA", "VALIDACAO"),
        ("tipo_cadastro", "admin", "VALIDACAO"),
    ],
)
def test_registration_validation(client, password, field, value, code):
    payload = {
        "nome_usuario": "Nome",
        "email_usuario": "pessoa@example.com",
        "senha": password,
        "titulacao_docente": "mestre",
        field: value,
    }
    response = client.post("/api/v1/usuarios", json=payload)
    assert response.status_code == 422
    assert response.json["error"]["code"] == code


def test_duplicate_email_is_case_insensitive(client, signup, password):
    signup(email_usuario="pessoa@example.com")
    response = client.post(
        "/api/v1/usuarios",
        json={
            "nome_usuario": "Outra",
            "email_usuario": "PESSOA@example.com",
            "senha": password,
            "titulacao_docente": "doutor",
        },
    )
    assert response.status_code == 409
    assert response.json["error"]["code"] == "UC_01_M04"


@pytest.mark.parametrize("data", [{}, {"perfis": ["coordenador"]}, []])
def test_missing_fields_and_mass_assignment(client, data):
    assert client.post("/api/v1/usuarios", json=data).status_code == 422


def test_student_registration(client, password):
    payload = {
        "nome_usuario": "Estudante",
        "email_usuario": "aluno@example.com",
        "senha": password,
        "tipo_cadastro": "aluno",
        "matricula_aluno": "00012",
        "id_curso": 1,
    }
    response = client.post("/api/v1/usuarios", json=payload)
    assert response.status_code == 201, response.json
    assert response.json["data"]["perfis"] == ["aluno"]
    assert response.json["data"]["aluno"]["matricula_aluno"] == "00012"
    payload["email_usuario"] = "outro@example.com"
    assert client.post("/api/v1/usuarios", json=payload).status_code == 409
    payload["id_curso"] = 999
    assert client.post("/api/v1/usuarios", json=payload).status_code == 422
    payload["titulacao_docente"] = "mestre"
    assert client.post("/api/v1/usuarios", json=payload).status_code == 422


def test_profile_update_and_logical_deletion(client, signup, login, password, app):
    user = signup()
    auth = headers(login(user)["access_token"])
    response = client.get("/api/v1/usuarios/me", headers=auth)
    tag = response.headers["ETag"]
    assert "hash_senha" not in str(response.json)
    assert client.patch("/api/v1/usuarios/me", headers=auth, json={}).status_code == 428
    changed = client.patch(
        "/api/v1/usuarios/me",
        headers=auth | {"If-Match": tag},
        json={
            "nome_usuario": "Novo Nome",
            "titulacao_docente": "doutor",
            "areas_interesse": ["IA"],
            "instituicao_origem_docente": "UFAM",
            "url_lattes_docente": "https://lattes.cnpq.br/456",
        },
    )
    assert changed.status_code == 200, changed.json
    assert changed.json["data"]["nome_usuario"] == "Novo Nome"
    assert changed.headers["ETag"] != tag
    assert (
        client.patch(
            "/api/v1/usuarios/me",
            headers=auth | {"If-Match": tag},
            json={"nome_usuario": "Perdido"},
        ).status_code
        == 412
    )
    delete_headers = auth | {"If-Match": changed.headers["ETag"]}
    assert (
        client.delete(
            "/api/v1/usuarios/me", headers=delete_headers, json={"senha_atual": "errada"}
        ).status_code
        == 401
    )
    assert (
        client.delete(
            "/api/v1/usuarios/me", headers=delete_headers, json={"senha_atual": password}
        ).status_code
        == 204
    )
    assert client.get("/api/v1/usuarios/me", headers=auth).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login", json={"email_usuario": user["email_usuario"], "senha": password}
        ).status_code
        == 403
    )
    with app.app_context():
        assert db.session.get(Usuario, user["id_usuario"]).ativo_usuario is False


def test_email_change_requires_password_and_revokes_session(client, signup, login, password):
    user = signup()
    auth = headers(login(user)["access_token"])
    tag = client.get("/api/v1/usuarios/me", headers=auth).headers["ETag"]
    data = {"email_usuario": "novo@example.com"}
    assert (
        client.patch("/api/v1/usuarios/me", headers=auth | {"If-Match": tag}, json=data).status_code
        == 401
    )
    data["senha_atual"] = password
    assert (
        client.patch("/api/v1/usuarios/me", headers=auth | {"If-Match": tag}, json=data).status_code
        == 200
    )
    assert client.get("/api/v1/usuarios/me", headers=auth).status_code == 401
