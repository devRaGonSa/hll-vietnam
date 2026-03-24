"""Public scoreboard provider adapter for historical HLL data."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..config import (
    get_historical_crcon_request_retries,
    get_historical_crcon_request_timeout_seconds,
    get_historical_crcon_retry_delay_seconds,
)


PUBLIC_INFO_ENDPOINT = "/api/get_public_info"
MATCH_LIST_ENDPOINT = "/api/get_scoreboard_maps"
MATCH_DETAIL_ENDPOINT = "/api/get_map_scoreboard"


@dataclass(frozen=True, slots=True)
class PublicScoreboardHistoricalDataSource:
    """Historical provider backed by the public CRCON scoreboard JSON API."""

    source_kind: str = "public-scoreboard"

    def fetch_public_info(self, *, base_url: str) -> dict[str, object]:
        return self._fetch_dict_payload(base_url, PUBLIC_INFO_ENDPOINT)

    def fetch_match_page(self, *, base_url: str, page: int, limit: int) -> dict[str, object]:
        return self._fetch_dict_payload(
            base_url,
            MATCH_LIST_ENDPOINT,
            {"page": page, "limit": limit},
            context=f"page={page}",
        )

    def fetch_match_details(
        self,
        *,
        base_url: str,
        match_ids: list[str],
        max_workers: int,
    ) -> list[dict[str, object]]:
        if not match_ids:
            return []
        if max_workers <= 1:
            return [
                self._fetch_match_detail(base_url=base_url, match_id=match_id)
                for match_id in match_ids
            ]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self._fetch_match_detail, base_url=base_url, match_id=match_id)
                for match_id in match_ids
            ]
            return [future.result() for future in futures]

    def _fetch_match_detail(self, *, base_url: str, match_id: str) -> dict[str, object]:
        return self._fetch_dict_payload(
            base_url,
            MATCH_DETAIL_ENDPOINT,
            {"map_id": match_id},
            context=f"match={match_id}",
        )

    def _fetch_json(
        self,
        *,
        base_url: str,
        endpoint: str,
        query: dict[str, object] | None = None,
    ) -> object:
        url = f"{base_url}{endpoint}"
        if query:
            url = f"{url}?{urlencode(query)}"

        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "HLL-Vietnam-Historical-Ingestion/0.1",
            },
        )
        try:
            with urlopen(
                request,
                timeout=get_historical_crcon_request_timeout_seconds(),
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"Historical provider request failed: {url} ({exc.code})") from exc
        except URLError as exc:
            raise RuntimeError(f"Historical provider request failed: {url} ({exc.reason})") from exc

    def _fetch_dict_payload(
        self,
        base_url: str,
        endpoint: str,
        query: dict[str, object] | None = None,
        *,
        context: str = "",
        retries: int | None = None,
    ) -> dict[str, object]:
        resolved_retries = retries or get_historical_crcon_request_retries()
        base_retry_delay_seconds = get_historical_crcon_retry_delay_seconds()
        last_error: Exception | None = None
        for attempt in range(1, resolved_retries + 1):
            try:
                payload = _unwrap_result(
                    self._fetch_json(base_url=base_url, endpoint=endpoint, query=query)
                )
            except Exception as exc:  # pragma: no cover - network path
                last_error = exc
            else:
                if isinstance(payload, dict):
                    return payload
                last_error = ValueError(
                    f"Unexpected payload type for {base_url}{endpoint} {context}".strip()
                )

            if attempt < resolved_retries:
                time.sleep(base_retry_delay_seconds * attempt)

        assert last_error is not None
        raise last_error


def _unwrap_result(payload: object) -> object:
    if not isinstance(payload, dict):
        return payload
    if "result" not in payload:
        return payload
    return payload.get("result")
