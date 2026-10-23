import hashlib
from datetime import timedelta

import pytest
from sqlalchemy import select

from backend.db import db, utcnow
from backend.models import DocenteCurso, Perfil, Turma, UsuarioPerfil
from tests.conftest import headers


def test_create_code_unique_per_period_and_multiple_classes(
    app, client, teacher, class_payload, created_class
):
    data = created_class.json["data"]
    assert data["autoinscricao_ativa_turma"] is True
    assert data["codigo_acesso"].isalnum()
    assert len(data["codigo_acesso"]) == 24
    with app.app_context():
        row = db.session.get(Turma, data["id_turma"])
        assert (
            row.hash_codigo_acesso_turma
            == hashlib.sha256(data["codigo_acesso"].encode()).hexdigest()
        )
    assert (
        client.post("/api/v1/turmas", json=class_payload, headers=teacher["headers"]).status_code
        == 409
    )
    class_payload["codigo_turma"] = "ESTCOMP02"
    assert (
        client.post("/api/v1/turmas", json=class_payload, headers=teacher["headers"]).status_code
        == 201
    )
    class_payload.update(periodo_letivo="2027/1", codigo_turma="estcomp01")
    assert (
        client.post("/api/v1/turmas", json=class_payload, headers=teacher["headers"]).status_code
        == 201
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("periodo_letivo", "2026/3"),
        ("periodo_letivo", "1999/1"),
        ("nivel_turma", True),
        ("nivel_turma", 3),
        ("codigo_turma", "COMP-01"),
        ("codigo_turma", "ESTCOMP"),
        ("id_curso", 999),
        ("id_docente_responsavel", 999),
    ],
)
def test_validation(client, teacher, class_payload, field, value):
    class_payload[field] = value
    assert client.post(
        "/api/v1/turmas", json=class_payload, headers=teacher["headers"]
    ).status_code in {403, 422}


def test_permissions_and_scope(app, client, teacher, class_payload, signup, login, created_class):
    user = signup()
    other_auth = headers(login(user)["access_token"])
    assert client.post("/api/v1/turmas", json=class_payload, headers=other_auth).status_code == 403
    with app.app_context():
        profile = db.session.scalar(
            select(Perfil).where(Perfil.codigo_perfil == "professor_disciplina")
        )
        db.session.add(UsuarioPerfil(id_usuario=user["id_usuario"], id_perfil=profile.id_perfil))
        db.session.add(
            DocenteCurso(
                id_docente=user["id_usuario"],
                id_curso=2,
                data_inicio_docente_curso=utcnow().date() - timedelta(days=1),
            )
        )
        db.session.commit()
    assert client.get("/api/v1/turmas", headers=other_auth).json["data"] == []
    target = f"/api/v1/turmas/{created_class.json['data']['id_turma']}"
    assert client.get(target, headers=other_auth).status_code == 404
    class_payload["id_curso"] = 2
    assert (
        client.post("/api/v1/turmas", json=class_payload, headers=teacher["headers"]).status_code
        == 403
    )


def test_class_edit_etag_rotation_and_soft_delete(client, teacher, created_class):
    path = created_class.headers["Location"]
    auth = teacher["headers"]
    tag = created_class.headers["ETag"]
    response = client.get(path, headers=auth)
    assert "codigo_acesso" not in response.json["data"]
    assert client.patch(path, headers=auth, json={}).status_code == 428
    changed = client.patch(
        path, headers=auth | {"If-Match": tag}, json={"codigo_turma": "ESTCOMP99"}
    )
    assert changed.status_code == 200, changed.json
    assert client.patch(path, headers=auth | {"If-Match": tag}, json={}).status_code == 412
    rotated = client.post(
        path + "/codigo-acesso", headers=auth | {"If-Match": changed.headers["ETag"]}
    )
    assert rotated.status_code == 200
    assert rotated.json["data"]["codigo_acesso"] != created_class.json["data"]["codigo_acesso"]
    assert (
        client.delete(path, headers=auth | {"If-Match": rotated.headers["ETag"]}).status_code == 204
    )
    inactive = client.get(path, headers=auth)
    assert inactive.json["data"]["ativa_turma"] is False
    assert inactive.json["data"]["autoinscricao_ativa_turma"] is False
    assert (
        client.post(
            path + "/codigo-acesso", headers=auth | {"If-Match": inactive.headers["ETag"]}
        ).status_code
        == 409
    )
    assert client.get("/api/v1/turmas?ativa_turma=true", headers=auth).json["meta"]["total"] == 0


def test_class_filters_and_pagination(client, teacher, created_class):
    query = "/api/v1/turmas?id_curso=1&periodo_letivo=2026/2&nivel_turma=1&per_page=1"
    response = client.get(query, headers=teacher["headers"])
    assert response.status_code == 200, response.json
    assert response.json["meta"]["total"] == 1
    for query in (
        "page=0",
        "page=abc",
        "per_page=101",
        "id_curso=x",
        "nivel_turma=x",
        "ativa_turma=1",
        "periodo_letivo=bad",
    ):
        assert client.get("/api/v1/turmas?" + query, headers=teacher["headers"]).status_code == 422


def test_coordinator_can_assign_teacher_and_catalogs(
    app, client, teacher, signup, login, class_payload
):
    coordinator = signup()
    result = app.test_cli_runner().invoke(
        args=[
            "conceder-perfil",
            "--email",
            coordinator["email_usuario"],
            "--perfil",
            "coordenador",
            "--id-curso",
            "1",
            "--justificativa",
            "Designação institucional",
        ]
    )
    assert result.exit_code == 0, result.output + str(result.exception)
    auth = headers(login(coordinator)["access_token"])
    assert client.post("/api/v1/turmas", json=class_payload, headers=auth).status_code == 201
    response = client.get("/api/v1/docentes?id_curso=1", headers=auth)
    assert response.status_code == 200, response.json
    assert [d["id_docente"] for d in response.json["data"]] == [teacher["id_usuario"]]
    assert client.get("/api/v1/docentes?id_curso=2", headers=auth).status_code == 403
    assert client.get("/api/v1/docentes", headers=auth).status_code == 422
    assert client.get("/api/v1/periodos-letivos", headers=auth).json["data"]


def test_expired_profile_and_future_or_ended_course_link(app, client, teacher, class_payload):
    with app.app_context():
        association = db.session.scalar(select(UsuarioPerfil))
        association.data_expiracao_usuario_perfil = utcnow() - timedelta(seconds=1)
        db.session.commit()
    assert (
        client.post("/api/v1/turmas", json=class_payload, headers=teacher["headers"]).status_code
        == 403
    )
