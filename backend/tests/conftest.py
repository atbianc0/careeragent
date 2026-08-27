"""Shared pytest fixtures for the backend test suite.

Uses a host-mode SQLite file as the test database, per the pattern the
README already documents for local non-Docker dev ("Host-mode SQLite is
useful for smoke tests, but PostgreSQL in Docker is the normal app
database"). None of the rule-based services under test (parsing, scoring,
verification, discovery dedup/filtering) depend on Postgres-specific
behavior, so SQLite keeps the suite fast and runnable with no Docker/DB
container required. The env vars below are set before any `app.*` import
so `Settings` picks them up at construction time, and they are forced
(not `setdefault`) so a developer's real local `.env` can never point the
suite at real dev data.
"""

import os
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
TEST_DB_PATH = TESTS_DIR / ".tmp" / "test.sqlite3"
TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
TEST_DB_PATH.unlink(missing_ok=True)

os.environ["LOCAL_DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["ENABLE_SAMPLE_JOBS"] = "false"
os.environ["AI_PROVIDER"] = "mock"
os.environ["AI_ALLOW_EXTERNAL_CALLS"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.database import Base, SessionLocal, engine, init_db  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    init_db()
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
