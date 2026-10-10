from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://securecode:securecode@localhost:5432/securecode"
    cors_origins: str = "http://localhost:3000"
    max_upload_size_bytes: int = Field(default=5 * 1024 * 1024, gt=0)
    upload_dir: str = str(Path(__file__).resolve().parents[2] / ".data" / "uploads")
    scanner_timeout_seconds: int = Field(default=30, gt=0)
    ai_provider: str = "mock"
    api_key: SecretStr | None = Field(default=None, min_length=32)
    max_concurrent_scans: int = Field(default=2, ge=1, le=8)
    max_scanner_output_bytes: int = Field(default=16 * 1024 * 1024, gt=0)
    max_findings: int = Field(default=5000, ge=1, le=10000)

    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parents[2] / ".env", Path(__file__).resolve().parents[3] / ".env"),
        env_ignore_empty=True,
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
