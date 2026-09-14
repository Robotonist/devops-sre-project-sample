import math
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

DEFAULT_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class TLSProbeResult:
    tls_valid: bool | None = None
    expires_at: datetime | None = None
    days_remaining: int | None = None
    error_type: str | None = None
    error_message: str | None = None


def days_until_expiry(expires_at: datetime, now: datetime) -> int:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return math.floor((expires_at - now).total_seconds() / 86400)


def inspect_tls(url: str, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> TLSProbeResult:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        return TLSProbeResult()

    hostname = parsed.hostname
    if not hostname:
        return TLSProbeResult(
            tls_valid=False,
            error_type="tls_error",
            error_message="HTTPS URL does not contain a hostname",
        )

    port = parsed.port or 443
    context = ssl.create_default_context()

    try:
        with socket.create_connection((hostname, port), timeout=timeout_seconds) as raw_socket:
            with context.wrap_socket(raw_socket, server_hostname=hostname) as tls_socket:
                certificate = tls_socket.getpeercert()

        not_after = certificate.get("notAfter")
        if not isinstance(not_after, str):
            return TLSProbeResult(
                tls_valid=False,
                error_type="tls_error",
                error_message="TLS certificate expiration is unavailable",
            )

        expires_at = datetime.fromtimestamp(ssl.cert_time_to_seconds(not_after), tz=timezone.utc)
        now = datetime.now(timezone.utc)
        remaining = days_until_expiry(expires_at, now)
        return TLSProbeResult(
            tls_valid=remaining >= 0,
            expires_at=expires_at,
            days_remaining=remaining,
        )
    except ssl.SSLCertVerificationError:
        return TLSProbeResult(
            tls_valid=False,
            error_type="tls_error",
            error_message="TLS certificate validation failed",
        )
    except (socket.timeout, TimeoutError):
        return TLSProbeResult(
            error_type="timeout",
            error_message="TLS connection timed out",
        )
    except socket.gaierror:
        return TLSProbeResult(
            error_type="dns_error",
            error_message="TLS hostname could not be resolved",
        )
    except ConnectionRefusedError:
        return TLSProbeResult(
            error_type="connection_refused",
            error_message="TLS connection was refused",
        )
    except OSError:
        return TLSProbeResult(
            error_type="connection_error",
            error_message="TLS connection failed",
        )
