"""Production configuration and deployment artifact tests."""

from pathlib import Path

import pytest

from apps.api.config import DEFAULT_DEV_SECRET, Settings

ROOT = Path(__file__).resolve().parents[1]


def test_production_rejects_sqlite_and_default_secret():
    settings = Settings(
        demo_mode=False,
        environment="production",
        database_url="sqlite:///./x.db",
        secret_key=DEFAULT_DEV_SECRET,
    )
    with pytest.raises(RuntimeError, match="Unsafe production configuration"):
        settings.validate_production_safety()


def test_production_accepts_postgres_and_custom_secret():
    settings = Settings(
        demo_mode=False,
        environment="production",
        database_url="postgresql://openworld:pw@localhost:5432/openworld",
        secret_key="a" * 32,
        cors_origins=["https://openworld-web.example.onrender.com"],
    )
    settings.validate_production_safety()


def test_production_rejects_wildcard_cors():
    settings = Settings(
        demo_mode=False,
        environment="production",
        database_url="postgresql://openworld:pw@localhost:5432/openworld",
        secret_key="a" * 32,
        cors_origins=["*"],
    )
    with pytest.raises(RuntimeError, match="Wildcard OPENWORLD_CORS_ORIGINS"):
        settings.validate_production_safety()


def test_production_rejects_default_localhost_cors():
    settings = Settings(
        demo_mode=False,
        environment="production",
        database_url="postgresql://openworld:pw@localhost:5432/openworld",
        secret_key="a" * 32,
    )
    with pytest.raises(RuntimeError, match="OPENWORLD_CORS_ORIGINS"):
        settings.validate_production_safety()


def test_platform_port_overrides_api_port(monkeypatch):
    monkeypatch.setenv("PORT", "10000")
    settings = Settings(api_port=8000)
    assert settings.api_port == 10000


def test_staging_rejects_demo_mode():
    settings = Settings(
        demo_mode=True,
        environment="staging",
        database_url="postgresql://openworld:pw@localhost:5432/openworld",
        secret_key="a" * 32,
    )
    with pytest.raises(RuntimeError, match="cannot run with OPENWORLD_DEMO_MODE"):
        settings.validate_production_safety()


def test_demo_mode_skips_production_safety():
    settings = Settings(demo_mode=True, secret_key=DEFAULT_DEV_SECRET)
    settings.validate_production_safety()


def test_prod_compose_does_not_embed_dev_secret():
    text = (ROOT / "docker-compose.prod.example.yml").read_text(encoding="utf-8")
    assert "dev-only-not-for-production" not in text
    assert "${OPENWORLD_SECRET_KEY}" in text
    assert "OPENWORLD_DEMO_MODE: \"false\"" in text


def test_api_dockerfile_is_non_root_and_secret_free():
    text = (ROOT / "docker/Dockerfile.api").read_text(encoding="utf-8")
    assert "USER appuser" in text
    assert "--reload" not in text
    assert "OPENWORLD_SECRET_KEY=" not in text
    assert "--port ${PORT:-8000}" in text


def test_render_blueprint_documents_services():
    text = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "openworld-api" in text
    assert "openworld-web" in text
    assert "python -m uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT" in text
    assert "npm ci && npm run build" in text
    assert "sync: false" in text
