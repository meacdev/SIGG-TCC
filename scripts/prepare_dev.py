"""Prepare the development database without exposing connection credentials."""

import ipaddress
import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.check_env import check  # noqa: E402


def prepare(values, runner=subprocess.run):
    issues = check(values)
    if issues:
        for issue in issues:
            print(f"PENDENTE — {issue}")
        return 1
    if values.get("APP_ENV", "development") != "development":
        print("Use APP_ENV=development para iniciar o servidor de desenvolvimento.")
        return 1
    url = make_url(values["DATABASE_URL"])
    host = url.host.lower().rstrip(".")
    try:
        local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = host == "localhost"
    # Alternate connection targets in URL parameters must be reviewed explicitly.
    automatic = (
        local and not url.query and str(values.get("AUTO_MIGRATE", "true")).lower() == "true"
    )
    if automatic:
        print("Aplicando migrações pendentes no PostgreSQL local...")
        args = ["-m", "flask", "--app", "backend.app:create_app", "db-upgrade"]
    else:
        print("Upgrade automático desativado ou banco remoto. Use yarn db:upgrade se necessário.")
        args = ["scripts/check_env.py", "--database"]
    try:
        result = runner(
            [sys.executable, *args],
            cwd=ROOT,
            env={**os.environ, **{k: str(v) for k, v in values.items() if v is not None}},
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
    except OSError, subprocess.TimeoutExpired:
        print("Não foi possível preparar o banco. Confira o PostgreSQL e execute yarn db:upgrade.")
        return 1
    if result.returncode:
        # Driver exceptions may contain credentials: keep captured output private.
        print(
            "Banco indisponível ou migração pendente/inválida. Confira o PostgreSQL, "
            "as permissões e a importação inicial do SQL base. "
            "Execute yarn db:upgrade para diagnosticar. Os servidores não foram iniciados."
        )
        return 1
    print("Banco preparado para desenvolvimento.")
    return 0


if __name__ == "__main__":
    raise SystemExit(prepare({**dotenv_values(ROOT / ".env"), **os.environ}))
