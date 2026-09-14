from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urlparse

import httpx

from app.probes.http import fetch_version, probe_http
from app.probes.tls import inspect_tls

if TYPE_CHECKING:
    from app.models.target import Target


class ProbeTarget(Protocol):
    url: str
    expected_status: int
    tls_warning_days: int
    version_url: str | None


@dataclass(frozen=True)
class ProbeOutcome:
    status: str
    http_status: int | None
    latency_ms: float | None
    tls_valid: bool | None
    tls_expires_at: datetime | None
    tls_days_remaining: int | None
    version: str | None
    error_type: str | None
    error_message: str | None


def classify_status(
    *,
    expected_status: int,
    http_status: int | None,
    http_error_type: str | None,
    tls_valid: bool | None,
    tls_error_type: str | None,
    tls_days_remaining: int | None,
    tls_warning_days: int,
    version_error_type: str | None,
) -> str:
    if http_error_type is not None:
        return "failed"
    if http_status != expected_status:
        return "failed"
    if tls_error_type is not None:
        return "failed"
    if tls_valid is False:
        return "failed"
    if tls_days_remaining is not None and tls_days_remaining < 0:
        return "failed"
    if tls_days_remaining is not None and tls_days_remaining <= tls_warning_days:
        return "degraded"
    if version_error_type is not None:
        return "degraded"
    return "healthy"


def run_probe(
    target: "Target | ProbeTarget",
    *,
    client: httpx.Client | None = None,
) -> ProbeOutcome:
    http_result = probe_http(target.url, client=client)

    parsed = urlparse(target.url)
    tls_result = inspect_tls(target.url) if parsed.scheme.lower() == "https" else None

    version_result = (
        fetch_version(target.version_url, client=client) if target.version_url else None
    )

    tls_valid = tls_result.tls_valid if tls_result else None
    tls_expires_at = tls_result.expires_at if tls_result else None
    tls_days_remaining = tls_result.days_remaining if tls_result else None
    tls_error_type = tls_result.error_type if tls_result else None
    tls_error_message = tls_result.error_message if tls_result else None
    version = version_result.version if version_result else None
    version_error_type = version_result.error_type if version_result else None
    version_error_message = version_result.error_message if version_result else None

    status = classify_status(
        expected_status=target.expected_status,
        http_status=http_result.http_status,
        http_error_type=http_result.error_type,
        tls_valid=tls_valid,
        tls_error_type=tls_error_type,
        tls_days_remaining=tls_days_remaining,
        tls_warning_days=target.tls_warning_days,
        version_error_type=version_error_type,
    )

    error_type: str | None = None
    error_message: str | None = None

    if http_result.error_type:
        error_type = http_result.error_type
        error_message = http_result.error_message
    elif http_result.http_status != target.expected_status:
        error_type = "unexpected_status"
        error_message = (
            f"Expected HTTP {target.expected_status}, received {http_result.http_status}"
        )
    elif tls_error_type or tls_valid is False:
        error_type = tls_error_type or "tls_invalid"
        error_message = tls_error_message or "TLS certificate is invalid or expired"
    elif tls_days_remaining is not None and tls_days_remaining <= target.tls_warning_days:
        error_type = "tls_expiring"
        error_message = "TLS certificate is within the configured warning window"
    elif version_error_type:
        error_type = f"version_{version_error_type}"
        error_message = version_error_message

    return ProbeOutcome(
        status=status,
        http_status=http_result.http_status,
        latency_ms=http_result.latency_ms,
        tls_valid=tls_valid,
        tls_expires_at=tls_expires_at,
        tls_days_remaining=tls_days_remaining,
        version=version,
        error_type=error_type,
        error_message=error_message,
    )
