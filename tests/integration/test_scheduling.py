from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.repositories import list_due_targets
from app.models.check_result import CheckResult
from app.models.target import Target


def add_target(
    db: Session,
    *,
    name: str,
    interval_seconds: int = 60,
    enabled: bool = True,
) -> Target:
    target = Target(
        name=name,
        url="http://service.test/health",
        interval_seconds=interval_seconds,
        expected_status=200,
        tls_warning_days=30,
        enabled=enabled,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


def add_result(db: Session, target: Target, *, started_at: datetime) -> None:
    db.add(
        CheckResult(
            target_id=target.id,
            started_at=started_at,
            completed_at=started_at + timedelta(seconds=1),
            status="healthy",
            http_status=200,
            latency_ms=10.0,
            tls_valid=None,
            tls_expires_at=None,
            tls_days_remaining=None,
            version=None,
            error_type=None,
            error_message=None,
        )
    )
    db.commit()


def test_list_due_targets_applies_interval_and_enabled_rules() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime(2026, 9, 13, 20, 0, tzinfo=UTC)

    with Session(engine) as db:
        new_target = add_target(db, name="New")
        overdue_target = add_target(db, name="Overdue")
        recent_target = add_target(db, name="Recent")
        disabled_target = add_target(db, name="Disabled", enabled=False)

        add_result(db, overdue_target, started_at=now - timedelta(seconds=61))
        add_result(db, recent_target, started_at=now - timedelta(seconds=59))

        due = list_due_targets(db, now=now)
        new_id = new_target.id
        overdue_id = overdue_target.id
        recent_id = recent_target.id
        disabled_id = disabled_target.id

    due_ids = {target.id for target in due}
    assert new_id in due_ids
    assert overdue_id in due_ids
    assert recent_id not in due_ids
    assert disabled_id not in due_ids


def test_dispatch_due_targets_enqueues_each_due_target() -> None:
    from app.worker.dispatch import dispatch_due_targets_once

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime(2026, 9, 13, 20, 0, tzinfo=UTC)
    enqueued: list[object] = []

    with Session(engine) as db:
        due_one = add_target(db, name="Due One")
        due_two = add_target(db, name="Due Two")
        recent = add_target(db, name="Recent Again")
        add_result(db, recent, started_at=now - timedelta(seconds=10))

        count = dispatch_due_targets_once(
            db,
            now=now,
            enqueue=lambda target_id: enqueued.append(target_id) or "task-id",
        )
        expected = {due_one.id, due_two.id}

    assert count == 2
    assert set(enqueued) == expected
