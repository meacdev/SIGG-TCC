import os
from datetime import timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from backend.academic_models import Reuniao
from backend.db import db, utcnow
from backend.defense_models import Matricula
from tests.test_enrollments import student as student
from tests.test_works import work_payload as work_payload


@pytest.fixture
def accepted_work(client, student, work_payload, signup, login):
    advisor = signup(nome_usuario="Orientador de Teste")
    headers = {"Authorization": f"Bearer {login(advisor)['access_token']}"}
    response = client.put(
        "/api/v1/meu-trabalho",
        headers=student["headers"],
        json={**work_payload, "id_orientador": advisor["id_usuario"]},
    )
    assert response.status_code == 201, response.json
    data = response.json["data"]
    result = client.post(
        f"/api/v1/orientacoes/{data['orientacoes'][0]['id_orientacao']}/resposta",
        headers={**headers, "If-Match": response.headers["ETag"]},
        json={"decisao": "aceito"},
    )
    assert result.status_code == 200
    return {**data, "advisor_headers": headers}


def test_registration_history_notifications_and_teacher_read_only(
    app, client, teacher, student, accepted_work
):
    stage = accepted_work["id_etapa"]
    path = f"/api/v1/etapas/{stage}/reunioes"
    old_day = (utcnow().date() - timedelta(days=40)).strftime("%d/%m/%Y")
    response = client.post(
        path,
        headers=student["headers"],
        json={"data_encontro": old_day, "resumo": "Revisar os objetivos e a metodologia."},
    )
    assert response.status_code == 201, response.json
    assert response.json["data"]["orientador"] == "Orientador de Teste"
    assert len(app.outbox) == 3
    assert {mail[0] for mail in app.outbox[-2:]} == {student["email_usuario"], app.outbox[0][0]}
    assert client.get(path, headers=teacher["headers"]).json["meta"]["total"] == 1
    assert (
        client.post(
            path,
            headers=teacher["headers"],
            json={"data_encontro": old_day, "resumo": "Não autorizado"},
        ).status_code
        == 403
    )
    report = client.get("/api/v1/acompanhamento-reunioes", headers=teacher["headers"]).json["data"][
        0
    ]
    assert report["quantidade_reunioes"] == 1
    assert report["alerta_inatividade"]
    assert report["dias_sem_reuniao"] >= 39
    assert (
        client.get("/api/v1/acompanhamento-reunioes", headers=student["headers"]).json["data"] == []
    )
    assert client.patch(path, headers=student["headers"], json={}).status_code == 405
    assert client.delete(path, headers=student["headers"]).status_code == 405
    with app.app_context():
        item = db.session.scalar(select(Reuniao))
        assert (
            item.resumo_encaminhamentos_reuniao_orientacao
            == "Revisar os objetivos e a metodologia."
        )


@pytest.mark.parametrize("day", ["31/02/2026", "29/02/2026", "2026-10-01", "01/01/9999", []])
def test_invalid_dates_leave_no_records(app, client, student, accepted_work, day):
    response = client.post(
        f"/api/v1/etapas/{accepted_work['id_etapa']}/reunioes",
        headers=student["headers"],
        json={"data_encontro": day, "resumo": "Resumo"},
    )
    assert response.json["error"]["code"] == "UC_05_M03"
    with app.app_context():
        assert db.session.query(Reuniao).count() == 0


def test_pending_advisor_block_and_absent_work_attendance(
    app, client, student, work_payload, teacher
):
    with app.app_context():
        record = db.session.get(Matricula, work_payload["id_matricula"])
        record.data_matricula_matricula_turma = utcnow() - timedelta(days=31)
        db.session.commit()
    report = client.get("/api/v1/acompanhamento-reunioes", headers=teacher["headers"]).json["data"][
        0
    ]
    assert report["id_etapa"] is None
    assert report["quantidade_reunioes"] == 0
    assert report["alerta_inatividade"]
    work = client.put("/api/v1/meu-trabalho", headers=student["headers"], json=work_payload).json[
        "data"
    ]
    path = f"/api/v1/etapas/{work['id_etapa']}/reunioes"
    assert (
        client.post(
            path,
            headers=student["headers"],
            json={"data_encontro": "01/10/2026", "resumo": "Resumo"},
        ).status_code
        == 403
    )


def test_access_and_removed_enrollment(app, client, student, accepted_work, signup, login):
    path = f"/api/v1/etapas/{accepted_work['id_etapa']}/reunioes"
    outsider = signup()
    headers = {"Authorization": f"Bearer {login(outsider)['access_token']}"}
    assert client.get(path, headers=headers).status_code == 404
    assert client.get("/api/v1/trabalhos-reunioes", headers=headers).json["data"] == []
    assert (
        client.post(path, headers=student["headers"], json={"resumo": "Falta data"}).json["error"][
            "code"
        ]
        == "UC_05_M02"
    )
    with app.app_context():
        db.session.get(
            Matricula, accepted_work["id_matricula"]
        ).situacao_matricula_turma = "removida"
        db.session.commit()
    assert client.get(path, headers=student["headers"]).status_code == 200
    assert (
        client.post(
            path,
            headers=student["headers"],
            json={"data_encontro": "01/10/2026", "resumo": "Resumo"},
        ).status_code
        == 403
    )


@pytest.mark.postgres
def test_database_preserves_meeting_history(app, client, student, accepted_work):
    if not os.getenv("TEST_DATABASE_URL", "").startswith("postgresql"):
        pytest.skip("Requires PostgreSQL history triggers")
    result = client.post(
        f"/api/v1/etapas/{accepted_work['id_etapa']}/reunioes",
        headers=student["headers"],
        json={"data_encontro": "01/10/2026", "resumo": "Registro histórico"},
    )
    assert result.status_code == 201
    with app.app_context():
        for statement in [
            "UPDATE reuniao_orientacao SET resumo_encaminhamentos_reuniao_orientacao = 'Alterado'",
            "DELETE FROM reuniao_orientacao",
            "TRUNCATE reuniao_orientacao",
        ]:
            with pytest.raises(SQLAlchemyError):
                db.session.execute(text(statement))
            db.session.rollback()
        assert db.session.query(Reuniao).count() == 1
