"""CRCON PostgreSQL application service for public historical aggregates."""

from __future__ import annotations

import atexit
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from threading import RLock
from typing import Callable

from ..config import (
    get_crcon_database_connect_timeout_seconds,
    get_crcon_database_lock_timeout_ms,
    get_crcon_database_pool_size,
    get_crcon_database_statement_timeout_ms,
    get_crcon_database_url,
)
from ..server_targets import ServerTarget, load_server_targets
from ..player_external_profiles import build_external_player_profile_fields
from .cache import TtlCache
from .models import (
    CrconAggregateState,
    CrconCapability,
    CrconCapabilityStatus,
    CrconDatabaseError,
)
from .postgres_repository import PostgresCrconRepository
from .repository import CrconReadRepository, CrconServerScope, resolve_server_scope


ALL_SERVER_KEYS = {"", "all", "all-servers"}


@dataclass(frozen=True, slots=True)
class AggregateWindow:
    timeframe: str
    start: datetime | None
    end: datetime | None
    label: str


class HistoricalAggregateService:
    """Typed, cached aggregate reads with explicit availability states."""

    def __init__(
        self,
        *,
        repository: CrconReadRepository,
        targets: tuple[ServerTarget, ...],
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        cache: TtlCache[tuple[object, ...], dict[str, object]] | None = None,
    ) -> None:
        self._repository = repository
        self._targets = tuple(target for target in targets if target.enabled)
        self._now = now
        self._cache = cache or TtlCache(max_entries=256, ttl_seconds=60)

    def server_summary(self, *, server_id: str | None) -> dict[str, object]:
        resolved = self._resolve(server_id)
        if isinstance(resolved, dict):
            return resolved
        targets, scopes = resolved
        gate = self._schema_gate()
        if gate is not None:
            return gate
        key = ("summary", scopes[0].game, tuple(scope.server_number for scope in scopes))
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        try:
            item = self._repository.get_server_aggregate(scopes=scopes)
        except CrconDatabaseError:
            return self._state(CrconAggregateState.UNAVAILABLE, "database-read-failed")
        server = targets[0] if len(targets) == 1 else None
        if item.matches_count == 0:
            coverage_status = "empty"
        elif (
            item.first_match_at is not None
            and item.last_match_at is not None
            and item.last_match_at - item.first_match_at >= timedelta(days=7)
        ):
            coverage_status = "week-plus"
        else:
            coverage_status = "under-week"
        result = {
            **self._state(CrconAggregateState.AVAILABLE),
            "found": item.matches_count > 0,
            "generated_at": _iso(self._now()),
            "summary_basis": "crcon-postgres-read-only",
            "server_slug": server.key if server else "all-servers",
            "item": {
                "server": {
                    "slug": server.key if server else "all-servers",
                    "name": server.display_name if server else "Todos los servidores",
                },
                "matches_count": item.matches_count,
                "imported_matches_count": item.matches_count,
                "unique_players": item.unique_players,
                "coverage": {
                    "status": coverage_status,
                    "first_match_at": _iso(item.first_match_at),
                    "last_match_at": _iso(item.last_match_at),
                },
                "time_range": {
                    "start": _iso(item.first_match_at),
                    "end": _iso(item.last_match_at),
                },
                "top_maps": [
                    {"map_name": name, "matches_count": count}
                    for name, count in item.top_maps
                ],
            },
        }
        self._cache.put(key, result, ttl_seconds=300)
        return result

    def ranking(
        self,
        *,
        server_id: str | None,
        timeframe: str,
        metric: str,
        limit: int,
        year: int | None = None,
        offset: int = 0,
    ) -> dict[str, object]:
        resolved = self._resolve(server_id)
        if isinstance(resolved, dict):
            return resolved
        targets, scopes = resolved
        gate = self._schema_gate()
        if gate is not None:
            return gate
        window = build_window(timeframe, now=self._now(), year=year)
        key = (
            "ranking", scopes[0].game, tuple(scope.server_number for scope in scopes),
            window.timeframe, window.start, window.end, metric, limit, offset,
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        try:
            rows = self._repository.list_rankings(
                scopes=scopes,
                started_at=window.start,
                ended_at=window.end,
                metric=metric,
                limit=limit,
                offset=offset,
            )
        except (CrconDatabaseError, ValueError) as error:
            if isinstance(error, ValueError):
                raise
            return self._state(CrconAggregateState.UNAVAILABLE, "database-read-failed")
        items = [_ranking_item(row) for row in rows]
        result = {
            **self._state(CrconAggregateState.AVAILABLE),
            "server_id": targets[0].key if len(targets) == 1 else "all-servers",
            "server_slug": targets[0].key if len(targets) == 1 else "all-servers",
            "timeframe": window.timeframe,
            "metric": metric,
            "limit": limit,
            "requested_limit": limit,
            "effective_limit": limit,
            "item_count": len(items),
            "source_matches_count": rows[0].source_matches_count if rows else 0,
            "window_start": _iso(window.start),
            "window_end": _iso(window.end),
            "window_kind": f"crcon-{window.timeframe}",
            "window_label": window.label,
            "generated_at": _iso(self._now()),
            "snapshot_status": "ready",
            "found": bool(items),
            "items": items,
        }
        self._cache.put(key, result)
        return result

    def player_profile(
        self, *, player_id: str, server_id: str | None, timeframe: str
    ) -> dict[str, object]:
        resolved = self._resolve(server_id)
        if isinstance(resolved, dict):
            return {**resolved, "player_id": player_id}
        targets, scopes = resolved
        gate = self._schema_gate()
        if gate is not None:
            return {**gate, "player_id": player_id}
        window = build_window(timeframe, now=self._now())
        key = (
            "profile", scopes[0].game, tuple(scope.server_number for scope in scopes),
            player_id, window.timeframe, window.start, window.end,
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        try:
            item = self._repository.get_player_profile_aggregate(
                player_id=player_id,
                scopes=scopes,
                started_at=window.start,
                ended_at=window.end,
            )
        except CrconDatabaseError:
            return {
                **self._state(CrconAggregateState.UNAVAILABLE, "database-read-failed"),
                "player_id": player_id,
            }
        if item is None:
            return {
                **self._state(CrconAggregateState.AVAILABLE),
                "player_id": player_id,
                "player_name": None,
                "matches_considered": 0,
                "timeframe": timeframe,
                "window_start": _iso(window.start),
                "window_end": _iso(window.end),
            }
        matches = item.matches_played
        kills = item.kills
        deaths = item.deaths
        identity_fields = build_external_player_profile_fields(
            steam_id=item.steam_id,
            eos_id=item.eos_id,
            platform=item.platform,
        )
        ranking = (
            {"ranking_position": item.kills_ranking_position, "metric": "kills"}
            if item.kills_ranking_position is not None
            else None
        )
        result = {
            **self._state(CrconAggregateState.AVAILABLE),
            "player_id": item.player_id,
            "player_name": item.player_name,
            "platform": identity_fields.get("platform"),
            "steam_id_64": identity_fields.get("steam_id_64"),
            "epic_id": identity_fields.get("epic_id"),
            "external_profile_links": identity_fields.get("external_profile_links") or {},
            "server_id": targets[0].key if len(targets) == 1 else None,
            "timeframe": timeframe,
            "window_start": _iso(window.start),
            "window_end": _iso(window.end),
            "window_kind": f"crcon-{timeframe}",
            "matches_considered": matches,
            "record_kills": item.record_kills,
            "kills": kills,
            "deaths": deaths,
            "teamkills": item.teamkills,
            "deaths_by_teamkill": item.deaths_by_teamkill,
            "combat": item.combat,
            "offense": item.offense,
            "defense": item.defense,
            "support": item.support,
            "vehicle_kills": item.vehicle_kills,
            "vehicles_destroyed": item.vehicles_destroyed,
            "kd_ratio": round(kills / deaths, 2) if deaths else float(kills),
            "kills_per_match": round(kills / matches, 2) if matches else 0.0,
            "deaths_per_match": round(deaths / matches, 2) if matches else 0.0,
            "player_active_seconds": item.time_seconds,
            "player_active_minutes": round(item.time_seconds / 60, 2),
            "kpm": round(kills * 60 / item.time_seconds, 2) if item.time_seconds else None,
            "kpm_status": "ready" if item.time_seconds else "unavailable",
            "active_time_source": "crcon-player-stats-time-seconds",
            "active_time_coverage": "complete" if item.time_seconds else "unavailable",
            "weekly_ranking": ranking if timeframe == "weekly" else None,
            "monthly_ranking": ranking if timeframe == "monthly" else None,
            "last_seen_at": _iso(item.last_seen_at),
            "servers_seen": self._server_keys(item.servers_seen),
        }
        self._cache.put(key, result)
        return result

    def _schema_gate(self) -> dict[str, object] | None:
        if not self._repository.configured:
            return self._state(CrconAggregateState.UNVERIFIED_SCHEMA, "database-url-not-configured")
        try:
            report = self._repository.probe_capabilities()
        except CrconDatabaseError:
            return self._state(CrconAggregateState.UNAVAILABLE, "schema-probe-failed")
        required = (
            CrconCapability.HISTORICAL_PLAYER_STATS,
            CrconCapability.PLAYER_AGGREGATES,
            CrconCapability.PLAYER_IDENTITIES,
        )
        if any(
            report.get(capability).status is not CrconCapabilityStatus.SUPPORTED
            for capability in required
        ):
            return self._state(CrconAggregateState.UNVERIFIED_SCHEMA, "required-schema-not-verified")
        return None

    def _resolve(
        self, server_id: str | None
    ) -> tuple[tuple[ServerTarget, ...], tuple[CrconServerScope, ...]] | dict[str, object]:
        normalized = str(server_id or "").strip().lower()
        if normalized in ALL_SERVER_KEYS:
            targets = self._targets
        else:
            targets = tuple(target for target in self._targets if target.key == normalized)
        if not targets:
            return self._state(CrconAggregateState.UNVERIFIED_SCHEMA, "server-target-not-configured")
        if len({target.game for target in targets}) != 1:
            return self._state(CrconAggregateState.UNAVAILABLE, "cross-game-aggregate-rejected")
        return targets, tuple(resolve_server_scope(target) for target in targets)

    def _server_keys(self, server_numbers: tuple[int, ...]) -> list[str]:
        lookup = {target.server_number: target.key for target in self._targets}
        return [lookup[number] for number in server_numbers if number in lookup]

    @staticmethod
    def _state(state: CrconAggregateState, reason: str | None = None) -> dict[str, object]:
        return {
            "source": "crcon-postgres-read-only",
            "aggregate_state": state.value,
            "state_reason": reason,
        }


def build_window(
    timeframe: str, *, now: datetime, year: int | None = None
) -> AggregateWindow:
    normalized = str(timeframe or "").strip().lower()
    current = now.astimezone(timezone.utc)
    if normalized == "weekly":
        start = current.replace(hour=0, minute=0, second=0, microsecond=0)
        start = start - timedelta(days=start.weekday())
        return AggregateWindow("weekly", start, current, "Semana actual")
    if normalized == "monthly":
        start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return AggregateWindow("monthly", start, current, "Mes actual")
    if normalized == "annual":
        selected_year = int(year or current.year)
        if selected_year < 2000 or selected_year > 2100:
            raise ValueError("Invalid annual ranking year.")
        start = datetime(selected_year, 1, 1, tzinfo=timezone.utc)
        end = datetime(selected_year + 1, 1, 1, tzinfo=timezone.utc)
        return AggregateWindow("annual", start, end, str(selected_year))
    if normalized in {"all", "alltime", "all-time"}:
        return AggregateWindow("alltime", None, None, "Todo el histórico")
    raise ValueError("Unsupported CRCON aggregate timeframe.")


def _ranking_item(row: object) -> dict[str, object]:
    matches = int(getattr(row, "matches_played"))
    kills = int(getattr(row, "kills"))
    deaths = int(getattr(row, "deaths"))
    return {
        "ranking_position": int(getattr(row, "ranking_position")),
        "player_id": str(getattr(row, "player_id")),
        "player_name": str(getattr(row, "player_name")),
        "metric_value": float(getattr(row, "metric_value")),
        "matches_considered": matches,
        "record_kills": int(getattr(row, "record_kills")),
        "kills": kills,
        "deaths": deaths,
        "teamkills": int(getattr(row, "teamkills")),
        "kd_ratio": round(kills / deaths, 2) if deaths else float(kills),
        "kills_per_match": round(kills / matches, 2) if matches else 0.0,
        "time_seconds": int(getattr(row, "time_seconds")),
        "combat": int(getattr(row, "combat")),
        "offense": int(getattr(row, "offense")),
        "defense": int(getattr(row, "defense")),
        "support": int(getattr(row, "support")),
        "vehicle_kills": int(getattr(row, "vehicle_kills")),
        "vehicles_destroyed": int(getattr(row, "vehicles_destroyed")),
        "matches_over_100_kills": int(getattr(row, "matches_over_100_kills")),
    }


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if value is not None else None


_runtime_lock = RLock()
_runtime_signature: tuple[object, ...] | None = None
_runtime_service: HistoricalAggregateService | None = None


def get_historical_aggregate_service() -> HistoricalAggregateService:
    """Reuse the pool until canonical aggregate configuration changes."""
    global _runtime_signature, _runtime_service
    dsn = get_crcon_database_url()
    targets = load_server_targets().all()
    signature = (
        sha256(dsn.encode("utf-8")).hexdigest() if dsn else None,
        tuple((target.key, target.server_number, target.game, target.enabled) for target in targets),
        get_crcon_database_connect_timeout_seconds(),
        get_crcon_database_statement_timeout_ms(),
        get_crcon_database_lock_timeout_ms(),
        get_crcon_database_pool_size(),
    )
    with _runtime_lock:
        if _runtime_service is None or signature != _runtime_signature:
            if _runtime_service is not None:
                _runtime_service._repository.close()
            repository = PostgresCrconRepository(
                dsn=dsn,
                connect_timeout_seconds=signature[2],
                statement_timeout_ms=signature[3],
                lock_timeout_ms=signature[4],
                pool_size=signature[5],
            )
            _runtime_service = HistoricalAggregateService(
                repository=repository, targets=targets
            )
            _runtime_signature = signature
        return _runtime_service


def _close_runtime_service() -> None:
    with _runtime_lock:
        if _runtime_service is not None:
            _runtime_service._repository.close()


atexit.register(_close_runtime_service)
