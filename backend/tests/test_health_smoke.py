"""End-to-end smoke test proving the scaffold works: app boots, hits the
test database, and the ORM/session fixtures are wired up correctly."""

from app.models import Job


def test_health_check_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_database_fixture_is_isolated(db_session):
    assert db_session.query(Job).count() == 0

    db_session.add(
        Job(
            company="Acme",
            title="Junior Engineer",
            location="Remote",
            url="https://example.com/jobs/1",
            source="test",
        )
    )
    db_session.commit()

    assert db_session.query(Job).count() == 1
