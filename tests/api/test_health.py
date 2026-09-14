from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app

client = TestClient(app)


class WorkingSession:
    def execute(self, statement: object) -> object:
        return object()


class FailingSession:
    def execute(self, statement: object) -> object:
        raise OperationalError("SELECT 1", {}, Exception("database unavailable"))


def test_healthz_reports_process_alive() -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_reports_database_ready() -> None:
    def override_get_db() -> Generator[Session, None, None]:
        yield WorkingSession()  # type: ignore[misc]

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/readyz")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_readyz_reports_database_unavailable() -> None:
    def override_get_db() -> Generator[Session, None, None]:
        yield FailingSession()  # type: ignore[misc]

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/readyz")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "unavailable"}
