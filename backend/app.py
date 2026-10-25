import time
from zoneinfo import ZoneInfo

from flask import Flask, g, jsonify, request
from sqlalchemy import event, text

from backend.config import configuration
from backend.db import db
from backend.errors import register_errors
from backend.security import limiter, register_jwt


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(configuration())
    if test_config:
        app.config.update(test_config)
    app.config["ACADEMIC_TIMEZONE"] = ZoneInfo("America/Manaus")
    database = app.config["SQLALCHEMY_DATABASE_URI"]
    secret = app.config["JWT_SECRET_KEY"]
    if not database:
        raise RuntimeError("Configure DATABASE_URL no arquivo .env.")
    if not isinstance(secret, str) or len(secret.encode()) < 32:
        raise RuntimeError("Configure JWT_SECRET_KEY com pelo menos 32 bytes aleatórios.")
    if not app.testing and not database.startswith("postgresql+psycopg://"):
        raise RuntimeError("O ambiente da aplicação exige PostgreSQL com o driver psycopg.")
    for key in (
        "SESSION_IDLE_MINUTES",
        "SESSION_MAX_HOURS",
        "RESET_CODE_MINUTES",
        "CLASS_CODE_DAYS",
    ):
        if app.config[key] <= 0:
            raise RuntimeError(f"{key} deve ser positivo.")
    if app.config["SESSION_IDLE_MINUTES"] > 20:
        raise RuntimeError("SESSION_IDLE_MINUTES deve ser no máximo 20, conforme RNF04.")
    if app.config["SMTP_SSL"] and app.config["SMTP_STARTTLS"]:
        raise RuntimeError("Escolha SMTP_SSL ou SMTP_STARTTLS.")
    if app.config["APP_ENV"] == "production":
        if app.config["RATELIMIT_STORAGE_URI"] == "memory://":
            raise RuntimeError("Configure armazenamento compartilhado do rate limiter em produção.")
        if not app.config["SMTP_SSL"] and not app.config["SMTP_STARTTLS"]:
            raise RuntimeError("SMTP deve utilizar TLS em produção.")
        if "*" in app.config["CORS_ORIGINS"] or any(
            not origin.startswith("https://") for origin in app.config["CORS_ORIGINS"]
        ):
            raise RuntimeError("CORS em produção exige origens HTTPS explícitas.")
    if database.startswith("postgresql"):
        options = dict(app.config["SQLALCHEMY_ENGINE_OPTIONS"])
        connect_args = dict(options.get("connect_args", {}))
        connect_args["options"] = (connect_args.get("options", "") + " -c timezone=UTC").strip()
        options["connect_args"] = connect_args
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = options
    db.init_app(app)
    register_errors(app)
    register_jwt(app)
    limiter.init_app(app)
    with app.app_context():
        if db.engine.dialect.name == "sqlite":

            @event.listens_for(db.engine, "connect")
            def enable_foreign_keys(connection, record):
                connection.execute("PRAGMA foreign_keys=ON")

    from backend.cli import register_cli
    from backend.routes import auth, catalogs, classes, enrollments, meetings, users, works

    for blueprint in (
        auth.bp,
        users.bp,
        classes.bp,
        catalogs.bp,
        enrollments.bp,
        works.bp,
        meetings.bp,
    ):
        app.register_blueprint(blueprint)
    register_cli(app)

    @app.cli.command("enviar-notificacoes-academicas")
    def academic_notifications():
        from backend.services.academic_mail import deliver

        deliver()

    @app.before_request
    def start_request():
        g.request_started = time.perf_counter()

    @app.after_request
    def response_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if app.config["APP_ENV"] == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Vary"] = "Origin"
        origin = request.headers.get("Origin")
        if origin and origin in app.config["CORS_ORIGINS"]:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = (
                "Authorization, Content-Type, If-Match"
            )
            response.headers["Access-Control-Expose-Headers"] = "ETag, Location, Retry-After"
        elapsed = (time.perf_counter() - g.get("request_started", time.perf_counter())) * 1000
        response.headers["Server-Timing"] = f"app;dur={elapsed:.2f}"
        return response

    @app.get("/api/v1/health/live")
    @limiter.exempt
    def live():
        return jsonify(status="ok")

    @app.get("/api/v1/health/ready")
    @limiter.exempt
    def ready():
        db.session.execute(text("SELECT 1"))
        # Readiness also checks the complementary migration, not only connectivity.
        db.session.execute(text("SELECT ativa_turma, data_atualizacao_turma FROM turma LIMIT 0"))
        db.session.execute(text("SELECT id_sessao FROM sessao_autenticacao LIMIT 0"))
        db.session.execute(text("SELECT id_recuperacao FROM recuperacao_senha LIMIT 0"))
        return jsonify(status="ok")

    @app.get("/api/v1/openapi.json")
    def openapi():
        return app.send_static_file("openapi.json")

    return app
