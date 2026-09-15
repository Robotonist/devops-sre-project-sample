from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


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


def target_payload(name: str = "Local API") -> dict[str, object]:
    return {
        "name": name,
        "url": "http://api:8000/healthz",
        "interval_seconds": 60,
        "expected_status": 200,
        "tls_warning_days": 30,
    }


def test_create_and_get_target(client: TestClient) -> None:
    created = client.post("/api/v1/targets", json=target_payload())

    assert created.status_code == 201
    target_id = created.json()["id"]

    fetched = client.get(f"/api/v1/targets/{target_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Local API"
    assert fetched.json()["enabled"] is True


def test_list_targets_returns_created_targets(client: TestClient) -> None:
    assert client.post("/api/v1/targets", json=target_payload("API One")).status_code == 201
    assert client.post("/api/v1/targets", json=target_payload("API Two")).status_code == 201

    response = client.get("/api/v1/targets")

    assert response.status_code == 200
    assert [target["name"] for target in response.json()] == ["API One", "API Two"]


def test_duplicate_target_name_returns_409(client: TestClient) -> None:
    payload = target_payload("Duplicate")

    assert client.post("/api/v1/targets", json=payload).status_code == 201
    response = client.post("/api/v1/targets", json=payload)

    assert response.status_code == 409
    assert response.json() == {"detail": "A target with that name already exists"}


def test_interval_below_ten_seconds_returns_422(client: TestClient) -> None:
    payload = target_payload()
    payload["interval_seconds"] = 9

    response = client.post("/api/v1/targets", json=payload)

    assert response.status_code == 422


def test_unknown_target_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/targets/00000000-0000-0000-0000-000000000001")

    assert response.status_code == 404
    assert response.json() == {"detail": "Target not found"}


def test_new_target_has_empty_check_history(client: TestClient) -> None:
    created = client.post("/api/v1/targets", json=target_payload())
    target_id = created.json()["id"]

    response = client.get(f"/api/v1/targets/{target_id}/checks")

    assert response.status_code == 200
    assert response.json() == []


class UnavailableSession:
    def scalars(self, statement: object) -> object:
        from sqlalchemy.exc import OperationalError

        raise OperationalError("SELECT targets", {}, Exception("database unavailable"))


def test_database_unavailable_returns_503() -> None:
    def override_get_db() -> Generator[Session, None, None]:
        yield UnavailableSession()  # type: ignore[misc]

    app.dependency_overrides[get_db] = override_get_db
    try:
        unavailable_client = TestClient(app, raise_server_exceptions=False)
        response = unavailable_client.get("/api/v1/targets")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
