"""Check local configuration without displaying credentials or changing the database."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def check(values):
    issues = []
    address = values.get("DATABASE_URL") or ""
    if not address:
        issues.append("DATABASE_URL: informe a conexão do PostgreSQL no .env da raiz.")
    else:
        try:
            url = make_url(address)
            if url.drivername not in {"postgresql", "postgresql+psycopg"}:
                issues.append("DATABASE_URL: utilize postgresql+psycopg://.")
            if not url.database or not url.username or not url.host:
                issues.append("DATABASE_URL: informe usuário, servidor e nome do banco.")
            if url.password and any(
                marker in url.password.upper()
                for marker in ("CHANGE_ME", "SUA_SENHA", "SUBSTITUA", "COLE_AQUI")
            ):
                issues.append(
                    "DATABASE_URL: substitua a senha de exemplo pela senha do PostgreSQL."
                )
            # Validate a textual port without ever displaying the URL.
            _ = url.port
        except Exception:
            issues.append(
                "DATABASE_URL: formato inválido; codifique caracteres especiais da senha."
            )
    secret = values.get("JWT_SECRET_KEY") or ""
    if len(secret.encode()) < 32 or any(
        marker in secret.upper() for marker in ("CHANGE_ME", "COLE_AQUI", "SUBSTITUA")
    ):
        issues.append("JWT_SECRET_KEY: gere uma chave com yarn env:key e cole no .env.")
    if values.get("APP_ENV") == "production":
        if (values.get("RATELIMIT_STORAGE_URI") or "memory://") == "memory://":
            issues.append("RATELIMIT_STORAGE_URI: configure Redis para produção.")
        origins = (values.get("CORS_ORIGINS") or "").split(",")
        if any(origin.strip() and not origin.strip().startswith("https://") for origin in origins):
            issues.append("CORS_ORIGINS: utilize somente as origens HTTPS da aplicação.")
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", action="store_true")
    args = parser.parse_args()
    values = {**dotenv_values(ROOT / ".env"), **os.environ}
    issues = check(values)
    for issue in issues:
        print(f"PENDENTE — {issue}")
    if issues:
        return 1
    print("Configuração básica preenchida. Nenhuma senha ou chave foi exibida.")
    if not args.database:
        print("Para testar a conexão e as tabelas, execute yarn db:check.")
        return 0
    from backend.app import create_app

    try:
        app = create_app()
        response = app.test_client().get("/api/v1/health/ready")
        if response.status_code != 200:
            raise RuntimeError
    except Exception:
        print(
            "Banco indisponível ou estrutura incompleta. Confira o serviço PostgreSQL, "
            "as credenciais, a importação do SQL base e yarn db:upgrade."
        )
        return 1
    print("Banco conectado e estrutura complementar disponível.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
