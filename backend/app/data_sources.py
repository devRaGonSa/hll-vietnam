"""Data source selection and contracts for live and historical backend flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .collector import collect_server_snapshots
from .config import get_historical_data_source_kind, get_live_data_source_kind
from .providers.public_scoreboard_provider import PublicScoreboardHistoricalDataSource
from .server_targets import A2SServerTarget, load_a2s_targets


LIVE_SOURCE_A2S = "a2s"
SOURCE_KIND_RCON = "rcon"


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
    if source_kind == "public-scoreboard":
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
