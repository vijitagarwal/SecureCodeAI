import tempfile

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://securecode:securecode@localhost:5432/securecode"
    cors_origins: str = "http://localhost:3000"
    max_upload_size_bytes: int = Field(default=5 * 1024 * 1024, gt=0)
    upload_dir: str = f"{tempfile.gettempdir()}\\securecode-ai"
    scanner_timeout_seconds: int = Field(default=30, gt=0)

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
