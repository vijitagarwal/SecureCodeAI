from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://securecode:securecode@localhost:5432/securecode"
    cors_origins: str = "http://localhost:3000"
    max_upload_size_bytes: int = Field(default=5 * 1024 * 1024, gt=0)
    upload_dir: str = str(Path(__file__).resolve().parents[2] / ".data" / "uploads")
    scanner_timeout_seconds: int = Field(default=30, gt=0)
    ai_provider: Literal["mock", "gemini"] = "mock"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = Field(default="gemini-2.5-flash", pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}$")
    ai_timeout_seconds: int = Field(default=20, ge=1, le=60)
    api_key: SecretStr | None = Field(default=None, min_length=32)
    max_concurrent_scans: int = Field(default=2, ge=1, le=8)
    max_concurrent_analyses: int = Field(default=2, ge=1, le=8)
    max_scanner_output_bytes: int = Field(default=16 * 1024 * 1024, gt=0)
    max_findings: int = Field(default=5000, ge=1, le=10000)

    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parents[2] / ".env", Path(__file__).resolve().parents[3] / ".env"),
        env_ignore_empty=True,
        hide_input_in_errors=True,
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator("ai_provider", mode="before")
    @classmethod
    def normalize_ai_provider(cls, value: object) -> object:
        return str(value).strip().lower()

    @model_validator(mode="after")
    def validate_ai_configuration(self) -> "Settings":
        if self.ai_provider == "gemini" and self.gemini_api_key is None:
            raise ValueError("GEMINI_API_KEY is required when AI_PROVIDER=gemini.")
        return self


settings = Settings()
