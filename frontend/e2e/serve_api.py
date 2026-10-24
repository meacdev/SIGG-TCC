"""Disposable API for browser tests; never opens the configured application database."""

import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app import create_app  # noqa: E402
from backend.cli import seed_profiles  # noqa: E402
from backend.db import db  # noqa: E402
from backend.models import Curso  # noqa: E402

app = create_app(
    {
        "TESTING": True,
        "APP_ENV": "testing",
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SQLALCHEMY_ENGINE_OPTIONS": {},
        "JWT_SECRET_KEY": secrets.token_hex(32),
        "RATELIMIT_ENABLED": False,
        "CORS_ORIGINS": [],
    }
)
with app.app_context():
    db.create_all()
    seed_profiles()
    db.session.add(Curso(codigo_curso="SI", nome_curso="Sistemas de Informação"))
    db.session.commit()

if __name__ == "__main__":
    # A single worker keeps the same in-memory database throughout the test run.
    from waitress import serve

    serve(app, host="127.0.0.1", port=5001, threads=1)
