from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.check_result import CheckResult
from app.models.target import Target
from app.probes.service import ProbeOutcome
from app.worker.executor import execute_target_check


def test_execute_target_check_persists_one_result() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        target = Target(
            name="Worker Target",
            url="http://service.test/health",
            interval_seconds=60,
            expected_status=200,
            tls_warning_days=30,
            enabled=True,
        )
        session.add(target)
        session.commit()
        session.refresh(target)

        def fake_probe(probe_target: Target) -> ProbeOutcome:
            assert probe_target.id == target.id
            return ProbeOutcome(
                status="healthy",
                http_status=200,
                latency_ms=12.5,
                tls_valid=None,
                tls_expires_at=None,
                tls_days_remaining=None,
                version="1.2.3",
                error_type=None,
                error_message=None,
            )

        result_id = execute_target_check(session, target.id, probe_runner=fake_probe)

        assert isinstance(result_id, UUID)
        results = list(session.scalars(select(CheckResult)).all())
        assert len(results) == 1
        result = results[0]
        assert result.id == result_id
        assert result.target_id == target.id
        assert result.status == "healthy"
        assert result.http_status == 200
        assert result.latency_ms == 12.5
        assert result.version == "1.2.3"
        assert result.started_at is not None
        assert result.completed_at is not None


def test_execute_target_check_returns_none_for_deleted_target() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        missing_id = UUID("00000000-0000-0000-0000-000000000001")
        result_id = execute_target_check(session, missing_id)

    assert result_id is None
