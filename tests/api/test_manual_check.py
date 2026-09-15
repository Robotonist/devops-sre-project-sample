from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.worker.dispatch import QueueUnavailableError


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        def override_get_db() -> Generator[Session, None, None]:
            yield session

        app.dependency_overrides[get_db] = override_get_db
        try:
            yield TestClient(app)
        finally:
            app.dependency_overrides.clear()


def _create_target(client: TestClient) -> str:
    response = client.post(
        "/api/v1/targets",
        json={
            "name": "Manual Target",
            "url": "http://service.test/health",
            "interval_seconds": 60,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_manual_check_enqueues_target(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    target_id = _create_target(client)
    monkeypatch.setattr("app.api.targets.enqueue_target_check", lambda target_id: "task-123")

    response = client.post(f"/api/v1/targets/{target_id}/check")

    assert response.status_code == 202
    assert response.json() == {"task_id": "task-123"}


def test_manual_check_returns_404_for_unknown_target(client: TestClient) -> None:
    response = client.post(
        "/api/v1/targets/00000000-0000-0000-0000-000000000001/check"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Target not found"}


def test_manual_check_returns_503_when_queue_is_unavailable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_id = _create_target(client)

    def unavailable(target_id: object) -> str:
        raise QueueUnavailableError("queue unavailable")

    monkeypatch.setattr("app.api.targets.enqueue_target_check", unavailable)

    response = client.post(f"/api/v1/targets/{target_id}/check")

    assert response.status_code == 503
    assert response.json() == {"detail": "Check queue unavailable"}
