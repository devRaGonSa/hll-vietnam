"""Normalized player event models for the V2 event pipeline foundation."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class PlayerEventRecord:
    """Minimal normalized player event contract reused across source and storage."""

    event_id: str
    event_type: str
    occurred_at: str | None
    server_slug: str
    external_match_id: str
    source_kind: str
    source_ref: str | None
    raw_event_ref: str | None
    killer_player_key: str | None
    killer_display_name: str | None
    victim_player_key: str | None
    victim_display_name: str | None
    weapon_name: str | None
    weapon_category: str | None
    kill_category: str | None
    is_teamkill: bool
    event_value: int = 1

    def to_dict(self) -> dict[str, object]:
        """Return the event as a plain dictionary."""
        return asdict(self)
