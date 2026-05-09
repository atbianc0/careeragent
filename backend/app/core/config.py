import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / "docker-compose.yml").exists() and (candidate / "data").exists():
            return candidate
    for candidate in current.parents:
        if (candidate / "data").exists():
            return candidate
    return current.parents[2]


def _running_in_docker() -> bool:
    return Path("/.dockerenv").exists()


def _default_database_url() -> str:
    host = "db" if _running_in_docker() else "localhost"
    return f"postgresql+psycopg2://careeragent:careeragent@{host}:5432/careeragent"


def _database_host_hint(database_url: str) -> str:
    try:
        parsed = urlparse(database_url)
    except Exception:
        return "unknown"
    return parsed.hostname or "unknown"


class Settings:
    def __init__(self) -> None:
        self.project_root = _find_project_root()
        self.data_dir = Path(os.getenv("CAREERAGENT_DATA_DIR", self.project_root / "data"))
        self.outputs_dir = Path(os.getenv("CAREERAGENT_OUTPUTS_DIR", self.project_root / "outputs"))
        self.postgres_user = os.getenv("POSTGRES_USER", "careeragent")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "careeragent")
        self.postgres_db = os.getenv("POSTGRES_DB", "careeragent")
        self.postgres_host = os.getenv("POSTGRES_HOST", "db")
        self.postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.database_url = os.getenv(
            "DATABASE_URL",
            _default_database_url(),
        )
        self.backend_runtime = "docker" if _running_in_docker() else "local"
        self.database_host_hint = _database_host_hint(self.database_url)
        self.backend_port = int(os.getenv("BACKEND_PORT", "8000"))
        self.frontend_port = int(os.getenv("FRONTEND_PORT", "3000"))
        self.enable_sample_jobs = _parse_bool(os.getenv("ENABLE_SAMPLE_JOBS"), default=False)
        self.ai_provider = (os.getenv("AI_PROVIDER", "mock") or "mock").strip().lower()
        self.openai_api_key = (os.getenv("OPENAI_API_KEY", "") or "").strip()
        self.openai_model = (os.getenv("OPENAI_MODEL", "") or "").strip() or "gpt-4.1-mini"
        self.autofill_navigation_timeout_ms = int(os.getenv("CAREERAGENT_AUTOFILL_NAVIGATION_TIMEOUT_MS", "30000"))
        self.autofill_review_timeout_seconds = int(os.getenv("CAREERAGENT_AUTOFILL_REVIEW_TIMEOUT_SECONDS", "90"))
        self.playwright_headless = _parse_bool(os.getenv("PLAYWRIGHT_HEADLESS"), default=True)
        self.playwright_use_xvfb = _parse_bool(os.getenv("PLAYWRIGHT_USE_XVFB"), default=False)
        self.playwright_slow_mo_ms = int(
            os.getenv("PLAYWRIGHT_SLOW_MO_MS", os.getenv("CAREERAGENT_AUTOFILL_SLOW_MO_MS", "0"))
        )
        self.playwright_keep_open_seconds = int(os.getenv("PLAYWRIGHT_KEEP_OPEN_SECONDS", "900"))
        self.autofill_slow_mo_ms = self.playwright_slow_mo_ms

    @property
    def cors_origins(self) -> list[str]:
        return [
            f"http://localhost:{self.frontend_port}",
            f"http://127.0.0.1:{self.frontend_port}",
        ]

    @property
    def profile_path(self) -> Path:
        return self.data_dir / "profile.yaml"

    @property
    def profile_example_path(self) -> Path:
        return self.data_dir / "profile.example.yaml"

    @property
    def resume_path(self) -> Path:
        return self.data_dir / "resume" / "base_resume.tex"

    @property
    def resume_example_path(self) -> Path:
        return self.data_dir / "resume" / "base_resume.example.tex"

    @property
    def application_packets_dir(self) -> Path:
        return self.outputs_dir / "application_packets"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
