"""Data source provider contracts for live and historical backend flows."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .collector import collect_server_snapshots
from .config import (
    get_historical_crcon_request_retries,
    get_historical_crcon_request_timeout_seconds,
    get_historical_crcon_retry_delay_seconds,
    get_historical_data_source_kind,
    get_live_data_source_kind,
)
from .server_targets import A2SServerTarget, load_a2s_targets


HISTORICAL_SOURCE_PUBLIC_SCOREBOARD = "public-scoreboard"
LIVE_SOURCE_A2S = "a2s"
SOURCE_KIND_RCON = "rcon"

PUBLIC_INFO_ENDPOINT = "/api/get_public_info"
MATCH_LIST_ENDPOINT = "/api/get_scoreboard_maps"
MATCH_DETAIL_ENDPOINT = "/api/get_map_scoreboard"


class HistoricalDataSource(Protocol):
    """Contract for historical providers used by ingestion flows."""

    source_kind: str

    def fetch_public_info(self, *, base_url: str) -> dict[str, object]:
        """Fetch provider metadata for one historical source."""

    def fetch_match_page(self, *, base_url: str, page: int, limit: int) -> dict[str, object]:
        """Fetch one page of historical matches."""

    def fetch_match_details(
        self,
        *,
        base_url: str,
        match_ids: list[str],
        max_workers: int,
    ) -> list[dict[str, object]]:
        """Fetch detailed payloads for one batch of matches."""


class LiveDataSource(Protocol):
    """Contract for live providers used by API payload builders."""

    source_kind: str

    def collect_snapshots(self, *, persist: bool) -> dict[str, object]:
        """Collect one live snapshot batch."""

    def build_target_index(self) -> dict[str | None, A2SServerTarget]:
        """Return optional server connection metadata keyed by external id."""


@dataclass(frozen=True, slots=True)
class PublicScoreboardHistoricalDataSource:
    """Historical provider backed by the public CRCON scoreboard JSON API."""

    source_kind: str = HISTORICAL_SOURCE_PUBLIC_SCOREBOARD

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


@dataclass(frozen=True, slots=True)
class A2SLiveDataSource:
    """Live provider backed by the existing A2S collector flow."""

    source_kind: str = LIVE_SOURCE_A2S

    def collect_snapshots(self, *, persist: bool) -> dict[str, object]:
        return collect_server_snapshots(
            source_mode="a2s",
            allow_controlled_fallback=False,
            persist=persist,
        )

    def build_target_index(self) -> dict[str | None, A2SServerTarget]:
        return {
            target.external_server_id: target
            for target in load_a2s_targets()
            if target.external_server_id
        }


@dataclass(frozen=True, slots=True)
class RconHistoricalDataSource:
    """Placeholder historical provider for future production RCON integration."""

    source_kind: str = SOURCE_KIND_RCON

    def fetch_public_info(self, *, base_url: str) -> dict[str, object]:
        raise RuntimeError("Historical RCON provider is not implemented yet.")

    def fetch_match_page(self, *, base_url: str, page: int, limit: int) -> dict[str, object]:
        raise RuntimeError("Historical RCON provider is not implemented yet.")

    def fetch_match_details(
        self,
        *,
        base_url: str,
        match_ids: list[str],
        max_workers: int,
    ) -> list[dict[str, object]]:
        raise RuntimeError("Historical RCON provider is not implemented yet.")


@dataclass(frozen=True, slots=True)
class RconLiveDataSource:
    """Placeholder live provider for future production RCON integration."""

    source_kind: str = SOURCE_KIND_RCON

    def collect_snapshots(self, *, persist: bool) -> dict[str, object]:
        raise RuntimeError("Live RCON provider is not implemented yet.")

    def build_target_index(self) -> dict[str | None, A2SServerTarget]:
        return {}


def get_historical_data_source() -> HistoricalDataSource:
    """Select the historical provider configured for the current environment."""
    source_kind = get_historical_data_source_kind()
    if source_kind == HISTORICAL_SOURCE_PUBLIC_SCOREBOARD:
        return PublicScoreboardHistoricalDataSource()
    if source_kind == SOURCE_KIND_RCON:
        return RconHistoricalDataSource()
    raise ValueError(f"Unsupported historical data source: {source_kind}")


def get_live_data_source() -> LiveDataSource:
    """Select the live provider configured for the current environment."""
    source_kind = get_live_data_source_kind()
    if source_kind == LIVE_SOURCE_A2S:
        return A2SLiveDataSource()
    if source_kind == SOURCE_KIND_RCON:
        return RconLiveDataSource()
    raise ValueError(f"Unsupported live data source: {source_kind}")


def _unwrap_result(payload: object) -> object:
    if not isinstance(payload, dict):
        return payload
    if "result" not in payload:
        return payload
    return payload.get("result")
