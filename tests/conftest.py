import os
import secrets
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from backend.app import create_app
from backend.cli import seed_profiles
from backend.db import db, utcnow
from backend.models import Curso, DocenteCurso, Perfil, UsuarioPerfil


@pytest.fixture
def password():
    return secrets.token_urlsafe(18)


@pytest.fixture
def app():
    database_url = os.getenv("TEST_DATABASE_URL", "sqlite://")
    schema = "sigg_test_" + uuid4().hex
    admin = None
    options = {"pool_pre_ping": True}
    if database_url.startswith("postgresql"):
        admin = create_engine(database_url)
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        options["connect_args"] = {"options": f"-c search_path={schema}"}
    outbox = []
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": database_url,
            "SQLALCHEMY_ENGINE_OPTIONS": options,
            "JWT_SECRET_KEY": secrets.token_hex(32),
            "RATELIMIT_ENABLED": False,
            "APP_ENV": "testing",
            "SMTP_HOST": "",
            "SMTP_FROM": "",
            "SMTP_SSL": False,
            "SMTP_STARTTLS": True,
            "CORS_ORIGINS": ["http://localhost:5173"],
            "MAIL_SENDER": lambda *args: outbox.append(args),
        }
    )
    app.outbox = outbox
    with app.app_context():
        if admin:
            sql = Path("backend/sql/000_schema_fornecido.sql").read_text(encoding="utf-8-sig")
            with db.engine.begin() as connection:
                connection.exec_driver_sql(sql)
            result = app.test_cli_runner().invoke(args=["db-upgrade"])
            assert result.exit_code == 0, result.output + str(result.exception)
        else:
            db.create_all()
            # Read-only delivery projections use independent metadata, not duplicate ORM models.
            from backend.services.monitoring_sources import metadata as delivery_metadata

            delivery_metadata.create_all(db.engine)
        seed_profiles()
        db.session.add_all(
            [
                Curso(codigo_curso="COMP", nome_curso="Computação"),
                Curso(codigo_curso="MAT", nome_curso="Matemática"),
            ]
        )
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
    if admin:
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def signup(client, password):
    def register(**overrides):
        payload = {
            "nome_usuario": "Docente Teste",
            "email_usuario": f"{uuid4().hex}@example.com",
            "senha": password,
            "titulacao_docente": "mestre",
        }
        payload.update(overrides)
        response = client.post("/api/v1/usuarios", json=payload)
        assert response.status_code == 201, response.json
        return response.json["data"]

    return register


@pytest.fixture
def login(client, password):
    def authenticate(user, secret=None):
        response = client.post(
            "/api/v1/auth/login",
            json={"email_usuario": user["email_usuario"], "senha": secret or password},
        )
        assert response.status_code == 200, response.json
        return response.json["data"]

    return authenticate


def headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def teacher(app, signup, login):
    user = signup()
    with app.app_context():
        profile = db.session.scalar(
            db.select(Perfil).where(Perfil.codigo_perfil == "professor_disciplina")
        )
        db.session.add(UsuarioPerfil(id_usuario=user["id_usuario"], id_perfil=profile.id_perfil))
        db.session.add(
            DocenteCurso(
                id_docente=user["id_usuario"],
                id_curso=1,
                data_inicio_docente_curso=utcnow().date() - timedelta(days=1),
            )
        )
        db.session.commit()
    user["tokens"] = login(user)
    user["headers"] = headers(user["tokens"]["access_token"])
    return user


@pytest.fixture
def class_payload(teacher):
    return {
        "periodo_letivo": "2026/2",
        "codigo_turma": "ESTCOMP01",
        "nivel_turma": 1,
        "id_curso": 1,
        "id_docente_responsavel": teacher["id_usuario"],
    }


@pytest.fixture
def created_class(client, teacher, class_payload):
    response = client.post("/api/v1/turmas", json=class_payload, headers=teacher["headers"])
    assert response.status_code == 201, response.json
    return response
