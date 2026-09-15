from types import SimpleNamespace

import httpx

from app.probes.service import classify_status, run_probe


def test_expected_http_without_tls_is_healthy() -> None:
    assert classify_status(
        expected_status=200,
        http_status=200,
        http_error_type=None,
        tls_valid=None,
        tls_error_type=None,
        tls_days_remaining=None,
        tls_warning_days=30,
        version_error_type=None,
    ) == "healthy"


def test_tls_inside_warning_window_is_degraded() -> None:
    assert classify_status(
        expected_status=200,
        http_status=200,
        http_error_type=None,
        tls_valid=True,
        tls_error_type=None,
        tls_days_remaining=10,
        tls_warning_days=30,
        version_error_type=None,
    ) == "degraded"


def test_unexpected_http_status_is_failed() -> None:
    assert classify_status(
        expected_status=200,
        http_status=503,
        http_error_type=None,
        tls_valid=None,
        tls_error_type=None,
        tls_days_remaining=None,
        tls_warning_days=30,
        version_error_type=None,
    ) == "failed"


def test_network_timeout_is_failed() -> None:
    assert classify_status(
        expected_status=200,
        http_status=None,
        http_error_type="timeout",
        tls_valid=None,
        tls_error_type=None,
        tls_days_remaining=None,
        tls_warning_days=30,
        version_error_type=None,
    ) == "failed"


def test_invalid_or_expired_tls_is_failed() -> None:
    assert classify_status(
        expected_status=200,
        http_status=200,
        http_error_type=None,
        tls_valid=False,
        tls_error_type=None,
        tls_days_remaining=-1,
        tls_warning_days=30,
        version_error_type=None,
    ) == "failed"


def test_version_failure_only_degrades_otherwise_healthy_target() -> None:
    assert classify_status(
        expected_status=200,
        http_status=200,
        http_error_type=None,
        tls_valid=None,
        tls_error_type=None,
        tls_days_remaining=None,
        tls_warning_days=30,
        version_error_type="timeout",
    ) == "degraded"


def test_run_probe_http_target_end_to_end_without_network() -> None:
    target = SimpleNamespace(
        url="http://service.test/health",
        expected_status=200,
        tls_warning_days=30,
        version_url=None,
    )
    transport = httpx.MockTransport(lambda request: httpx.Response(200, request=request))

    with httpx.Client(transport=transport) as client:
        outcome = run_probe(target, client=client)

    assert outcome.status == "healthy"
    assert outcome.http_status == 200
    assert outcome.latency_ms is not None
    assert outcome.tls_valid is None
    assert outcome.error_type is None


def test_tls_probe_network_failure_marks_https_target_failed(monkeypatch) -> None:
    from app.probes import service
    from app.probes.tls import TLSProbeResult

    target = SimpleNamespace(
        url="https://service.test/health",
        expected_status=200,
        tls_warning_days=30,
        version_url=None,
    )
    transport = httpx.MockTransport(lambda request: httpx.Response(200, request=request))

    monkeypatch.setattr(
        service,
        "inspect_tls",
        lambda url: TLSProbeResult(
            error_type="timeout",
            error_message="TLS connection timed out",
        ),
    )

    with httpx.Client(transport=transport) as client:
        outcome = run_probe(target, client=client)

    assert outcome.status == "failed"
    assert outcome.error_type == "timeout"
