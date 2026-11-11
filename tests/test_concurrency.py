from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from backend.db import db
from tests.conftest import headers


@pytest.fixture
def postgres_only(app):
    with app.app_context():
        if db.engine.dialect.name != "postgresql":
            pytest.skip("Row-lock and race checks require PostgreSQL")


def race(actions):
    barrier = Barrier(len(actions))

    def run(action):
        barrier.wait(timeout=10)
        return action()

    with ThreadPoolExecutor(max_workers=len(actions)) as executor:
        return list(executor.map(run, actions))


def test_refresh_token_can_be_consumed_once_concurrently(postgres_only, app, signup, login):
    token = login(signup())["refresh_token"]

    def action():
        with app.test_client() as client:
            return client.post("/api/v1/auth/refresh", headers=headers(token)).status_code

    assert sorted(race([action, action])) == [200, 401]


def test_two_edits_with_same_etag_do_not_lose_updates(postgres_only, app, teacher, created_class):
    path = created_class.headers["Location"]
    auth = teacher["headers"] | {"If-Match": created_class.headers["ETag"]}

    def action():
        with app.test_client() as client:
            return client.patch(path, headers=auth, json={"codigo_turma": "ESTCOMP77"}).status_code

    assert sorted(race([action, action])) == [200, 412]


def test_duplicate_registration_race_is_conflict(postgres_only, app, password):
    payload = {
        "nome_usuario": "Concorrente",
        "email_usuario": "race@example.com",
        "senha": password,
        "titulacao_docente": "mestre",
    }

    def action():
        with app.test_client() as client:
            response = client.post("/api/v1/usuarios", json=payload)
            if response.status_code == 409:
                assert response.json["error"]["code"] == "UC_01_M04"
            return response.status_code

    assert sorted(race([action, action])) == [201, 409]


def test_duplicate_class_race_is_conflict(postgres_only, app, teacher, class_payload):
    def action():
        with app.test_client() as client:
            response = client.post("/api/v1/turmas", headers=teacher["headers"], json=class_payload)
            if response.status_code == 409:
                assert response.json["error"]["code"] == "TURMA_DUPLICADA"
            return response.status_code

    assert sorted(race([action, action])) == [201, 409]
