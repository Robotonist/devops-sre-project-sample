import httpx

from app.probes.http import fetch_version, probe_http


def test_http_probe_records_status_and_latency() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, request=request))

    with httpx.Client(transport=transport) as client:
        result = probe_http("https://service.test/health", client=client)

    assert result.http_status == 200
    assert result.latency_ms is not None
    assert result.latency_ms >= 0
    assert result.error_type is None


def test_http_probe_normalizes_timeout() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow upstream", request=request)

    with httpx.Client(transport=httpx.MockTransport(timeout)) as client:
        result = probe_http("https://service.test/health", client=client)

    assert result.http_status is None
    assert result.error_type == "timeout"
    assert result.error_message == "HTTP request timed out"


def test_version_response_is_normalized_and_capped() -> None:
    raw = "  version   1.2.3  " + ("x" * 400)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=raw, request=request)
    )

    with httpx.Client(transport=transport) as client:
        result = fetch_version("https://service.test/version", client=client)

    assert result.error_type is None
    assert result.version is not None
    assert result.version.startswith("version 1.2.3")
    assert len(result.version) == 256


def test_http_probe_normalizes_connection_failure() -> None:
    def connect_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with httpx.Client(transport=httpx.MockTransport(connect_error)) as client:
        result = probe_http("https://service.test/health", client=client)

    assert result.error_type == "connection_error"
    assert result.error_message == "HTTP connection failed"


def test_check_result_schema_fits_max_normalized_version() -> None:
    from app.models.check_result import CheckResult
    from app.probes.http import MAX_VERSION_LENGTH

    assert CheckResult.__table__.c.version.type.length >= MAX_VERSION_LENGTH
