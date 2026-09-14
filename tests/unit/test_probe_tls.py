from datetime import datetime, timedelta, timezone

from app.probes.tls import days_until_expiry


def test_days_until_expiry_returns_thirty_days() -> None:
    now = datetime(2026, 9, 13, tzinfo=timezone.utc)
    assert days_until_expiry(now + timedelta(days=30), now) == 30


def test_days_until_expiry_is_negative_for_expired_certificate() -> None:
    now = datetime(2026, 9, 13, tzinfo=timezone.utc)
    assert days_until_expiry(now - timedelta(days=1), now) == -1
