"""Data source selection and contracts for live and historical backend flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .collector import collect_server_snapshots
from .config import get_historical_data_source_kind, get_live_data_source_kind
from .providers.public_scoreboard_provider import PublicScoreboardHistoricalDataSource
from .providers.rcon_provider import RconLiveDataSource
from .rcon_historical_read_model import (
    describe_rcon_historical_read_model,
    list_rcon_historical_recent_activity,
    list_rcon_historical_server_summaries,
)
from .server_targets import A2SServerTarget, load_a2s_targets


LIVE_SOURCE_A2S = "a2s"
SOURCE_KIND_PUBLIC_SCOREBOARD = "public-scoreboard"
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

    def build_target_index(self) -> dict[str | None, object]:
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
class RconFirstLiveDataSource:
    """Live source arbitration with RCON as primary and A2S as controlled fallback."""

    primary_source: RconLiveDataSource = RconLiveDataSource()
    fallback_source: A2SLiveDataSource = A2SLiveDataSource()
    source_kind: str = SOURCE_KIND_RCON

    def collect_snapshots(self, *, persist: bool) -> dict[str, object]:
        attempts: list[dict[str, object]] = []
        fallback_reason: str | None = None

        try:
            primary_payload = self.primary_source.collect_snapshots(persist=persist)
        except Exception as error:  # noqa: BLE001 - source arbitration keeps fallback controlled
            attempts.append(
                build_source_attempt(
                    source=SOURCE_KIND_RCON,
                    role="primary",
                    status="error",
                    reason="rcon-live-request-failed",
                    message=str(error),
                )
            )
            fallback_reason = "rcon-live-request-failed"
        else:
            primary_success_count = int(primary_payload.get("success_count") or 0)
            primary_snapshots = list(primary_payload.get("snapshots") or [])
            if primary_success_count > 0 and primary_snapshots:
                attempts.append(
                    build_source_attempt(
                        source=SOURCE_KIND_RCON,
                        role="primary",
                        status="success",
                    )
                )
                return attach_source_policy(
                    primary_payload,
                    build_source_policy(
                        primary_source=SOURCE_KIND_RCON,
                        selected_source=SOURCE_KIND_RCON,
                        source_attempts=attempts,
                    ),
                )

            attempts.append(
                build_source_attempt(
                    source=SOURCE_KIND_RCON,
                    role="primary",
                    status="empty",
                    reason="rcon-live-returned-no-usable-snapshots",
                    message=f"success_count={primary_success_count}",
                )
            )
            fallback_reason = "rcon-live-returned-no-usable-snapshots"

        try:
            fallback_payload = self.fallback_source.collect_snapshots(persist=persist)
        except Exception as error:  # noqa: BLE001 - keep combined failure explicit
            attempts.append(
                build_source_attempt(
                    source=LIVE_SOURCE_A2S,
                    role="fallback",
                    status="error",
                    reason="a2s-live-fallback-failed",
                    message=str(error),
                )
            )
            raise RuntimeError(
                "RCON-first live collection failed and A2S fallback also failed."
            ) from error

        attempts.append(
            build_source_attempt(
                source=LIVE_SOURCE_A2S,
                role="fallback",
                status="success",
            )
        )
        return attach_source_policy(
            fallback_payload,
            build_source_policy(
                primary_source=SOURCE_KIND_RCON,
                selected_source=LIVE_SOURCE_A2S,
                fallback_used=True,
                fallback_reason=fallback_reason,
                source_attempts=attempts,
            ),
        )

    def build_target_index(self) -> dict[str | None, object]:
        target_index = dict(self.fallback_source.build_target_index())
        target_index.update(self.primary_source.build_target_index())
        return target_index


@dataclass(frozen=True, slots=True)
class RconHistoricalDataSource:
    """Persisted RCON-backed historical read model over captured competitive windows."""

    source_kind: str = SOURCE_KIND_RCON

    def fetch_public_info(self, *, base_url: str) -> dict[str, object]:
        raise RuntimeError(
            "RCON historical read mode does not support CRCON ingestion operations."
        )

    def fetch_match_page(self, *, base_url: str, page: int, limit: int) -> dict[str, object]:
        raise RuntimeError(
            "RCON historical read mode does not support CRCON ingestion operations."
        )

    def fetch_match_details(
        self,
        *,
        base_url: str,
        match_ids: list[str],
        max_workers: int,
    ) -> list[dict[str, object]]:
        raise RuntimeError(
            "RCON historical read mode does not support CRCON ingestion operations."
        )

    def list_server_summaries(self, *, server_key: str | None = None) -> list[dict[str, object]]:
        """Return coverage and freshness from persisted RCON-backed competitive history."""
        return list_rcon_historical_server_summaries(server_key=server_key)

    def list_recent_activity(
        self,
        *,
        server_key: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, object]]:
        """Return recent RCON-backed competitive history without on-demand network calls."""
        return list_rcon_historical_recent_activity(server_key=server_key, limit=limit)

    def describe_capabilities(self) -> dict[str, object]:
        """Describe the supported RCON historical read surface."""
        return describe_rcon_historical_read_model()


def get_historical_data_source() -> HistoricalDataSource:
    """Select the historical provider configured for the current environment."""
    source_kind = get_historical_data_source_kind()
    if source_kind == SOURCE_KIND_PUBLIC_SCOREBOARD:
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
        return RconFirstLiveDataSource()
    raise ValueError(f"Unsupported live data source: {source_kind}")


def get_rcon_historical_read_model() -> RconHistoricalDataSource | None:
    """Return the persisted RCON-backed historical read model when selected."""
    if get_historical_data_source_kind() != SOURCE_KIND_RCON:
        return None
    return RconHistoricalDataSource()


def describe_historical_runtime_policy() -> dict[str, object]:
    """Describe the effective historical runtime policy for the current environment."""
    if get_historical_data_source_kind() != SOURCE_KIND_RCON:
        return {
            "mode": "public-scoreboard-primary",
            "primary_source": SOURCE_KIND_PUBLIC_SCOREBOARD,
            "fallback_source": None,
            "summary": "Historical runtime uses public-scoreboard directly.",
        }
    return {
        "mode": "rcon-first-with-public-scoreboard-fallback",
        "primary_source": SOURCE_KIND_RCON,
        "fallback_source": SOURCE_KIND_PUBLIC_SCOREBOARD,
        "summary": (
            "Historical runtime attempts the persisted RCON-backed competitive model first "
            "and falls back to public-scoreboard when the requested operation is unsupported, has "
            "no coverage yet, or the primary path fails."
        ),
    }


def build_historical_runtime_source_policy(
    *,
    operation: str,
    rcon_status: str,
    fallback_reason: str | None = None,
    selected_source: str | None = None,
    rcon_message: str | None = None,
) -> dict[str, object]:
    """Build one normalized source-policy block for historical runtime reads."""
    configured_kind = get_historical_data_source_kind()
    if configured_kind != SOURCE_KIND_RCON:
        return build_source_policy(
            primary_source=SOURCE_KIND_PUBLIC_SCOREBOARD,
            selected_source=SOURCE_KIND_PUBLIC_SCOREBOARD,
            source_attempts=[
                build_source_attempt(
                    source=SOURCE_KIND_PUBLIC_SCOREBOARD,
                    role="primary",
                    status="success",
                    reason=f"{operation}-served-by-public-scoreboard",
                )
            ],
        )

    if rcon_status == "success":
        return build_source_policy(
            primary_source=SOURCE_KIND_RCON,
            selected_source=selected_source or SOURCE_KIND_RCON,
            source_attempts=[
                build_source_attempt(
                    source=SOURCE_KIND_RCON,
                    role="primary",
                    status="success",
                    reason=f"{operation}-served-by-rcon",
                )
            ],
        )

    return build_source_policy(
        primary_source=SOURCE_KIND_RCON,
        selected_source=selected_source or SOURCE_KIND_PUBLIC_SCOREBOARD,
        fallback_used=True,
        fallback_reason=fallback_reason,
        source_attempts=[
            build_source_attempt(
                source=SOURCE_KIND_RCON,
                role="primary",
                status=rcon_status,
                reason=fallback_reason,
                message=rcon_message,
            ),
            build_source_attempt(
                source=SOURCE_KIND_PUBLIC_SCOREBOARD,
                role="fallback",
                status="success",
                reason=f"{operation}-served-by-public-scoreboard-fallback",
            ),
        ],
    )


def resolve_historical_ingestion_data_source() -> tuple[HistoricalDataSource, dict[str, object]]:
    """Resolve the fallback provider used when classic scoreboard import is required."""
    configured_kind = get_historical_data_source_kind()
    if configured_kind in {SOURCE_KIND_PUBLIC_SCOREBOARD, SOURCE_KIND_RCON}:
        primary_source = (
            SOURCE_KIND_PUBLIC_SCOREBOARD
            if configured_kind == SOURCE_KIND_PUBLIC_SCOREBOARD
            else SOURCE_KIND_RCON
        )
        fallback_used = configured_kind == SOURCE_KIND_RCON
        fallback_reason = (
            "classic-historical-import-requires-public-scoreboard-fallback"
            if fallback_used
            else None
        )
        attempts = []
        if configured_kind == SOURCE_KIND_RCON:
            attempts.append(
                build_source_attempt(
                    source=SOURCE_KIND_RCON,
                    role="primary",
                    status="deferred",
                    reason="rcon-primary-writer-attempt-is-handled-by-historical-ingestion",
                )
            )
        attempts.append(
            build_source_attempt(
                source=SOURCE_KIND_PUBLIC_SCOREBOARD,
                role="fallback" if fallback_used else "primary",
                status="ready",
                reason="classic-historical-import-provider-ready",
            )
        )
        return (
            PublicScoreboardHistoricalDataSource(),
            build_source_policy(
                primary_source=primary_source,
                selected_source=SOURCE_KIND_PUBLIC_SCOREBOARD,
                fallback_used=fallback_used,
                fallback_reason=fallback_reason,
                source_attempts=attempts,
            ),
        )

    raise ValueError(f"Unsupported historical data source: {configured_kind}")


def build_source_attempt(
    *,
    source: str,
    role: str,
    status: str,
    reason: str | None = None,
    message: str | None = None,
) -> dict[str, object]:
    """Build one normalized trace entry for source arbitration."""
    return {
        "source": source,
        "role": role,
        "status": status,
        "reason": reason,
        "message": message,
    }


def build_source_policy(
    *,
    primary_source: str,
    selected_source: str,
    fallback_used: bool = False,
    fallback_reason: str | None = None,
    source_attempts: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Build one small source-policy block for API responses and worker output."""
    return {
        "primary_source": primary_source,
        "selected_source": selected_source,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "source_attempts": list(source_attempts or []),
    }


def attach_source_policy(
    payload: dict[str, object],
    source_policy: dict[str, object],
) -> dict[str, object]:
    """Attach normalized source-policy metadata to an existing payload."""
    enriched = dict(payload)
    enriched.update(source_policy)
    return enriched
