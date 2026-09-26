<<<<<<< HEAD
import os
from functools import lru_cache
from pathlib import Path

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

    @property
    def database_path(self) -> Path:
        return database_path_from_url(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
=======
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    llm_timeout_seconds: float

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.llm_model)


def get_settings() -> Settings:
    timeout = os.getenv("LLM_TIMEOUT_SECONDS", "30")
    try:
        timeout_seconds = float(timeout)
    except ValueError as error:
        raise ValueError("LLM_TIMEOUT_SECONDS must be a number.") from error

    return Settings(
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/"),
        llm_model=os.getenv("LLM_MODEL", "").strip(),
        llm_timeout_seconds=timeout_seconds,
    )
>>>>>>> 6308a7a (feat: add LLM API integration)
