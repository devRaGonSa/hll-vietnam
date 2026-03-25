"""Player event source selection and contracts for the V2 pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .config import get_historical_data_source_kind
from .data_sources import (
    SOURCE_KIND_PUBLIC_SCOREBOARD,
    SOURCE_KIND_RCON,
    build_source_attempt,
    build_source_policy,
)
from .player_event_models import PlayerEventRecord
from .providers.player_event_source_provider import PublicScoreboardPlayerEventSource


class PlayerEventSource(Protocol):
    """Contract for adapters that normalize player event signals."""

    source_kind: str

    def extract_match_events(
        self,
        *,
        server_slug: str,
        match_payload: dict[str, object],
        source_ref: str | None = None,
    ) -> list[PlayerEventRecord]:
        """Normalize one match payload into reusable player event records."""

    def describe_scope(self) -> dict[str, object]:
        """Describe what the adapter can and cannot capture today."""


class RconPlayerEventSource:
    """Placeholder adapter for a future raw RCON/log feed."""

    source_kind = "rcon-events"

    def extract_match_events(
        self,
        *,
        server_slug: str,
        match_payload: dict[str, object],
        source_ref: str | None = None,
    ) -> list[PlayerEventRecord]:
        raise RuntimeError("Raw RCON player event extraction is not implemented yet.")

    def describe_scope(self) -> dict[str, object]:
        return {
            "source_kind": self.source_kind,
            "supports_raw_kill_events": False,
            "captures": [],
            "limitations": [
                "No raw RCON event or log feed is integrated in this repository yet.",
            ],
        }


@dataclass(frozen=True, slots=True)
class PlayerEventSourceSelection:
    """Resolved player-event adapter plus source-policy metadata."""

    source: PlayerEventSource
    source_policy: dict[str, object]


def resolve_player_event_source() -> PlayerEventSourceSelection:
    """Select the event adapter with safe fallback when raw RCON events are unavailable."""
    source_kind = get_historical_data_source_kind()
    if source_kind == SOURCE_KIND_PUBLIC_SCOREBOARD:
        return PlayerEventSourceSelection(
            source=PublicScoreboardPlayerEventSource(),
            source_policy=build_source_policy(
                primary_source=SOURCE_KIND_PUBLIC_SCOREBOARD,
                selected_source="public-scoreboard-match-summary",
                source_attempts=[
                    build_source_attempt(
                        source=SOURCE_KIND_PUBLIC_SCOREBOARD,
                        role="primary",
                        status="success",
                    )
                ],
            ),
        )
    if source_kind == SOURCE_KIND_RCON:
        return PlayerEventSourceSelection(
            source=PublicScoreboardPlayerEventSource(),
            source_policy=build_source_policy(
                primary_source=SOURCE_KIND_RCON,
                selected_source="public-scoreboard-match-summary",
                fallback_used=True,
                fallback_reason="rcon-player-events-not-implemented-yet",
                source_attempts=[
                    build_source_attempt(
                        source=SOURCE_KIND_RCON,
                        role="primary",
                        status="unsupported",
                        reason="rcon-player-events-not-implemented-yet",
                    ),
                    build_source_attempt(
                        source="public-scoreboard-match-summary",
                        role="fallback",
                        status="success",
                    ),
                ],
            ),
        )
    raise ValueError(f"Unsupported player event source: {source_kind}")
