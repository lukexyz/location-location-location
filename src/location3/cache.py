"""Private response caching with a redacted, bounded request ledger."""

from __future__ import annotations

from base64 import b64decode, b64encode
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Callable, Mapping
from urllib.parse import urlsplit, urlunsplit

from .net import HttpResponse, HttpTransport


Clock = Callable[[], datetime]


@dataclass
class RequestLedger:
    """Collect safe request metadata and enforce a shared network-call cap."""

    max_network_requests: int
    entries: list[dict[str, object]] = field(default_factory=list)
    network_requests: int = 0

    def reserve_network_request(self) -> None:
        if self.network_requests >= self.max_network_requests:
            raise RuntimeError(
                f"provider call cap of {self.max_network_requests} would be exceeded"
            )
        self.network_requests += 1

    @property
    def cache_used(self) -> bool:
        return any(entry["cache"] == "hit" for entry in self.entries)


class CachingTransport:
    """Cache successful HTTP responses and record no sensitive request material."""

    def __init__(
        self,
        provider: str,
        upstream: HttpTransport,
        cache_directory: Path,
        ledger: RequestLedger,
        *,
        ttl: timedelta,
        clock: Clock | None = None,
    ) -> None:
        if not provider or not provider.replace("-", "").isalnum():
            raise ValueError("provider must be a simple non-empty name")
        if ttl <= timedelta(0):
            raise ValueError("cache ttl must be positive")
        self._provider = provider
        self._upstream = upstream
        self._directory = cache_directory / provider
        self._ledger = ledger
        self._ttl = ttl
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes,
        timeout: float,
    ) -> HttpResponse:
        now = _aware(self._clock())
        request_id = _request_id(method, url, headers, body)
        cache_path = self._directory / f"{request_id.removeprefix('sha256:')}.json"
        cached = _read_cache(cache_path, now)
        if cached is not None:
            response, expires_at = cached
            self._record(request_id, url, now, "hit", response.status, expires_at)
            return response

        self._ledger.reserve_network_request()
        try:
            upstream_response = self._upstream.request(
                method, url, headers=headers, body=body, timeout=timeout
            )
        except Exception:
            self._record(request_id, url, now, "miss", 0, None)
            raise

        response = HttpResponse(
            upstream_response.status,
            upstream_response.body,
            {**upstream_response.headers, "X-Location3-Retrieved-At": now.isoformat()},
        )
        expires_at = now + self._ttl
        if 200 <= response.status < 300:
            _write_cache(cache_path, response, now, expires_at)
        self._record(request_id, url, now, "miss", response.status, expires_at)
        return response

    def _record(
        self,
        request_id: str,
        url: str,
        requested_at: datetime,
        cache: str,
        status: int,
        expires_at: datetime | None,
    ) -> None:
        entry: dict[str, object] = {
            "provider": self._provider,
            "request_id": request_id,
            "endpoint": _safe_endpoint(url),
            "requested_at": requested_at.isoformat(),
            "cache": cache,
            "status": status,
        }
        if expires_at is not None:
            entry["cache_expires_at"] = expires_at.isoformat()
        self._ledger.entries.append(entry)


def _request_id(
    method: str, url: str, headers: Mapping[str, str], body: bytes
) -> str:
    content_type = next(
        (value for key, value in headers.items() if key.casefold() == "content-type"), ""
    )
    fingerprint = json.dumps(
        {
            "method": method.upper(),
            "url": url,
            "content_type": content_type,
            "body_sha256": sha256(body).hexdigest(),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{sha256(fingerprint).hexdigest()}"


def _safe_endpoint(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("provider endpoint must be an HTTP URL")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _read_cache(
    path: Path, now: datetime
) -> tuple[HttpResponse, datetime] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        expires_at = _parse_datetime(payload["expires_at"])
        if payload.get("schema_version") != "1" or expires_at <= now:
            return None
        headers = {str(key): str(value) for key, value in payload["headers"].items()}
        headers["X-Location3-Retrieved-At"] = str(payload["stored_at"])
        response = HttpResponse(
            status=int(payload["status"]),
            body=b64decode(payload["body_base64"], validate=True),
            headers=headers,
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None
    return response, expires_at


def _write_cache(
    path: Path,
    response: HttpResponse,
    stored_at: datetime,
    expires_at: datetime,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1",
        "stored_at": stored_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "status": response.status,
        "headers": dict(response.headers),
        "body_base64": b64encode(response.body).decode("ascii"),
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _parse_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    return _aware(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc)
