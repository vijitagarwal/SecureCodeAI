import tempfile

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://securecode:securecode@localhost:5432/securecode"
    cors_origins: str = "http://localhost:3000"
    max_upload_size_bytes: int = 5 * 1024 * 1024
    upload_dir: str = f"{tempfile.gettempdir()}\\securecode-ai"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
