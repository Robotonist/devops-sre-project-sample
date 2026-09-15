from dataclasses import dataclass
from time import perf_counter

import httpx

DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_VERSION_READ_BYTES = 4096
MAX_VERSION_LENGTH = 256


@dataclass(frozen=True)
class HTTPProbeResult:
    http_status: int | None = None
    latency_ms: float | None = None
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class VersionProbeResult:
    version: str | None = None
    error_type: str | None = None
    error_message: str | None = None


def _normalize_http_exception(exc: httpx.HTTPError) -> tuple[str, str]:
    if isinstance(exc, httpx.TimeoutException):
        return "timeout", "HTTP request timed out"
    if isinstance(exc, httpx.ConnectError):
        return "connection_error", "HTTP connection failed"
    return "http_error", "HTTP request failed"


def probe_http(
    url: str,
    *,
    client: httpx.Client | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> HTTPProbeResult:
    owns_client = client is None
    active_client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=False)
    started = perf_counter()

    try:
        with active_client.stream("GET", url) as response:
            latency_ms = (perf_counter() - started) * 1000
            return HTTPProbeResult(http_status=response.status_code, latency_ms=latency_ms)
    except httpx.HTTPError as exc:
        error_type, error_message = _normalize_http_exception(exc)
        return HTTPProbeResult(
            latency_ms=(perf_counter() - started) * 1000,
            error_type=error_type,
            error_message=error_message,
        )
    finally:
        if owns_client:
            active_client.close()


def fetch_version(
    url: str,
    *,
    client: httpx.Client | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> VersionProbeResult:
    owns_client = client is None
    active_client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=False)

    try:
        with active_client.stream("GET", url) as response:
            if not 200 <= response.status_code < 300:
                return VersionProbeResult(
                    error_type="unexpected_status",
                    error_message=f"Version endpoint returned HTTP {response.status_code}",
                )

            body = bytearray()
            for chunk in response.iter_bytes():
                remaining = MAX_VERSION_READ_BYTES - len(body)
                if remaining <= 0:
                    break
                body.extend(chunk[:remaining])
                if len(body) >= MAX_VERSION_READ_BYTES:
                    break

            encoding = response.encoding or "utf-8"
            normalized = " ".join(body.decode(encoding, errors="replace").split())
            return VersionProbeResult(version=normalized[:MAX_VERSION_LENGTH])
    except httpx.HTTPError as exc:
        error_type, error_message = _normalize_http_exception(exc)
        return VersionProbeResult(error_type=error_type, error_message=error_message)
    finally:
        if owns_client:
            active_client.close()
