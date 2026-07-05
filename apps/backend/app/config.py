"""Application settings loaded from environment variables.

Purpose: Centralizes configuration (database URL, CORS, upload directory, size limits).
Interactions: Reads apps/backend/.env and repo-root .env. Consumed by main.py,
database.py, and document_storage.py. Values are documented in .env.example files.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    cors_origins: str = "http://localhost:3000"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    upload_dir: str = "uploads"
    max_upload_mb: int = 50

    embedding_provider: str = "gemini"
    embedding_model: str = "gemini-embedding-2"
    embedding_dimensions: int = 768
    gemini_api_key: str = ""
    embedding_batch_size: int = 4
    embedding_request_token_budget: int = 6000
    embedding_tokens_per_minute: int = 25000
    search_default_top_k: int = 8
    search_max_top_k: int = 10

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        if not path.is_absolute():
            path = ROOT_DIR / path
        return path

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL is required. Set it in apps/backend/.env with no syntax errors. "
                "See docs/SUPABASE_SETUP.md."
            )

        url = self.database_url.strip().strip('"').strip("'")

        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)

        if "supabase.co" in url and "sslmode=" not in url:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}sslmode=require"

        return url


settings = Settings()
