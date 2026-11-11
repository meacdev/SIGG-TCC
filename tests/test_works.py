import pytest
from sqlalchemy import select

from backend.db import db
from backend.defense_models import Etapa, Matricula, Orientacao, Trabalho
from tests.test_enrollments import student as student


@pytest.fixture
def work_payload(client, teacher, created_class, student):
    result = client.post(
        f"/api/v1/turmas/{created_class.json['data']['id_turma']}/matriculas",
        headers=teacher["headers"],
        json={"id_aluno": student["id_usuario"]},
    )
    assert result.status_code == 201
    return {
        "titulo": "Pesquisa de Teste",
        "tema": "Engenharia de software",
        "modalidade": "monografia",
        "id_matricula": result.json["data"]["id_matricula"],
        "id_curso": 1,
        "id_orientador": teacher["id_usuario"],
        "palavras_chave": ["testes", "qualidade"],
    }


@pytest.fixture
def registered_work(client, student, work_payload):
    result = client.put("/api/v1/meu-trabalho", headers=student["headers"], json=work_payload)
    assert result.status_code == 201, result.json
    return result


def test_create_edit_and_orientation_acceptance(
    app, client, teacher, student, registered_work, work_payload
):
    result = registered_work
    data = result.json["data"]
    assert data["nivel_turma"] == 1
    assert data["orientacoes"][0]["situacao"] == "pendente"
    assert len(app.outbox) == 1
    assert (
        client.put(
            "/api/v1/meu-trabalho", headers=student["headers"], json=work_payload
        ).status_code
        == 428
    )
    current = client.get(f"/api/v1/orientacoes/{data['id_trabalho']}", headers=teacher["headers"])
    decision = client.post(
        f"/api/v1/orientacoes/{data['orientacoes'][0]['id_orientacao']}/resposta",
        headers={**teacher["headers"], "If-Match": current.headers["ETag"]},
        json={"decisao": "aceito"},
    )
    assert decision.status_code == 200, decision.json
    assert decision.json["data"]["orientacoes"][0]["situacao"] == "aceito"
    stale = client.put(
        "/api/v1/meu-trabalho",
        headers={**student["headers"], "If-Match": result.headers["ETag"]},
        json=work_payload,
    )
    assert stale.status_code == 412
    update = client.put(
        "/api/v1/meu-trabalho",
        headers={**student["headers"], "If-Match": decision.headers["ETag"]},
        json={**work_payload, "titulo": "Título atualizado"},
    )
    assert update.status_code == 200
    with app.app_context():
        assert db.session.query(Trabalho).count() == 1
        assert db.session.query(Etapa).count() == 1
        assert db.session.scalar(select(Orientacao)).situacao_aceite_orientacao == "aceito"
    assert client.delete("/api/v1/meu-trabalho", headers=student["headers"]).status_code == 405


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"modalidade": "artigo"}, "UC_06_M03"),
        ({"modalidade": "artigo", "tipo_artigo": "publicado"}, "UC_06_M04"),
        (
            {
                "modalidade": "artigo",
                "tipo_artigo": "publicado",
                "url": "https://example.com/artigo",
                "doi": "inválido",
            },
            "DOI_INVALIDO",
        ),
        ({"id_matricula": 999}, "UC_06_M06"),
        ({"id_curso": 2}, "CURSO_DIVERGENTE"),
        ({"palavras_chave": "não é lista"}, "VALIDACAO"),
    ],
)
def test_validation_preserves_no_partial_records(app, client, student, work_payload, changes, code):
    result = client.put(
        "/api/v1/meu-trabalho", headers=student["headers"], json={**work_payload, **changes}
    )
    assert result.status_code == 422, result.json
    assert result.json["error"]["code"] == code
    with app.app_context():
        assert db.session.query(Trabalho).count() == 0


def test_article_fields_permissions_removed_enrollment_and_rf05(
    app, client, teacher, student, work_payload, signup, login
):
    article = {
        **work_payload,
        "modalidade": "artigo",
        "tipo_artigo": "publicado",
        "url": "https://example.com/artigo",
        "doi": "10.1234/artigo",
    }
    response = client.put("/api/v1/meu-trabalho", headers=student["headers"], json=article)
    assert response.status_code == 201, response.json
    assert response.json["data"]["doi"] == "10.1234/artigo"
    assert (
        client.put(
            "/api/v1/meu-trabalho", headers=teacher["headers"], json=work_payload
        ).status_code
        == 403
    )
    outsider = signup()
    headers = {"Authorization": f"Bearer {login(outsider)['access_token']}"}
    identifier = response.json["data"]["id_trabalho"]
    assert client.get(f"/api/v1/orientacoes/{identifier}", headers=headers).status_code == 404
    assert client.get("/api/v1/orientacoes", headers=headers).json["data"] == []
    swap = client.put(
        "/api/v1/meu-trabalho",
        headers={**student["headers"], "If-Match": response.headers["ETag"]},
        json={**article, "id_orientador": outsider["id_usuario"]},
    )
    assert swap.json["error"]["code"] == "TROCA_ORIENTACAO_RF05"
    with app.app_context():
        db.session.get(
            Matricula, work_payload["id_matricula"]
        ).situacao_matricula_turma = "removida"
        db.session.commit()
    denied = client.put(
        "/api/v1/meu-trabalho",
        headers={**student["headers"], "If-Match": response.headers["ETag"]},
        json=article,
    )
    assert denied.json["error"]["code"] == "UC_06_M06"
