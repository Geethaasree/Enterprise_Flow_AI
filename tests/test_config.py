"""Configuration loading tests."""

from app.config import Settings, get_settings


def test_settings_defaults(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    get_settings.cache_clear()
    s = Settings(
        _env_file=None,
        DATABASE_URL="postgresql+psycopg://u:p@localhost:5432/db",
        REDIS_URL="redis://localhost:6379/0",
    )
    assert s.app_name
    assert "postgresql" in s.database_url
    assert s.redis_url.startswith("redis://")
    get_settings.cache_clear()


def test_get_settings_cached(monkeypatch):
    monkeypatch.setenv("APP_NAME", "EF-Test")
    get_settings.cache_clear()
    a = get_settings()
    b = get_settings()
    assert a is b
    assert a.app_name == "EF-Test"
    get_settings.cache_clear()
