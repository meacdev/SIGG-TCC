from datetime import timedelta

import pytest
from sqlalchemy import select

from backend.academic_models import NotificacaoAcademica
from backend.db import db, utcnow
from backend.defense_models import Matricula
from backend.models import Turma
from backend.services import academic_mail


@pytest.fixture
def student(client, password, login):
    response = client.post(
        "/api/v1/usuarios",
        json={
            "nome_usuario": "Estudante Teste",
            "email_usuario": "estudante@example.com",
            "senha": password,
            "tipo_cadastro": "aluno",
            "id_curso": 1,
            "matricula_aluno": "000123",
        },
    )
    assert response.status_code == 201
    user = response.json["data"]
    user["headers"] = {"Authorization": f"Bearer {login(user)['access_token']}"}
    return user


def test_enroll_search_duplicate_remove_history_and_reenroll(
    app, client, created_class, teacher, student
):
    class_id = created_class.json["data"]["id_turma"]
    base = f"/api/v1/turmas/{class_id}"
    headers = teacher["headers"]
    assert (
        client.get(base + "/estudantes?q=000", headers=headers).json["data"][0]["id_aluno"]
        == student["id_usuario"]
    )
    assert client.get(base + "/estudantes?q=%25%25", headers=headers).json["data"] == []
    response = client.post(
        base + "/matriculas", headers=headers, json={"id_aluno": student["id_usuario"]}
    )
    assert response.status_code == 201, response.json
    identifier = response.json["data"]["id_matricula"]
    assert (
        client.post(
            base + "/matriculas", headers=headers, json={"id_aluno": student["id_usuario"]}
        ).status_code
        == 409
    )
    assert (
        len(client.get("/api/v1/minhas-matriculas", headers=student["headers"]).json["data"]) == 1
    )
    removal = base + f"/matriculas/{identifier}"
    payload = {
        "confirmacao": f"{student['nome_usuario']}/{created_class.json['data']['codigo_turma']}",
        "motivo": "Inclusão indevida",
    }
    assert client.delete(removal, headers=headers, json=payload).status_code == 428
    version = {**headers, "If-Match": response.headers["ETag"]}
    assert (
        client.delete(
            removal, headers=version, json={**payload, "confirmacao": "errada"}
        ).status_code
        == 422
    )
    removed = client.delete(removal, headers=version, json=payload)
    assert removed.status_code == 200, removed.json
    assert removed.json["data"]["notificacao"] == "enviada"
    assert len(app.outbox) == 1
    assert client.get("/api/v1/minhas-matriculas", headers=student["headers"]).json["data"] == []
    enrolled = client.post(
        base + "/matriculas", headers=headers, json={"id_aluno": student["id_usuario"]}
    )
    assert enrolled.json["data"]["id_matricula"] == identifier
    assert client.delete(removal, headers=version, json=payload).status_code == 412
    with app.app_context():
        assert db.session.query(Matricula).count() == 1
        academic_mail.deliver()
    assert len(app.outbox) == 1


def test_self_enrollment_scope_expiry_and_rotation(
    app, client, teacher, created_class, student, signup, login
):
    base = "/api/v1/matriculas/autoinscricao"
    code = created_class.json["data"]["codigo_acesso"]
    assert (
        client.post(base, headers=teacher["headers"], json={"codigo_acesso": code}).status_code
        == 403
    )
    wrong = client.post(
        "/api/v1/usuarios",
        json={
            "nome_usuario": "Outro estudante",
            "email_usuario": "outro@example.com",
            "senha": "Senha de teste UC04 123",
            "tipo_cadastro": "aluno",
            "id_curso": 2,
            "matricula_aluno": "000999",
        },
    ).json["data"]
    headers = {"Authorization": f"Bearer {login(wrong, 'Senha de teste UC04 123')['access_token']}"}
    assert client.post(base, headers=headers, json={"codigo_acesso": code}).status_code == 422
    assert (
        client.get(
            f"/api/v1/turmas/{created_class.json['data']['id_turma']}/estudantes?q=00",
            headers=student["headers"],
        ).status_code
        == 403
    )
    with app.app_context():
        turma = db.session.get(Turma, created_class.json["data"]["id_turma"])
        turma.data_expiracao_acesso_turma = utcnow() - timedelta(minutes=1)
        db.session.commit()
    assert (
        client.post(base, headers=student["headers"], json={"codigo_acesso": code}).status_code
        == 422
    )
    class_path = f"/api/v1/turmas/{created_class.json['data']['id_turma']}"
    etag = client.get(class_path, headers=teacher["headers"]).headers["ETag"]
    new = client.post(
        class_path + "/codigo-acesso", headers={**teacher["headers"], "If-Match": etag}
    ).json["data"]["codigo_acesso"]
    assert (
        client.post(base, headers=student["headers"], json={"codigo_acesso": code}).status_code
        == 422
    )
    assert (
        client.post(base, headers=student["headers"], json={"codigo_acesso": new}).status_code
        == 201
    )


def test_failed_email_is_persisted_and_retried(app, client, created_class, teacher, student):
    base = f"/api/v1/turmas/{created_class.json['data']['id_turma']}/matriculas"
    response = client.post(
        base, headers=teacher["headers"], json={"id_aluno": student["id_usuario"]}
    )

    def fail(*args):
        raise OSError("Simulated transport failure")

    app.config["MAIL_SENDER"] = fail
    removed = client.delete(
        base + f"/{response.json['data']['id_matricula']}",
        headers={**teacher["headers"], "If-Match": response.headers["ETag"]},
        json={
            "confirmacao": (
                f"{student['nome_usuario']}/{created_class.json['data']['codigo_turma']}"
            ),
            "motivo": "Correção",
        },
    )
    assert removed.status_code == 200
    assert removed.json["data"]["notificacao"] == "falha"
    app.config["MAIL_SENDER"] = lambda *args: app.outbox.append(args)
    with app.app_context():
        academic_mail.deliver()
        item = db.session.scalar(select(NotificacaoAcademica))
        assert item.situacao_notificacao == "enviada"
        assert item.tentativas_notificacao == 2
    assert len(app.outbox) == 1
