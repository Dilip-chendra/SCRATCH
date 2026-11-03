import pytest
from pydantic import ValidationError
from app.core.config import Settings


def test_valid_development_settings():
    """Verify that development settings load cleanly with valid defaults."""
    cfg = Settings(
        ENVIRONMENT="development",
        SECRET_KEY="short_dev_key",
        DATABASE_URL="sqlite+aiosqlite:///:memory:"
    )
    assert cfg.ENVIRONMENT == "development"
    assert cfg.ACCESS_TOKEN_EXPIRE_MINUTES == 15
    assert cfg.COOKIE_SECURE is False


def test_production_rejects_insecure_default_secret_key():
    """Verify that production mode strictly rejects default or insecure secret keys."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="change_me_to_a_secure_random_32_character_string",
            DATABASE_URL="sqlite+aiosqlite:///:memory:"
        )
    assert "SECRET_KEY must be a secure, non-default string" in str(exc_info.value)


def test_production_rejects_short_secret_key():
    """Verify that production mode rejects secret keys under 32 characters."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="too_short_key_12345",
            DATABASE_URL="sqlite+aiosqlite:///:memory:"
        )
    assert "SECRET_KEY must be a secure, non-default string" in str(exc_info.value)


def test_production_accepts_valid_strong_secret():
    """Verify that production mode accepts a strong 32+ character key."""
    strong_key = "a" * 32
    cfg = Settings(
        ENVIRONMENT="production",
        SECRET_KEY=strong_key,
        DATABASE_URL="sqlite+aiosqlite:///:memory:"
    )
    assert cfg.SECRET_KEY == strong_key


def test_cors_origins_parsing():
    """Verify CORS origins parses stringified JSON arrays."""
    cfg = Settings(
        BACKEND_CORS_ORIGINS='["https://app.scratch.io", "https://staging.scratch.io"]'
    )
    assert "https://app.scratch.io" in cfg.BACKEND_CORS_ORIGINS
    assert "https://staging.scratch.io" in cfg.BACKEND_CORS_ORIGINS
