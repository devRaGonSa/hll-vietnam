"""Opaque player identity types for HLL and HLL Vietnam."""

from __future__ import annotations

from dataclasses import dataclass
from typing import NewType


PlayerId = NewType("PlayerId", str)


def player_id_from(value: object) -> PlayerId | None:
    """Normalize a present identifier without interpreting its characters."""
    if value is None:
        return None
    normalized = str(value).strip()
    return PlayerId(normalized) if normalized else None


@dataclass(frozen=True, slots=True)
class PlayerIdentity:
    """Canonical opaque ID plus explicit, independently sourced metadata."""

    player_id: PlayerId
    steam_id: str | None = None
    eos_id: str | None = None
    platform: str | None = None
    display_name: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.player_id, str) or not self.player_id.strip():
            raise ValueError("PlayerIdentity player_id must be a non-empty opaque string.")
        object.__setattr__(self, "player_id", PlayerId(self.player_id.strip()))
