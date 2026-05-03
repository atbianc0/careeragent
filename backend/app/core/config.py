import os
from functools import lru_cache
from pathlib import Path


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / "data").exists():
            return candidate
    return current.parents[2]


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
            "postgresql+psycopg2://careeragent:careeragent@db:5432/careeragent",
        )
        self.backend_port = int(os.getenv("BACKEND_PORT", "8000"))
        self.frontend_port = int(os.getenv("FRONTEND_PORT", "3000"))

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
