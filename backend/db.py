from datetime import UTC, datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import BigInteger, Integer
from sqlalchemy.types import DateTime, TypeDecorator


def utcnow():
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    """Normalize both the exported TIMESTAMP and dictionary TIMESTAMPTZ to UTC."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return value.astimezone(UTC) if value is not None else None

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


db = SQLAlchemy(session_options={"expire_on_commit": False})
ID = BigInteger().with_variant(Integer, "sqlite")
