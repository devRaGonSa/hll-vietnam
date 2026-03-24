"""Player event source selection and contracts for the V2 pipeline."""

from __future__ import annotations

from typing import Protocol

from .config import get_historical_data_source_kind
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


def get_player_event_source() -> PlayerEventSource:
    """Select the event adapter that best matches the configured historical source."""
    source_kind = get_historical_data_source_kind()
    if source_kind == "public-scoreboard":
        return PublicScoreboardPlayerEventSource()
    if source_kind == "rcon":
        return RconPlayerEventSource()
    raise ValueError(f"Unsupported player event source: {source_kind}")
