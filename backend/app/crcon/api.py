"""Sanitized, injectable HTTP client for the verified CRCON foundation API."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .models import CrconApiError


PUBLIC_INFO_ENDPOINT = "/api/get_public_info"
SCOREBOARD_MAPS_ENDPOINT = "/api/get_scoreboard_maps"
MAP_SCOREBOARD_ENDPOINT = "/api/get_map_scoreboard"
USER_AGENT = "HLL-Vietnam-CRCON-BFF/0.1"

Transport = Callable[[Request, float], Any]


class CrconApiClient:
    """Minimal CRCON GET client whose transport and auth headers are injectable."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        retries: int = 0,
        headers: Mapping[str, str] | None = None,
        transport: Transport | None = None,
    ) -> None:
        self._base_url = _validate_base_url(base_url)
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        if retries not in {0, 1}:
            raise ValueError("retries must be zero or one.")
        self._timeout_seconds = timeout_seconds
        self._retries = retries
        self._headers = {
            **dict(headers or {}),
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        self._transport = transport or _open_request

    def get_public_info(self) -> dict[str, object]:
        return self._get_dict(PUBLIC_INFO_ENDPOINT)

    def get_scoreboard_maps(
        self,
        *,
        page: int = 1,
        limit: int = 100,
        server_number: int | str | None = None,
    ) -> dict[str, object]:
        query: dict[str, object] = {"page": page, "limit": limit}
        if server_number is not None:
            query["server_number"] = server_number
        return self._get_dict(SCOREBOARD_MAPS_ENDPOINT, query)

    def get_map_scoreboard(self, *, map_id: int | str) -> dict[str, object]:
        return self._get_dict(MAP_SCOREBOARD_ENDPOINT, {"map_id": map_id})

    def _get_dict(
        self,
        endpoint: str,
        query: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        url = _join_url(self._base_url, endpoint, query)
        for _attempt in range(self._retries + 1):
            request = Request(url, headers=self._headers, method="GET")
            try:
                with self._transport(request, self._timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                result = _unwrap_result(payload)
                if not isinstance(result, dict):
                    raise CrconApiError("CRCON API returned an unexpected response.")
                return result
            except CrconApiError:
                raise
            except (HTTPError, URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError):
                continue

        raise CrconApiError("CRCON API request failed.") from None


def _validate_base_url(base_url: str) -> str:
    normalized = str(base_url or "").strip().rstrip("/")
    parsed = urlsplit(normalized)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("CRCON API base URL must be an unauthenticated HTTP(S) origin.")
    return normalized


def _join_url(
    base_url: str,
    endpoint: str,
    query: Mapping[str, object] | None,
) -> str:
    if not endpoint.startswith("/api/") or ".." in endpoint:
        raise ValueError("CRCON API endpoint is invalid.")
    parsed = urlsplit(base_url)
    base_path = parsed.path.rstrip("/")
    path = f"{base_path}{endpoint}"
    query_string = urlencode(query or {})
    return urlunsplit((parsed.scheme, parsed.netloc, path, query_string, ""))


def _unwrap_result(payload: object) -> object:
    if not isinstance(payload, dict):
        return payload
    if payload.get("failed") is True:
        raise CrconApiError("CRCON API reported a failed response.")
    return payload.get("result") if "result" in payload else payload


def _open_request(request: Request, timeout_seconds: float) -> Any:
    return urlopen(request, timeout=timeout_seconds)
