from scripts.check_env import check


def test_local_config_accepts_encoded_password_without_revealing_it():
    values = {
        "DATABASE_URL": "postgresql+psycopg://sigg:private%40password@localhost:5432/sigg_tcc",
        "JWT_SECRET_KEY": "a" * 64,
        "APP_ENV": "development",
    }
    assert check(values) == []
    values["DATABASE_URL"] = "postgresql+psycopg://sigg:private%40password@localhost:bad/sigg"
    issues = check(values)
    assert issues
    assert "private" not in " ".join(issues)
    assert values["DATABASE_URL"] not in " ".join(issues)


def test_template_values_are_rejected_without_displaying_credentials():
    issues = check(
        {
            "DATABASE_URL": "postgresql+psycopg://sigg_app:CHANGE_ME@localhost:5432/sigg_tcc",
            "JWT_SECRET_KEY": "",
        }
    )
    assert len(issues) == 2
    assert any("DATABASE_URL" in issue for issue in issues)
    assert any("JWT_SECRET_KEY" in issue for issue in issues)
    assert "CHANGE_ME" not in " ".join(issues)


def test_production_rejects_local_rate_limiting_and_http_origin():
    issues = check(
        {
            "DATABASE_URL": "postgresql+psycopg://sigg@localhost:5432/sigg_tcc",
            "JWT_SECRET_KEY": "b" * 64,
            "APP_ENV": "production",
            "RATELIMIT_STORAGE_URI": "memory://",
            "CORS_ORIGINS": "http://localhost:5173",
        }
    )
    assert len(issues) == 2
