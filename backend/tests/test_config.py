import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


def test_remote_provider_requires_a_key_at_startup():
    with pytest.raises(ValidationError, match="GEMINI_API_KEY"):
        Settings(_env_file=None, ai_provider="gemini")


def test_provider_name_is_normalized():
    settings = Settings(_env_file=None, ai_provider=" GEMINI ", gemini_api_key=SecretStr("test-key"))

    assert settings.ai_provider == "gemini"


def test_unknown_provider_is_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ai_provider="unknown")


def test_wildcard_cors_is_rejected():
    with pytest.raises(ValidationError, match="explicit origins"):
        Settings(_env_file=None, cors_origins="*")
