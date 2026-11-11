import secrets
import smtplib
from datetime import timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app import create_app
from backend.db import db, utcnow
from backend.models import Auditoria, Perfil, UsuarioPerfil
from backend.security import limiter
from backend.services.mail import send_reset_email


def test_health_cors_http_errors_and_json_contract(app, client):
    assert client.get("/api/v1/health/live").json == {"status": "ok"}
    assert client.get("/api/v1/health/ready").status_code == 200
    response = client.options("/api/v1/usuarios", headers={"Origin": "http://localhost:5173"})
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert "ETag" in response.headers["Access-Control-Expose-Headers"]
    assert (
        client.options("/api/v1/usuarios", headers={"Origin": "https://evil.example"}).headers.get(
            "Access-Control-Allow-Origin"
        )
        is None
    )
    assert client.get("/missing").status_code == 404
    assert client.put("/api/v1/usuarios").status_code == 405
    assert client.post("/api/v1/usuarios", data="text").status_code == 415
    assert (
        client.post("/api/v1/usuarios", data="{bad", content_type="application/json").status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/usuarios", data="x" * 70000, content_type="application/json"
        ).status_code
        == 413
    )
    assert client.get("/api/v1/cursos").json["meta"]["total"] == 2


def test_rate_limit(app, client):
    limited_app = create_app(dict(app.config) | {"RATELIMIT_ENABLED": True})
    client = limited_app.test_client()
    with limited_app.app_context():
        limiter.reset()
        limiter.enabled = True
    try:
        for _ in range(10):
            assert client.post("/api/v1/auth/login", json={}).status_code == 422
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 429
        assert response.json["error"]["code"] == "HTTP_429"
        assert "Retry-After" in response.headers
    finally:
        limiter.enabled = False


@pytest.mark.parametrize(
    "overrides",
    [
        {"SQLALCHEMY_DATABASE_URI": ""},
        {"JWT_SECRET_KEY": ""},
        {"TESTING": False, "SQLALCHEMY_DATABASE_URI": "sqlite://"},
        {"SESSION_IDLE_MINUTES": 21},
        {"SESSION_MAX_HOURS": 0},
        {"SMTP_SSL": True, "SMTP_STARTTLS": True},
        {"APP_ENV": "production", "RATELIMIT_STORAGE_URI": "memory://"},
        {
            "APP_ENV": "production",
            "RATELIMIT_STORAGE_URI": "redis://localhost",
            "SMTP_SSL": False,
            "SMTP_STARTTLS": False,
        },
        {
            "APP_ENV": "production",
            "RATELIMIT_STORAGE_URI": "redis://localhost",
            "SMTP_SSL": False,
            "SMTP_STARTTLS": True,
            "CORS_ORIGINS": ["*"],
        },
    ],
)
def test_configuration_fails_closed(overrides):
    config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "JWT_SECRET_KEY": secrets.token_hex(32),
        "APP_ENV": "testing",
    }
    with pytest.raises(RuntimeError):
        create_app(config | overrides)


def test_admin_cli_seed_courses_periods_grant_revoke(app, signup, client, login):
    runner = app.test_cli_runner()
    for _ in range(2):
        assert runner.invoke(args=["seed-perfis"]).exit_code == 0
    result = runner.invoke(args=["criar-curso", "--codigo", "ENG", "--nome", "Engenharia"])
    assert result.exit_code == 0, result.exception
    assert (
        runner.invoke(args=["criar-curso", "--codigo", "ENG", "--nome", "Engenharia"]).exit_code
        == 1
    )
    assert runner.invoke(args=["criar-periodo", "2027/1"]).exit_code == 0
    user = signup()
    args = [
        "conceder-perfil",
        "--email",
        user["email_usuario"],
        "--perfil",
        "professor_disciplina",
        "--id-curso",
        "1",
        "--justificativa",
        "Designação de docente",
    ]
    assert runner.invoke(args=args).exit_code == 0
    future = (utcnow() + timedelta(days=10)).isoformat()
    assert runner.invoke(args=args + ["--expira-em", future]).exit_code == 0
    assert runner.invoke(args=args + ["--expira-em", "invalid"]).exit_code == 1
    assert runner.invoke(args=args + ["--revogar"]).exit_code == 0
    with app.app_context():
        profile = db.session.scalar(
            select(Perfil).where(Perfil.codigo_perfil == "professor_disciplina")
        )
        association = db.session.get(UsuarioPerfil, (user["id_usuario"], profile.id_perfil))
        assert association.data_expiracao_usuario_perfil <= utcnow()
    assert (
        runner.invoke(
            args=[
                "conceder-perfil",
                "--email",
                user["email_usuario"],
                "--perfil",
                "aluno",
                "--justificativa",
                "Teste",
            ]
        ).exit_code
        == 1
    )
    assert (
        runner.invoke(
            args=[
                "conceder-perfil",
                "--email",
                "missing@example.com",
                "--perfil",
                "orientador",
                "--justificativa",
                "Teste",
            ]
        ).exit_code
        == 1
    )
    assert (
        runner.invoke(
            args=[
                "conceder-perfil",
                "--email",
                user["email_usuario"],
                "--perfil",
                "coordenador",
                "--justificativa",
                "Teste",
            ]
        ).exit_code
        == 1
    )


def test_mail_tls_and_failure(app, monkeypatch):
    sent = []

    class SMTP:
        def __init__(self, *args, **kwargs):
            sent.append("connect")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self, **kwargs):
            sent.append("tls")

        def login(self, *args):
            sent.append("login")

        def send_message(self, message):
            sent.append(message)

    monkeypatch.setattr(smtplib, "SMTP", SMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", SMTP)
    with app.app_context():
        app.config.update(
            MAIL_SENDER=None,
            SMTP_HOST="smtp.example.com",
            SMTP_FROM="sigg@example.com",
            SMTP_USERNAME="sigg",
            SMTP_PASSWORD=secrets.token_urlsafe(18),
        )
        send_reset_email("user@example.com", "1234567890")
        assert sent[1:3] == ["tls", "login"]
        app.config.update(SMTP_SSL=True, SMTP_STARTTLS=False)
        send_reset_email("user@example.com", "1234567890")
        monkeypatch.setattr(SMTP, "send_message", lambda *args: (_ for _ in ()).throw(OSError()))
        from backend.errors import APIError

        with pytest.raises(APIError):
            send_reset_email("user@example.com", "1234567890")


def test_database_and_unexpected_errors_hide_details(app, client, monkeypatch):
    def broken(*args, **kwargs):
        raise SQLAlchemyError("private connection details")

    monkeypatch.setattr(db.session, "execute", broken)
    result = client.get("/api/v1/health/ready")
    assert result.status_code == 503
    assert "private" not in result.get_data(as_text=True)
    monkeypatch.setattr(db.session, "execute", lambda *args, **kwargs: 1 / 0)
    assert client.get("/api/v1/health/ready").status_code == 500


def test_postgres_migration_idempotent_and_audit_immutable(app, signup):
    with app.app_context():
        if db.engine.dialect.name != "postgresql":
            pytest.skip("PostgreSQL triggers require TEST_DATABASE_URL")
    signup()
    assert app.test_cli_runner().invoke(args=["db-upgrade"]).exit_code == 0
    with app.app_context():
        assert db.session.scalar(select(Auditoria.id_auditoria))
        for statement in (
            "UPDATE auditoria SET acao_auditoria='alterada'",
            "DELETE FROM auditoria",
            "TRUNCATE auditoria_alteracao",
        ):
            with pytest.raises(SQLAlchemyError):
                db.session.execute(text(statement))
            db.session.rollback()
