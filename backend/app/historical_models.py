"""Historical domain models for persisted CRCON scoreboard data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class HistoricalServerDefinition:
    """Stable identity for one historical CRCON source."""

    slug: str
    display_name: str
    scoreboard_base_url: str
    server_number: int | None
    source_kind: str = "crcon-scoreboard-json"


@dataclass(frozen=True, slots=True)
class HistoricalMapRecord:
    """Normalized map metadata reused across historical matches."""

    external_map_id: str | None
    map_name: str | None
    pretty_name: str | None
    game_mode: str | None
    image_name: str | None


@dataclass(frozen=True, slots=True)
class HistoricalMatchRecord:
    """Normalized match identity and summary."""

    external_match_id: str
    server_slug: str
    created_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None
    map_name: str | None
    map_pretty_name: str | None
    map_external_id: str | None
    game_mode: str | None
    image_name: str | None
    allied_score: int | None
    axis_score: int | None


@dataclass(frozen=True, slots=True)
class HistoricalPlayerIdentity:
    """Stable player identity across historical match stats."""

    stable_player_key: str
    display_name: str
    steam_id: str | None
    source_player_id: str | None


@dataclass(frozen=True, slots=True)
class HistoricalPlayerMatchStats:
    """Metrics persisted per player and match."""

    stable_player_key: str
    match_player_ref: str | None
    team_side: str | None
    level: int | None
    kills: int | None
    deaths: int | None
    teamkills: int | None
    time_seconds: int | None
    kills_per_minute: float | None
    deaths_per_minute: float | None
    kill_death_ratio: float | None
    combat: int | None
    offense: int | None
    defense: int | None
    support: int | None


@dataclass(frozen=True, slots=True)
class HistoricalIngestionRunSummary:
    """Outcome metadata recorded for one ingestion execution."""

    mode: str
    started_at: datetime
    completed_at: datetime | None
    status: str
    pages_processed: int
    matches_seen: int
    matches_inserted: int
    matches_updated: int
    player_rows_inserted: int
    player_rows_updated: int
