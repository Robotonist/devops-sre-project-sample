import os
import time
from uuid import uuid4

import httpx
import pytest

SMOKE_BASE_URL = os.getenv("SMOKE_BASE_URL")
pytestmark = pytest.mark.skipif(
    not SMOKE_BASE_URL,
    reason="set SMOKE_BASE_URL to run the live Compose smoke test",
)


def test_internal_health_target_end_to_end() -> None:
    assert SMOKE_BASE_URL is not None

    with httpx.Client(base_url=SMOKE_BASE_URL, timeout=5.0) as client:
        created = client.post(
            "/api/v1/targets",
            json={
                "name": f"smoke-self-health-{uuid4()}",
                "url": "http://api:8000/healthz",
                "interval_seconds": 3600,
                "expected_status": 200,
                "tls_warning_days": 30,
                "enabled": False,
            },
        )
        assert created.status_code == 201
        target_id = created.json()["id"]

        queued = client.post(f"/api/v1/targets/{target_id}/check")
        assert queued.status_code == 202
        assert queued.json()["task_id"]

        deadline = time.monotonic() + 10.0
        checks: list[dict[str, object]] = []
        while time.monotonic() < deadline:
            response = client.get(f"/api/v1/targets/{target_id}/checks")
            assert response.status_code == 200
            checks = response.json()
            if checks:
                break
            time.sleep(0.25)

    assert checks, "worker did not persist a check result before the smoke-test timeout"
    assert checks[0]["status"] == "healthy"
    assert checks[0]["http_status"] == 200
