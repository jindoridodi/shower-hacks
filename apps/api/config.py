import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_DATABASE_FILENAME = "borrowed_intimacy.db"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def database_path_from_url(url: str, root: Path | None = None) -> Path:
    """Resolve a sqlite DATABASE_URL to a filesystem path.

    Relative paths are anchored at the repository root, not the process cwd.
    """
    if not url.startswith("sqlite:///"):
        raise ValueError("This slice only supports sqlite DATABASE_URL values")
    raw = url.removeprefix("sqlite:///")
    if raw == "":
        raise ValueError("DATABASE_URL is missing a database path")
    path = Path(raw)
    base = root or repo_root()
    if not path.is_absolute():
        path = base / path
    return Path(os.path.normpath(path))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(repo_root() / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./data/borrowed_intimacy.db"
    firecrawl_api_key: str = ""
    apify_api_token: str = ""
    apify_instagram_actor: str = "apify~instagram-profile-scraper"
    apify_instagram_timeout_seconds: int = 90
    instagram_use_fixtures: bool = False
    crawl_allowed_urls: str = ""
    crawl_terms_accepted_hosts: str = ""
    crawl_requests_per_minute: int = 10
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = ""
    llm_timeout_seconds: float = 30.0
    embeddings_enabled: bool = False
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_model_revision: str = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
    embedding_cache_dir: str | None = None
    embedding_batch_size: int = Field(default=16, ge=1, le=128)

    @property
    def database_path(self) -> Path:
        return database_path_from_url(self.database_url)

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.llm_model)


@lru_cache
def get_settings() -> Settings:
    return Settings()
