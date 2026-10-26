"""Disposable API for browser tests; never opens the configured application database."""

import secrets
import sys
from pathlib import Path

from flask import jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app import create_app  # noqa: E402
from backend.cli import seed_profiles  # noqa: E402
from backend.db import db  # noqa: E402
from backend.models import Curso  # noqa: E402

outbox = {}
app = create_app(
    {
        "TESTING": True,
        "APP_ENV": "testing",
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SQLALCHEMY_ENGINE_OPTIONS": {},
        "JWT_SECRET_KEY": secrets.token_hex(32),
        "RATELIMIT_ENABLED": False,
        "CORS_ORIGINS": [],
        "SMTP_HOST": "",
        "SMTP_FROM": "",
        "MAIL_SENDER": lambda address, subject, content: outbox.update({address: content}),
    }
)


@app.get("/__test__/mail")
def test_mail():
    # Only this disposable test server exposes captured mail, never the application factory.
    return jsonify(content=outbox.get(request.args.get("email"), ""))


with app.app_context():
    db.create_all()
    seed_profiles()
    db.session.add(Curso(codigo_curso="SI", nome_curso="Sistemas de Informação"))
    db.session.commit()

if __name__ == "__main__":
    # A single worker keeps the same in-memory database throughout the test run.
    from waitress import serve

    serve(app, host="127.0.0.1", port=5001, threads=1)
