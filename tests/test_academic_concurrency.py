import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.test_enrollments import student as student
from tests.test_works import registered_work as registered_work
from tests.test_works import work_payload as work_payload

pytestmark = pytest.mark.postgres


def require_postgres():
    if not os.getenv("TEST_DATABASE_URL", "").startswith("postgresql"):
        pytest.skip("Requires PostgreSQL transactional row locks")


def test_concurrent_enrollment_has_one_link(app, created_class, teacher, student):
    require_postgres()

    def send(_):
        with app.test_client() as client:
            return client.post(
                f"/api/v1/turmas/{created_class.json['data']['id_turma']}/matriculas",
                headers=teacher["headers"],
                json={"id_aluno": student["id_usuario"]},
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(send, range(2))) == [201, 409]


def test_concurrent_work_creation_has_one_work(app, student, work_payload):
    require_postgres()

    def send(_):
        with app.test_client() as client:
            return client.put(
                "/api/v1/meu-trabalho", headers=student["headers"], json=work_payload
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(send, range(2))) == [201, 428]


def test_concurrent_orientation_response_preserves_one_decision(app, teacher, registered_work):
    require_postgres()
    identifier = registered_work.json["data"]["orientacoes"][0]["id_orientacao"]
    headers = {**teacher["headers"], "If-Match": registered_work.headers["ETag"]}

    def send(decision):
        with app.test_client() as client:
            return client.post(
                f"/api/v1/orientacoes/{identifier}/resposta",
                headers=headers,
                json={"decisao": decision},
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(send, ["aceito", "recusado"])) == [200, 412]
