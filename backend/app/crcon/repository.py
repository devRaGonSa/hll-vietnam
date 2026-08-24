"""Read-only CRCON repository contract and server-scope resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from ..domain import PlayerIdentity
from ..server_targets import ServerTarget
from .models import CrconCapabilityReport, CrconSchemaIncompatibleError


@dataclass(frozen=True, slots=True)
class CrconServerScope:
    """Canonical history scope plus an independently verified log discriminator."""

    server_number: int
    game: str
    log_server: str | None = None
    log_game: int | None = None

    def __post_init__(self) -> None:
        if self.server_number <= 0:
            raise ValueError("CRCON server scope number must be positive.")
        if self.game not in {"hll", "hllv"}:
            raise ValueError("CRCON server scope game must be 'hll' or 'hllv'.")
        if self.log_game is not None and self.log_game not in {1, 2}:
            raise ValueError("CRCON log game discriminator must be 1 or 2.")

    def require_log_server(self) -> str:
        if self.log_server is None or not self.log_server.strip():
            raise CrconSchemaIncompatibleError(
                "CRCON log server discriminator is unverified for this target."
            )
        return self.log_server.strip()

    def require_log_discriminators(self) -> tuple[str, int]:
        """Fail closed until both deployed log discriminators are explicit."""
        log_server = self.require_log_server()
        if self.log_game is None:
            raise CrconSchemaIncompatibleError(
                "CRCON log game discriminator is unverified for this target."
            )
        return log_server, self.log_game


def resolve_server_scope(
    target: ServerTarget,
    *,
    log_server: str | None = None,
    log_game: int | None = None,
) -> CrconServerScope:
    """Resolve scope once without inferring log server from server_number."""
    return CrconServerScope(
        server_number=target.server_number,
        game=target.game,
        log_server=str(log_server).strip() if log_server is not None else None,
        log_game=log_game,
    )


@dataclass(frozen=True, slots=True)
class CrconCurrentMap:
    id: int
    start: datetime
    end: datetime | None
    server_number: int
    map_name: str
    result: dict[str, int] | None


@dataclass(frozen=True, slots=True)
class CrconMatchLogEvent:
    id: int
    event_time: datetime
    type: str
    player1_name: str | None
    player1_id: str | None
    player2_name: str | None
    player2_id: str | None
    weapon: str | None


@dataclass(frozen=True, slots=True)
class CrconMatchCombatStats:
    player_id: str | None
    player_name: str
    kills: int
    deaths: int
    teamkills: int
    deaths_by_teamkill: int
    weapon_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class CrconPlayerAggregate:
    """Reusable per-player history aggregate scoped to one CRCON server."""

    identity: PlayerIdentity
    scope: CrconServerScope
    matches_played: int
    record_kills: int
    total_kills: int
    deaths: int
    combat: int
    offense: int
    defense: int
    support: int
    vehicle_kills: int
    vehicles_destroyed: int


@dataclass(frozen=True, slots=True)
class CrconServerAggregate:
    matches_count: int
    unique_players: int
    first_match_at: datetime | None
    last_match_at: datetime | None
    top_maps: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class CrconRankingRow:
    player_id: str
    player_name: str
    matches_played: int
    record_kills: int
    kills: int
    deaths: int
    teamkills: int
    time_seconds: int
    combat: int
    offense: int
    defense: int
    support: int
    vehicle_kills: int
    vehicles_destroyed: int
    matches_over_100_kills: int
    ranking_position: int
    metric_value: float
    total_rows: int
    source_matches_count: int


@dataclass(frozen=True, slots=True)
class CrconPlayerProfileAggregate:
    player_id: str
    player_name: str
    steam_id: str | None
    eos_id: str | None
    platform: str | None
    matches_played: int
    record_kills: int
    kills: int
    deaths: int
    teamkills: int
    deaths_by_teamkill: int
    time_seconds: int
    combat: int
    offense: int
    defense: int
    support: int
    vehicle_kills: int
    vehicles_destroyed: int
    last_seen_at: datetime | None
    servers_seen: tuple[int, ...]
    kills_ranking_position: int | None


@dataclass(frozen=True, slots=True)
class CrconHistoricalMatchLookup:
    """One bounded, explicitly scoped CRCON map-history lookup."""

    map_id: int
    scope: CrconServerScope

    def __post_init__(self) -> None:
        if isinstance(self.map_id, bool) or self.map_id <= 0:
            raise ValueError("CRCON historical map ID must be a positive integer.")


@dataclass(frozen=True, slots=True)
class CrconMatchPlayerCount:
    map_id: int
    player_count: int


@dataclass(frozen=True, slots=True)
class CrconExplicitPlayerIdentity:
    """Explicit platform metadata keyed by CRCON's otherwise opaque player ID."""

    player_id: str
    steam_id_64: str | None
    eos_id: str | None
    platform: str | None


class CrconReadRepository(Protocol):
    """Small application-facing contract; it intentionally exposes no raw SQL."""

    @property
    def configured(self) -> bool: ...

    def probe_capabilities(
        self,
        *,
        api_configured: bool = False,
    ) -> CrconCapabilityReport: ...

    def get_player_aggregate(
        self,
        *,
        identity: PlayerIdentity,
        scope: CrconServerScope,
    ) -> CrconPlayerAggregate: ...

    def find_current_map(
        self,
        *,
        server_number: int,
        map_name: str | None,
        started_at: datetime | None,
        tolerance_seconds: int = 180,
    ) -> CrconCurrentMap | None: ...

    def list_match_log_events(
        self,
        *,
        scope: CrconServerScope,
        started_at: datetime,
        ended_at: datetime,
        limit: int = 500,
    ) -> tuple[CrconMatchLogEvent, ...]: ...

    def aggregate_match_combat_stats(
        self,
        *,
        scope: CrconServerScope,
        started_at: datetime,
        ended_at: datetime,
    ) -> tuple[CrconMatchCombatStats, ...]: ...

    def get_server_aggregate(
        self,
        *,
        scopes: tuple[CrconServerScope, ...],
    ) -> CrconServerAggregate: ...

    def list_rankings(
        self,
        *,
        scopes: tuple[CrconServerScope, ...],
        started_at: datetime | None,
        ended_at: datetime | None,
        metric: str,
        limit: int,
        offset: int = 0,
    ) -> tuple[CrconRankingRow, ...]: ...

    def get_player_profile_aggregate(
        self,
        *,
        player_id: str,
        scopes: tuple[CrconServerScope, ...],
        started_at: datetime | None,
        ended_at: datetime | None,
    ) -> CrconPlayerProfileAggregate | None: ...

    def list_match_player_counts(
        self,
        *,
        matches: tuple[CrconHistoricalMatchLookup, ...],
    ) -> tuple[CrconMatchPlayerCount, ...]: ...

    def list_match_player_identities(
        self,
        *,
        match: CrconHistoricalMatchLookup,
        player_ids: tuple[str, ...],
    ) -> tuple[CrconExplicitPlayerIdentity, ...]: ...

    def close(self) -> None: ...
