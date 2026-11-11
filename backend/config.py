import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def configuration():
    load_dotenv(ROOT / ".env", override=False)
    database = os.getenv("DATABASE_URL", "")
    if database.startswith("postgresql://"):
        database = database.replace("postgresql://", "postgresql+psycopg://", 1)
    return {
        "APP_ENV": os.getenv("APP_ENV", "development"),
        "FRONTEND_URL": os.getenv("FRONTEND_URL", "http://127.0.0.1:5173"),
        "SQLALCHEMY_DATABASE_URI": database,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True},
        "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", ""),
        "JWT_TOKEN_LOCATION": ["headers"],
        "JWT_ACCESS_TOKEN_EXPIRES": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "20"))),
        "JWT_REFRESH_TOKEN_EXPIRES": timedelta(hours=int(os.getenv("SESSION_MAX_HOURS", "12"))),
        "SESSION_IDLE_MINUTES": int(os.getenv("SESSION_IDLE_MINUTES", "20")),
        "SESSION_MAX_HOURS": int(os.getenv("SESSION_MAX_HOURS", "12")),
        "RESET_CODE_MINUTES": int(os.getenv("RESET_CODE_MINUTES", "10")),
        "CLASS_CODE_DAYS": int(os.getenv("CLASS_CODE_DAYS", "30")),
        "CORS_ORIGINS": [x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()],
        "RATELIMIT_STORAGE_URI": os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
        "RATELIMIT_HEADERS_ENABLED": True,
        "MAX_CONTENT_LENGTH": 64 * 1024,
        "SMTP_HOST": os.getenv("SMTP_HOST", ""),
        "SMTP_PORT": int(os.getenv("SMTP_PORT", "587")),
        "SMTP_USERNAME": os.getenv("SMTP_USERNAME", ""),
        "SMTP_PASSWORD": os.getenv("SMTP_PASSWORD", ""),
        "SMTP_FROM": os.getenv("SMTP_FROM", ""),
        "SMTP_STARTTLS": os.getenv("SMTP_STARTTLS", "true").lower() == "true",
        "SMTP_SSL": os.getenv("SMTP_SSL", "false").lower() == "true",
    }
