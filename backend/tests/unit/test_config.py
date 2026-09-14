from app.core.config import Settings


def test_settings_default_values():
    settings = Settings()
    assert settings.PROJECT_NAME == "FLUX ONE API"
    assert settings.VERSION == "0.1.0"
    assert settings.ALGORITHM == "HS256"
    assert "postgresql+asyncpg" in settings.DATABASE_URL
    assert settings.DB_POOL_SIZE >= 5


def test_settings_env_override():
    custom_settings = Settings(PROJECT_NAME="FLUX ONE TEST", DEBUG=False)
    assert custom_settings.PROJECT_NAME == "FLUX ONE TEST"
    assert custom_settings.DEBUG is False
