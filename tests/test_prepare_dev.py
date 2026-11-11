import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts.prepare_dev import prepare


def config(host="localhost"):
    return {
        "DATABASE_URL": f"postgresql+psycopg://dev:private-password@{host}/sigg",
        "JWT_SECRET_KEY": "a" * 64,
        "APP_ENV": "development",
    }


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "[::1]"])
def test_local_development_applies_migrations(host):
    runner = Mock(return_value=SimpleNamespace(returncode=0))
    assert prepare(config(host), runner) == 0
    assert runner.call_args.args[0][-1] == "db-upgrade"


@pytest.mark.parametrize("mode", ["remote", "disabled", "query"])
def test_other_connections_only_check_readiness(mode):
    values = config("db.example.org" if mode == "remote" else "localhost")
    if mode == "disabled":
        values["AUTO_MIGRATE"] = "false"
    if mode == "query":
        values["DATABASE_URL"] += "?host=db.example.org"
    runner = Mock(return_value=SimpleNamespace(returncode=0))
    assert prepare(values, runner) == 0
    assert runner.call_args.args[0][-1] == "--database"


@pytest.mark.parametrize("mode", ["production", "invalid"])
def test_invalid_configuration_never_runs_database_commands(mode):
    values = config()
    values["APP_ENV" if mode == "production" else "JWT_SECRET_KEY"] = (
        "production" if mode == "production" else ""
    )
    runner = Mock()
    assert prepare(values, runner) == 1
    runner.assert_not_called()


def test_database_failure_stops_startup_without_exposing_credentials(capsys):
    runner = Mock(return_value=SimpleNamespace(returncode=1, stderr="private-password"))
    assert prepare(config(), runner) == 1
    assert "private-password" not in capsys.readouterr().out


def test_timeout_stops_startup(capsys):
    runner = Mock(side_effect=subprocess.TimeoutExpired("private-password", 120))
    assert prepare(config(), runner) == 1
    assert "private-password" not in capsys.readouterr().out
