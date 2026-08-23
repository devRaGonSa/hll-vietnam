"""Coherent HLL-owned current-match domain and CRCON-first snapshot service."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from threading import Event, Lock
from typing import Any, TypeVar

from ..config import (
    get_crcon_api_timeout_seconds,
    get_crcon_current_match_bindings,
    get_crcon_log_stream_tokens,
    get_current_match_source,
)
from ..crcon import CrconApiClient, TtlCache
from ..crcon.repository import (
    CrconCurrentMap,
    CrconMatchCombatStats,
    CrconMatchLogEvent,
    CrconReadRepository,
    resolve_server_scope,
)
from ..crcon.dto import CrconLiveGameStats, CrconPublicInfo
from ..crcon.log_stream import (
    CrconCurrentMatchEvent,
    CrconLogStreamManager,
    CrconLogStreamStatus,
    CrconLogStreamTarget,
    CrconLogStreamWindow,
)
from ..normalizers import normalize_map_name
from ..scoreboard_origins import get_trusted_public_scoreboard_origin
from ..server_targets import ServerTarget


CURRENT_MATCH_CACHE_TTL_SECONDS = 1.5
CURRENT_MATCH_CACHE_MAX_ENTRIES = 8
CURRENT_MATCH_EVENT_LIMIT = 500
CURRENT_MATCH_MAP_START_TOLERANCE_SECONDS = 180


class MatchIdentityKind(StrEnum):
    CANONICAL = "canonical"
    EPHEMERAL = "ephemeral"


class CurrentMatchSourceStatus(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class CurrentMatchUnavailableError(RuntimeError):
    """Raised when a CRCON snapshot has no trustworthy current-match identity."""


class CurrentMatchCursorError(ValueError):
    """Raised when an opaque cursor is malformed or belongs to another match."""


@dataclass(frozen=True, slots=True)
class CrconCurrentMatchBinding:
    target: ServerTarget
    database_url: str | None
    api_headers: Mapping[str, str]
    log_server: str | None = None
    log_game: int | None = None

    @property
    def server_slug(self) -> str:
        return self.target.key

    @property
    def server_name(self) -> str:
        return self.target.display_name

    @property
    def api_base_url(self) -> str:
        return self.target.crcon_base_url

    @property
    def server_number(self) -> int:
        return self.target.server_number

    @property
    def capabilities(self) -> frozenset[str]:
        return self.target.capabilities


@dataclass(frozen=True, slots=True)
class CurrentMatchSourceState:
    source: str
    status: CurrentMatchSourceStatus
    observed_at: datetime
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "status": self.status.value,
            "observed_at": _iso(self.observed_at),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class CurrentMatchSummary:
    server_slug: str
    server_name: str
    map_name: str | None
    layer: str | None
    mode: str | None
    started_at: datetime
    allied_score: int | None
    axis_score: int | None
    remaining_seconds: int | None
    player_count: int | None
    max_player_count: int | None
    allied_count: int | None
    axis_count: int | None


@dataclass(frozen=True, slots=True)
class CurrentPlayer:
    player_id: str | None
    name: str
    team: str | None
    unit: str | None
    role: str | None
    level: int | None
    status: str | None
    combat: int | None
    offense: int | None
    defense: int | None
    support: int | None
    kills: int | None
    deaths: int | None
    teamkills: int | None
    deaths_by_teamkill: int | None
    favorite_weapon: str | None
    weapon_counts: tuple[tuple[str, int], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "team": self.team,
            "unit": self.unit,
            "role": self.role,
            "level": self.level,
            "status": self.status,
            "combat": self.combat,
            "offense": self.offense,
            "defense": self.defense,
            "support": self.support,
            "kills": self.kills,
            "deaths": self.deaths,
            "teamkills": self.teamkills,
            "deaths_by_teamkill": self.deaths_by_teamkill,
            "favorite_weapon": self.favorite_weapon,
            "weapon_counts": dict(self.weapon_counts),
        }


@dataclass(frozen=True, slots=True)
class KillEvent:
    cursor: str
    timestamp: datetime
    position_id: int
    killer_id: str | None
    killer_name: str | None
    killer_team: str | None
    victim_id: str | None
    victim_name: str | None
    victim_team: str | None
    weapon: str | None
    teamkill: bool
    match_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "cursor": self.cursor,
            "timestamp": _iso(self.timestamp),
            "killer": {
                "id": self.killer_id,
                "name": self.killer_name,
                "team": self.killer_team,
            },
            "victim": {
                "id": self.victim_id,
                "name": self.victim_name,
                "team": self.victim_team,
            },
            "weapon": self.weapon,
            "teamkill": self.teamkill,
            "match_id": self.match_id,
        }


@dataclass(frozen=True, slots=True)
class CurrentMatchKillfeedState:
    source: str
    status: str
    available: bool
    degraded: bool
    gap_detected: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "status": self.status,
            "available": self.available,
            "degraded": self.degraded,
            "gap_detected": self.gap_detected,
        }


@dataclass(frozen=True, slots=True)
class CurrentMatchSnapshot:
    server_slug: str
    match_id: str
    identity_kind: MatchIdentityKind
    summary: CurrentMatchSummary
    players: tuple[CurrentPlayer, ...]
    kills: tuple[KillEvent, ...]
    killfeed_truncated: bool
    version: str
    observed_at: datetime
    source_states: tuple[CurrentMatchSourceState, ...]
    degraded: bool
    degraded_reasons: tuple[str, ...]
    killfeed_state: CurrentMatchKillfeedState | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "server": self.server_slug,
            "server_slug": self.server_slug,
            "match_id": self.match_id,
            "identity_kind": self.identity_kind.value,
            "map": self.summary.map_name,
            "layer": self.summary.layer,
            "mode": self.summary.mode,
            "started_at": _iso(self.summary.started_at),
            "score": {
                "allied": self.summary.allied_score,
                "axis": self.summary.axis_score,
            },
            "remaining_seconds": self.summary.remaining_seconds,
            "player_count": self.summary.player_count,
            "max_player_count": self.summary.max_player_count,
            "allied_count": self.summary.allied_count,
            "axis_count": self.summary.axis_count,
            "players": [player.to_dict() for player in self.players],
            "kills": [event.to_dict() for event in self.kills],
            "killfeed_truncated": self.killfeed_truncated,
            "killfeed": (
                self.killfeed_state.to_dict()
                if self.killfeed_state is not None
                else None
            ),
            "version": self.version,
            "observed_at": _iso(self.observed_at),
            "sources": [state.to_dict() for state in self.source_states],
            "degraded": self.degraded,
            "degraded_reasons": list(self.degraded_reasons),
        }


ApiFactory = Callable[[CrconCurrentMatchBinding], Any]
DatabaseFactory = Callable[[CrconCurrentMatchBinding], CrconReadRepository]
Clock = Callable[[], datetime]
Result = TypeVar("Result")


@dataclass(slots=True)
class _Flight:
    event: Event
    result: object | None = None
    error: BaseException | None = None


class _SingleFlight:
    """Small per-key single-flight primitive; it never creates a background thread."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._flights: dict[str, _Flight] = {}

    def run(self, key: str, refresh: Callable[[], Result]) -> Result:
        with self._lock:
            flight = self._flights.get(key)
            leader = flight is None
            if leader:
                flight = _Flight(event=Event())
                self._flights[key] = flight
        assert flight is not None

        if leader:
            try:
                flight.result = refresh()
            except BaseException as error:
                flight.error = error
            finally:
                with self._lock:
                    self._flights.pop(key, None)
                flight.event.set()
        else:
            flight.event.wait()

        if flight.error is not None:
            raise flight.error
        return flight.result  # type: ignore[return-value]


class CurrentMatchSnapshotService:
    """Build one coherent request/cache-driven current-match snapshot per server."""

    def __init__(
        self,
        *,
        bindings: Mapping[str, CrconCurrentMatchBinding],
        api_factory: ApiFactory,
        database_factory: DatabaseFactory | None = None,
        cache: TtlCache[str, CurrentMatchSnapshot] | None = None,
        now: Clock = lambda: datetime.now(UTC),
        event_limit: int = CURRENT_MATCH_EVENT_LIMIT,
        log_stream_manager: CrconLogStreamManager | None = None,
    ) -> None:
        if event_limit < 1 or event_limit > CURRENT_MATCH_EVENT_LIMIT:
            raise ValueError("event_limit must be between one and 500.")
        self._bindings = dict(bindings)
        self._api_factory = api_factory
        self._database_factory = database_factory
        self._cache = (
            cache
            if cache is not None
            else TtlCache(
                max_entries=CURRENT_MATCH_CACHE_MAX_ENTRIES,
                ttl_seconds=CURRENT_MATCH_CACHE_TTL_SECONDS,
            )
        )
        self._now = now
        self._event_limit = event_limit
        self._log_stream_manager = log_stream_manager
        self._single_flight = _SingleFlight()
        self._identity_lock = Lock()
        self._last_match_by_server: dict[str, str] = {}
        self._last_good_by_server: dict[str, CurrentMatchSnapshot] = {}

    def get_snapshot(self, server_slug: str) -> CurrentMatchSnapshot:
        binding = self._bindings.get(str(server_slug or "").strip())
        if binding is None:
            raise CurrentMatchUnavailableError(
                "CRCON current match is not configured for this server."
            )
        cached = self._cache.get(binding.server_slug)
        if cached is not None:
            return cached
        try:
            return self._single_flight.run(
                binding.server_slug,
                lambda: self._refresh_and_cache(binding),
            )
        except Exception:
            with self._identity_lock:
                last_good = self._last_good_by_server.get(binding.server_slug)
            if last_good is None:
                raise
            observed_at = _ensure_utc(self._now())
            stale_state = CurrentMatchSourceState(
                source="crcon-api-last-good",
                status=CurrentMatchSourceStatus.STALE,
                observed_at=observed_at,
                reason="crcon-live-refresh-unavailable",
            )
            stale = replace(
                last_good,
                observed_at=observed_at,
                source_states=last_good.source_states + (stale_state,),
                degraded=True,
                degraded_reasons=tuple(
                    dict.fromkeys(
                        last_good.degraded_reasons + ("crcon-live-last-good-stale",)
                    )
                ),
            )
            stale = replace(stale, version=_snapshot_version(stale))
            self._cache.put(binding.server_slug, stale)
            return stale

    def project_kills(
        self,
        snapshot: CurrentMatchSnapshot,
        *,
        since_cursor: str | None,
        limit: int,
    ) -> tuple[KillEvent, ...]:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between one and 100.")
        if since_cursor:
            for index, event in enumerate(snapshot.kills):
                if event.cursor == since_cursor:
                    return snapshot.kills[index + 1 : index + 1 + limit]
            if since_cursor.startswith("kc2."):
                cursor_match, _stream_id = decode_stream_kill_cursor(since_cursor)
                if cursor_match != snapshot.match_id:
                    raise CurrentMatchCursorError(
                        "Kill cursor belongs to a different current match."
                    )
                raise CurrentMatchCursorError(
                    "Kill cursor predates the retained current-match feed window."
                )
            cursor_match, cursor_time, cursor_id = decode_kill_cursor(since_cursor)
            if cursor_match != snapshot.match_id:
                raise CurrentMatchCursorError(
                    "Kill cursor belongs to a different current match."
                )
            cursor_position = (cursor_time, cursor_id)
            if snapshot.killfeed_truncated and (
                not snapshot.kills
                or cursor_position
                < (snapshot.kills[0].timestamp, snapshot.kills[0].position_id)
            ):
                raise CurrentMatchCursorError(
                    "Kill cursor predates the retained current-match feed window."
                )
            return tuple(
                event
                for event in snapshot.kills
                if (event.timestamp, event.position_id) > cursor_position
            )[:limit]
        return snapshot.kills[-limit:]

    def _refresh_and_cache(
        self,
        binding: CrconCurrentMatchBinding,
    ) -> CurrentMatchSnapshot:
        cached = self._cache.get(binding.server_slug)
        if cached is not None:
            return cached
        snapshot = self._refresh(binding)
        with self._identity_lock:
            previous_match = self._last_match_by_server.get(binding.server_slug)
            if previous_match is not None and previous_match != snapshot.match_id:
                self._cache.invalidate(binding.server_slug)
            self._last_match_by_server[binding.server_slug] = snapshot.match_id
            self._last_good_by_server[binding.server_slug] = snapshot
        self._cache.put(binding.server_slug, snapshot)
        return snapshot

    def _refresh(self, binding: CrconCurrentMatchBinding) -> CurrentMatchSnapshot:
        observed_at = _ensure_utc(self._now())
        public_info: CrconPublicInfo | Mapping[str, object] | None = None
        live_stats: CrconLiveGameStats | Mapping[str, object] | None = None
        api_reasons: list[str] = []

        if "live_state" in binding.capabilities:
            try:
                api = self._api_factory(binding)
                try:
                    public_info = api.get_public_info()
                except Exception:
                    api_reasons.append("crcon-api-public-info-unavailable")
                try:
                    live_stats = api.get_live_game_stats()
                except Exception:
                    api_reasons.append("crcon-api-live-stats-unavailable")
            except Exception:
                api_reasons.extend(
                    [
                        "crcon-api-public-info-unavailable",
                        "crcon-api-live-stats-unavailable",
                    ]
                )
        else:
            api_reasons.append("crcon-api-live-state-disabled")

        api_state = _api_source_state(public_info, live_stats, api_reasons, observed_at)
        public = _parse_public_info(public_info)
        current_map: CrconCurrentMap | None = None
        event_rows: tuple[CrconMatchLogEvent, ...] = ()
        combat_rows: tuple[CrconMatchCombatStats, ...] = ()
        map_query_available = False
        feed_available = False
        combat_available = False
        database_reasons: list[str] = []
        database = None

        database_capabilities = {"historical_maps", "event_logs"} & binding.capabilities
        if database_capabilities:
            if self._database_factory is None:
                database_reasons.append("crcon-database-unavailable")
            else:
                try:
                    database = self._database_factory(binding)
                except Exception:
                    database_reasons.append("crcon-database-unavailable")
            if database is not None and "historical_maps" in binding.capabilities:
                try:
                    current_map = database.find_current_map(
                        server_number=binding.server_number,
                        map_name=public.layer,
                        started_at=public.started_at,
                        tolerance_seconds=CURRENT_MATCH_MAP_START_TOLERANCE_SECONDS,
                    )
                    map_query_available = True
                except Exception:
                    database_reasons.append("crcon-map-history-unavailable")
        if current_map is not None:
            match_id = _canonical_match_id(current_map.id)
            identity_kind = MatchIdentityKind.CANONICAL
            started_at = _ensure_utc(current_map.start)
            layer = public.layer or current_map.map_name
        elif public.layer and public.started_at is not None:
            match_id = _ephemeral_match_id(
                binding.server_slug,
                public.started_at,
                public.layer,
            )
            identity_kind = MatchIdentityKind.EPHEMERAL
            started_at = public.started_at
            layer = public.layer
            if map_query_available:
                database_reasons.append("crcon-map-identity-pending")
        else:
            raise CurrentMatchUnavailableError(
                "CRCON current match is unavailable for this server."
            )

        if (
            self._log_stream_manager is None
            and database is not None
            and "event_logs" in binding.capabilities
        ):
            scope = resolve_server_scope(
                binding.target,
                log_server=binding.log_server,
                log_game=binding.log_game,
            )
            try:
                queried_events = database.list_match_log_events(
                    scope=scope,
                    started_at=started_at,
                    ended_at=observed_at,
                    limit=self._event_limit,
                )
                event_rows = tuple(
                    event
                    for event in queried_events
                    if started_at <= _ensure_utc(event.event_time) <= observed_at
                )
                feed_available = True
            except Exception:
                database_reasons.append("crcon-event-feed-unavailable")
            try:
                combat_rows = database.aggregate_match_combat_stats(
                    scope=scope,
                    started_at=started_at,
                    ended_at=observed_at,
                )
                combat_available = True
            except Exception:
                database_reasons.append("crcon-combat-aggregate-unavailable")
        elif self._log_stream_manager is None and "event_logs" not in binding.capabilities:
            feed_available = False

        live_rows = _live_stat_rows(live_stats)
        team_index = _build_live_team_index(live_rows)
        stream_window: CrconLogStreamWindow | None = None
        if self._log_stream_manager is not None:
            stream_window = self._log_stream_manager.window_for_match(
                binding.server_slug,
                match_id,
                started_at,
            )
            kill_events = _build_stream_kill_events(
                stream_window.events,
                match_id=match_id,
                team_index=team_index,
            )
            feed_available = stream_window.status == CrconLogStreamStatus.AVAILABLE
        else:
            kill_events = _build_kill_events(
                event_rows,
                match_id=match_id,
                team_index=team_index,
            )
        players, disagreement = _build_players(
            live_rows,
            combat_rows,
            combat_available=combat_available,
            live_combat_canonical=not database_capabilities,
        )
        total_combat_events = sum(
            max(0, row.kills) + max(0, row.teamkills) for row in combat_rows
        )
        killfeed_truncated = (
            combat_available and total_combat_events > len(kill_events)
        ) or (
            not combat_available
            and feed_available
            and len(event_rows) >= self._event_limit
        )
        if stream_window is not None:
            killfeed_truncated = stream_window.truncated

        degraded_reasons = list(dict.fromkeys(api_reasons + database_reasons))
        killfeed_state: CurrentMatchKillfeedState | None = None
        if stream_window is not None:
            stream_reason = _log_stream_degraded_reason(stream_window)
            if stream_reason is not None:
                degraded_reasons.append(stream_reason)
            killfeed_state = CurrentMatchKillfeedState(
                source="crcon-log-stream",
                status=stream_window.status.value,
                available=feed_available,
                degraded=not feed_available or stream_window.gap_detected,
                gap_detected=stream_window.gap_detected,
            )
        if disagreement:
            degraded_reasons.append("crcon-api-log-combat-disagreement")
        degraded_reasons = list(dict.fromkeys(degraded_reasons))

        summary = CurrentMatchSummary(
            server_slug=binding.server_slug,
            server_name=public.server_name or binding.server_name,
            map_name=normalize_map_name(public.map_name or layer),
            layer=layer,
            mode=public.mode,
            started_at=started_at,
            allied_score=public.allied_score,
            axis_score=public.axis_score,
            remaining_seconds=public.remaining_seconds,
            player_count=public.player_count,
            max_player_count=public.max_player_count,
            allied_count=public.allied_count,
            axis_count=public.axis_count,
        )
        source_states = (api_state,)
        if stream_window is not None:
            source_states += (
                CurrentMatchSourceState(
                    source="crcon-log-stream",
                    status=(
                        CurrentMatchSourceStatus.FRESH
                        if feed_available and not stream_window.gap_detected
                        else CurrentMatchSourceStatus.DEGRADED
                        if feed_available or bool(stream_window.events)
                        else CurrentMatchSourceStatus.UNAVAILABLE
                    ),
                    observed_at=observed_at,
                    reason=_log_stream_degraded_reason(stream_window),
                ),
            )
        if database_capabilities:
            database_reason = database_reasons[0] if database_reasons else None
            source_states += (
                CurrentMatchSourceState(
                    source="crcon-database",
                    status=(
                        CurrentMatchSourceStatus.FRESH
                        if current_map is not None and feed_available and combat_available
                        else CurrentMatchSourceStatus.DEGRADED
                        if map_query_available or feed_available or combat_available
                        else CurrentMatchSourceStatus.UNAVAILABLE
                    ),
                    observed_at=observed_at,
                    reason=database_reason,
                ),
            )
        snapshot = CurrentMatchSnapshot(
            server_slug=binding.server_slug,
            match_id=match_id,
            identity_kind=identity_kind,
            summary=summary,
            players=players,
            kills=kill_events,
            killfeed_truncated=killfeed_truncated,
            version="",
            observed_at=observed_at,
            source_states=source_states,
            degraded=bool(degraded_reasons),
            degraded_reasons=tuple(degraded_reasons),
            killfeed_state=killfeed_state,
        )
        return replace(snapshot, version=_snapshot_version(snapshot))


@dataclass(frozen=True, slots=True)
class _PublicState:
    layer: str | None = None
    map_name: str | None = None
    mode: str | None = None
    started_at: datetime | None = None
    allied_score: int | None = None
    axis_score: int | None = None
    remaining_seconds: int | None = None
    player_count: int | None = None
    max_player_count: int | None = None
    allied_count: int | None = None
    axis_count: int | None = None
    server_name: str | None = None


def encode_kill_cursor(match_id: str, timestamp: datetime, event_id: int) -> str:
    payload = json.dumps(
        {"i": event_id, "m": match_id, "t": _iso(timestamp)},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return f"kc1.{encoded}"


def decode_kill_cursor(cursor: str) -> tuple[str, datetime, int]:
    candidate = str(cursor or "").strip()
    if not candidate.startswith("kc1."):
        raise CurrentMatchCursorError("Kill cursor is invalid.")
    encoded = candidate.removeprefix("kc1.")
    try:
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding))
        match_id = str(payload["m"])
        timestamp = _parse_datetime(payload["t"])
        event_id = int(payload["i"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, binascii.Error):
        raise CurrentMatchCursorError("Kill cursor is invalid.") from None
    if not match_id or timestamp is None or event_id < 0:
        raise CurrentMatchCursorError("Kill cursor is invalid.")
    return match_id, timestamp, event_id


def encode_stream_kill_cursor(match_id: str, stream_id: str) -> str:
    payload = json.dumps(
        {"m": match_id, "s": stream_id},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return f"kc2.{encoded}"


def decode_stream_kill_cursor(cursor: str) -> tuple[str, str]:
    candidate = str(cursor or "").strip()
    if not candidate.startswith("kc2."):
        raise CurrentMatchCursorError("Kill cursor is invalid.")
    encoded = candidate.removeprefix("kc2.")
    try:
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding))
        match_id = str(payload["m"]).strip()
        stream_id = str(payload["s"]).strip()
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, binascii.Error):
        raise CurrentMatchCursorError("Kill cursor is invalid.") from None
    if not match_id or not stream_id:
        raise CurrentMatchCursorError("Kill cursor is invalid.")
    return match_id, stream_id


def snapshot_payload(snapshot: CurrentMatchSnapshot) -> dict[str, object]:
    return {"status": "ok", "data": snapshot.to_dict()}


def legacy_summary_projection(snapshot: CurrentMatchSnapshot) -> dict[str, object]:
    summary = snapshot.summary
    trusted_origin = get_trusted_public_scoreboard_origin(snapshot.server_slug)
    return {
        "status": "ok",
        "data": {
            "found": True,
            "server_slug": snapshot.server_slug,
            "server_name": summary.server_name,
            "status": "degraded" if snapshot.degraded else "online",
            "map": summary.map_name,
            "map_id": summary.layer,
            "map_pretty_name": summary.map_name,
            "game_mode": summary.mode,
            "started_at": _iso(summary.started_at),
            "allied_score": summary.allied_score,
            "axis_score": summary.axis_score,
            "allied_players": summary.allied_count,
            "axis_players": summary.axis_count,
            "players": summary.player_count,
            "max_players": summary.max_player_count,
            "player_count_quality": "crcon-live" if summary.player_count is not None else None,
            "player_count_source": "crcon-api" if summary.player_count is not None else None,
            "score_source": "crcon-api" if summary.allied_score is not None else None,
            "map_source": "crcon-api",
            "match_time_seconds": None,
            "remaining_match_time_seconds": summary.remaining_seconds,
            "captured_at": _iso(snapshot.observed_at),
            "updated_at": _iso(snapshot.observed_at),
            "public_scoreboard_url": (
                trusted_origin.base_url if trusted_origin is not None else None
            ),
            "match_id": snapshot.match_id,
            "identity_kind": snapshot.identity_kind.value,
            "version": snapshot.version,
            "degraded": snapshot.degraded,
            "degraded_reasons": list(snapshot.degraded_reasons),
        },
    }


def legacy_kills_projection(
    snapshot: CurrentMatchSnapshot,
    events: Sequence[KillEvent],
) -> dict[str, object]:
    return {
        "status": "ok",
        "data": {
            "server_slug": snapshot.server_slug,
            "server_name": snapshot.summary.server_name,
            "primary_source": "crcon",
            "selected_source": "crcon-log-stream",
            "fallback_used": False,
            "fallback_reason": None,
            "source_attempts": [],
            "scope": snapshot.match_id,
            "confidence": "degraded" if snapshot.degraded else "fresh",
            "stale_events_filtered": 0,
            "truncated_before": snapshot.killfeed_truncated,
            "items": [
                {
                    "event_id": event.cursor,
                    "event_timestamp": _iso(event.timestamp),
                    "server_time": int(event.timestamp.timestamp()),
                    "killer_id": event.killer_id,
                    "killer_name": event.killer_name,
                    "killer_team": event.killer_team,
                    "victim_id": event.victim_id,
                    "victim_name": event.victim_name,
                    "victim_team": event.victim_team,
                    "weapon": event.weapon,
                    "is_teamkill": event.teamkill,
                    "match_id": event.match_id,
                }
                for event in events
            ],
            "version": snapshot.version,
            "degraded": snapshot.degraded,
        },
    }


def legacy_players_projection(snapshot: CurrentMatchSnapshot) -> dict[str, object]:
    return {
        "status": "ok",
        "data": {
            "server_slug": snapshot.server_slug,
            "server_name": snapshot.summary.server_name,
            "primary_source": "crcon",
            "selected_source": "crcon-live-game-stats",
            "fallback_used": False,
            "fallback_reason": None,
            "source_attempts": [],
            "scope": snapshot.match_id,
            "confidence": "degraded" if snapshot.degraded else "fresh",
            "source": "crcon-live-game-stats",
            "updated_at": _iso(snapshot.observed_at),
            "stale_events_filtered": 0,
            "items": [
                {
                    "player_id": player.player_id,
                    "player_name": player.name,
                    "team": player.team,
                    "kills": player.kills,
                    "deaths": player.deaths,
                    "teamkills": player.teamkills,
                    "deaths_by_teamkill": player.deaths_by_teamkill,
                    "favorite_weapon": player.favorite_weapon,
                    "combat": player.combat,
                    "offense": player.offense,
                    "defense": player.defense,
                    "support": player.support,
                    "unit": player.unit,
                    "role": player.role,
                    "level": player.level,
                    "status": player.status,
                    "last_seen_at": _iso(snapshot.observed_at),
                }
                for player in snapshot.players
            ],
            "version": snapshot.version,
            "degraded": snapshot.degraded,
            "degraded_reasons": list(snapshot.degraded_reasons),
        },
    }


_runtime_lock = Lock()
_runtime_fingerprint: str | None = None
_runtime_service: CurrentMatchSnapshotService | None = None
_runtime_log_stream_manager: CrconLogStreamManager | None = None
_runtime_log_streams_started = False


def get_current_match_snapshot_service() -> CurrentMatchSnapshotService:
    """Build or reuse one process-local service for the current environment."""
    binding_configs = get_crcon_current_match_bindings()
    stream_tokens = get_crcon_log_stream_tokens()
    fingerprint_payload = json.dumps(
        {
            "bindings": binding_configs,
            "log_stream_token_targets": sorted(stream_tokens),
        },
        default=str,
        separators=(",", ":"),
        sort_keys=True,
    )
    fingerprint = hashlib.sha256(fingerprint_payload.encode("utf-8")).hexdigest()
    global _runtime_fingerprint, _runtime_service, _runtime_log_stream_manager
    with _runtime_lock:
        if _runtime_service is not None and _runtime_fingerprint == fingerprint:
            return _runtime_service
        bindings = _build_bindings(
            binding_configs,
            shared_database_url=None,
            api_only=True,
        )
        timeout_seconds = get_crcon_api_timeout_seconds()
        if _runtime_log_stream_manager is not None and _runtime_log_streams_started:
            _runtime_log_stream_manager.stop()
        stream_targets = tuple(
            CrconLogStreamTarget(
                server_slug=slug,
                base_url=binding.api_base_url,
                bearer_token=stream_tokens[slug],
            )
            for slug, binding in bindings.items()
            if slug in stream_tokens
        )
        _runtime_log_stream_manager = CrconLogStreamManager(stream_targets)
        _runtime_service = CurrentMatchSnapshotService(
            bindings=bindings,
            api_factory=lambda binding: CrconApiClient(
                base_url=binding.api_base_url,
                timeout_seconds=timeout_seconds,
                headers=binding.api_headers,
            ),
            log_stream_manager=_runtime_log_stream_manager,
        )
        if _runtime_log_streams_started:
            _runtime_log_stream_manager.start()
        _runtime_fingerprint = fingerprint
        return _runtime_service


def start_current_match_log_streams() -> None:
    """Start CRCON consumers once when this process can exercise CRCON mode."""
    global _runtime_log_streams_started
    if get_current_match_source() not in {"crcon", "shadow"}:
        return
    service = get_current_match_snapshot_service()
    with _runtime_lock:
        _runtime_log_streams_started = True
        if service._log_stream_manager is not None:
            service._log_stream_manager.start()


def stop_current_match_log_streams() -> None:
    """Stop every process-local CRCON consumer during backend shutdown."""
    global _runtime_log_streams_started
    with _runtime_lock:
        _runtime_log_streams_started = False
        manager = _runtime_log_stream_manager
    if manager is not None:
        manager.stop()


def _build_bindings(
    configs: Sequence[Mapping[str, object]],
    *,
    shared_database_url: str | None,
    api_only: bool = False,
) -> dict[str, CrconCurrentMatchBinding]:
    bindings: dict[str, CrconCurrentMatchBinding] = {}
    for config in configs:
        slug = str(config["server_slug"])
        trusted = get_trusted_public_scoreboard_origin(slug)
        display_name = str(
            config.get("display_name")
            or (trusted.display_name if trusted is not None else slug)
        ).strip()
        target = ServerTarget(
            key=slug,
            display_name=display_name,
            crcon_base_url=str(config["api_base_url"]),
            server_number=int(config["server_number"]),
            game=str(config.get("game") or "hll"),  # type: ignore[arg-type]
            enabled=bool(config.get("enabled", True)),
            capabilities=(
                frozenset({"live_state"})
                if api_only
                else frozenset(config.get("capabilities") or ())
            ),
        )
        if not target.enabled:
            continue
        bindings[slug] = CrconCurrentMatchBinding(
            target=target,
            database_url=(
                None
                if api_only
                else str(
                    config.get("database_url") or shared_database_url or ""
                ).strip()
                or None
            ),
            api_headers=dict(config.get("api_headers") or {}),
            log_server=str(config.get("log_server") or "").strip() or None,
            log_game=(
                int(config["log_game"])
                if config.get("log_game") is not None
                else None
            ),
        )
    return bindings


def _parse_public_info(
    payload: CrconPublicInfo | Mapping[str, object] | None,
) -> _PublicState:
    if isinstance(payload, CrconPublicInfo):
        return _PublicState(
            layer=payload.current_map.layer,
            map_name=payload.current_map.map_name,
            mode=payload.current_map.mode,
            started_at=payload.current_map.started_at,
            allied_score=payload.score.allied,
            axis_score=payload.score.axis,
            remaining_seconds=payload.remaining_seconds,
            player_count=payload.player_count,
            max_player_count=payload.max_player_count,
            allied_count=payload.allied_count,
            axis_count=payload.axis_count,
            server_name=payload.server_name,
        )
    if not isinstance(payload, Mapping):
        return _PublicState()
    current_map = payload.get("current_map")
    map_payload = current_map if isinstance(current_map, Mapping) else {}
    raw_layer = map_payload.get("map")
    layer_payload = raw_layer if isinstance(raw_layer, Mapping) else {}
    layer = _text(
        layer_payload.get("id")
        or layer_payload.get("layer")
        or raw_layer
    )
    map_name = _text(layer_payload.get("map") or layer_payload.get("name") or layer)
    mode = _text(layer_payload.get("game_mode") or layer_payload.get("mode"))
    score = payload.get("score") if isinstance(payload.get("score"), Mapping) else {}
    team_counts = (
        payload.get("player_count_by_team")
        if isinstance(payload.get("player_count_by_team"), Mapping)
        else {}
    )
    name = payload.get("name") if isinstance(payload.get("name"), Mapping) else {}
    return _PublicState(
        layer=layer,
        map_name=map_name,
        mode=mode,
        started_at=_parse_datetime(map_payload.get("start")),
        allied_score=_integer(score.get("allied")),
        axis_score=_integer(score.get("axis")),
        remaining_seconds=_integer(payload.get("time_remaining")),
        player_count=_integer(payload.get("player_count")),
        max_player_count=_integer(payload.get("max_player_count")),
        allied_count=_integer(team_counts.get("allied")),
        axis_count=_integer(team_counts.get("axis")),
        server_name=_text(name.get("name") or name.get("short_name")),
    )


def _live_stat_rows(
    payload: CrconLiveGameStats | Mapping[str, object] | None,
) -> tuple[Mapping[str, object], ...]:
    if isinstance(payload, CrconLiveGameStats):
        return tuple(player.to_current_match_mapping() for player in payload.players)
    if not isinstance(payload, Mapping):
        return ()
    rows = payload.get("stats")
    if not isinstance(rows, list):
        return ()
    return tuple(row for row in rows if isinstance(row, Mapping))


def _build_live_team_index(
    rows: Sequence[Mapping[str, object]],
) -> dict[str, str | None]:
    teams: dict[str, str | None] = {}
    for row in rows:
        team = _team(row.get("team"))
        player_id = _text(row.get("player_id"))
        name = _text(row.get("player") or row.get("name"))
        if player_id:
            teams[f"id:{player_id}"] = team
        if name:
            teams[f"name:{name.casefold()}"] = team
    return teams


def _build_kill_events(
    rows: Sequence[CrconMatchLogEvent],
    *,
    match_id: str,
    team_index: Mapping[str, str | None],
) -> tuple[KillEvent, ...]:
    events: list[KillEvent] = []
    seen_ids: set[int] = set()
    for row in sorted(rows, key=lambda item: (_ensure_utc(item.event_time), item.id)):
        if row.id in seen_ids or row.type not in {"KILL", "TEAM KILL"}:
            continue
        seen_ids.add(row.id)
        timestamp = _ensure_utc(row.event_time)
        events.append(
            KillEvent(
                cursor=encode_kill_cursor(match_id, timestamp, row.id),
                timestamp=timestamp,
                position_id=row.id,
                killer_id=row.player1_id,
                killer_name=row.player1_name,
                killer_team=_indexed_team(team_index, row.player1_id, row.player1_name),
                victim_id=row.player2_id,
                victim_name=row.player2_name,
                victim_team=_indexed_team(team_index, row.player2_id, row.player2_name),
                weapon=row.weapon,
                teamkill=row.type == "TEAM KILL",
                match_id=match_id,
            )
        )
    return tuple(events)


def _build_stream_kill_events(
    rows: Sequence[CrconCurrentMatchEvent],
    *,
    match_id: str,
    team_index: Mapping[str, str | None],
) -> tuple[KillEvent, ...]:
    events: list[KillEvent] = []
    for row in rows:
        timestamp = _ensure_utc(row.timestamp)
        events.append(
            KillEvent(
                cursor=encode_stream_kill_cursor(match_id, row.event_id),
                timestamp=timestamp,
                position_id=_stream_position_id(row.event_id),
                killer_id=row.killer_id,
                killer_name=row.killer_name,
                killer_team=_indexed_team(
                    team_index,
                    row.killer_id,
                    row.killer_name,
                ),
                victim_id=row.victim_id,
                victim_name=row.victim_name,
                victim_team=_indexed_team(
                    team_index,
                    row.victim_id,
                    row.victim_name,
                ),
                weapon=row.weapon,
                teamkill=row.teamkill,
                match_id=match_id,
            )
        )
    return tuple(events)


def _stream_position_id(stream_id: str) -> int:
    try:
        milliseconds, sequence = stream_id.split("-", 1)
        return (int(milliseconds) << 32) + int(sequence)
    except (TypeError, ValueError):
        return int.from_bytes(
            hashlib.sha256(stream_id.encode("utf-8")).digest()[:16],
            "big",
        )


def _build_players(
    live_rows: Sequence[Mapping[str, object]],
    combat_rows: Sequence[CrconMatchCombatStats],
    *,
    combat_available: bool,
    live_combat_canonical: bool = False,
) -> tuple[tuple[CurrentPlayer, ...], bool]:
    builders: dict[str, dict[str, object]] = {}
    api_totals: dict[str, tuple[int | None, int | None, int | None]] = {}

    for row in live_rows:
        player_id = _text(row.get("player_id"))
        name = _text(row.get("player") or row.get("name")) or "Unknown player"
        key = _player_key(player_id, name)
        unit, role = _live_unit_role(row)
        builders[key] = {
            "player_id": player_id,
            "name": name,
            "team": _team(row.get("team")),
            "unit": unit,
            "role": role,
            "level": _integer(row.get("level")),
            "status": _text(row.get("status")),
            "combat": _integer(row.get("combat")),
            "offense": _integer(row.get("offense")),
            "defense": _integer(row.get("defense")),
            "support": _integer(row.get("support")),
            "kills": (
                _integer(row.get("kills"))
                if live_combat_canonical
                else 0 if combat_available else None
            ),
            "deaths": (
                _integer(row.get("deaths"))
                if live_combat_canonical
                else 0 if combat_available else None
            ),
            "teamkills": (
                _integer(row.get("teamkills"))
                if live_combat_canonical
                else 0 if combat_available else None
            ),
            "deaths_by_teamkill": (
                _integer(row.get("deaths_by_teamkill"))
                if live_combat_canonical
                else 0 if combat_available else None
            ),
            "weapons": (
                Counter(_count_mapping(row.get("weapons")))
                if live_combat_canonical
                else Counter()
            ),
        }
        api_totals[key] = (
            _integer(row.get("kills")),
            _integer(row.get("deaths")),
            _integer(row.get("teamkills")),
        )

    if combat_available:
        for stats in combat_rows:
            player = _ensure_player_builder(
                builders,
                stats.player_id,
                stats.player_name,
                combat_available=True,
            )
            player["kills"] = stats.kills
            player["deaths"] = stats.deaths
            player["teamkills"] = stats.teamkills
            player["deaths_by_teamkill"] = stats.deaths_by_teamkill
            player["weapons"] = Counter(dict(stats.weapon_counts))

    disagreement = False
    players: list[CurrentPlayer] = []
    for key, builder in builders.items():
        weapons = builder.pop("weapons")
        assert isinstance(weapons, Counter)
        weapon_counts = tuple(sorted(weapons.items()))
        favorite_weapon = (
            sorted(weapons.items(), key=lambda item: (-item[1], item[0]))[0][0]
            if weapons
            else None
        )
        api_values = api_totals.get(key)
        if combat_available and api_values is not None:
            canonical = (
                builder["kills"],
                builder["deaths"],
                builder["teamkills"],
            )
            disagreement = disagreement or any(
                api_value is not None and api_value != canonical_value
                for api_value, canonical_value in zip(api_values, canonical)
            )
        players.append(
            CurrentPlayer(
                **builder,  # type: ignore[arg-type]
                favorite_weapon=favorite_weapon,
                weapon_counts=weapon_counts,
            )
        )
    players.sort(
        key=lambda player: (
            player.status != "online",
            -(player.kills or 0),
            player.name.casefold(),
            player.player_id or "",
        )
    )
    return tuple(players), disagreement


def _ensure_player_builder(
    builders: dict[str, dict[str, object]],
    player_id: str | None,
    name: str | None,
    *,
    combat_available: bool,
) -> dict[str, object]:
    resolved_name = name or "Unknown player"
    key = _player_key(player_id, resolved_name)
    existing = builders.get(key)
    if existing is not None:
        return existing
    builder: dict[str, object] = {
        "player_id": player_id,
        "name": resolved_name,
        "team": None,
        "unit": None,
        "role": None,
        "level": None,
        "status": "offline",
        "combat": None,
        "offense": None,
        "defense": None,
        "support": None,
        "kills": 0 if combat_available else None,
        "deaths": 0 if combat_available else None,
        "teamkills": 0 if combat_available else None,
        "deaths_by_teamkill": 0 if combat_available else None,
        "weapons": Counter(),
    }
    builders[key] = builder
    return builder


def _live_unit_role(row: Mapping[str, object]) -> tuple[str | None, str | None]:
    unit = _text(row.get("unit"))
    role = _text(row.get("role"))
    units = row.get("units")
    if isinstance(units, list) and units:
        latest = units[-1]
        if isinstance(latest, Mapping):
            unit = unit or _text(latest.get("squad") or latest.get("unit"))
            role = role or _text(latest.get("role"))
    return unit, role


def _api_source_state(
    public_info: object,
    live_stats: object,
    reasons: Sequence[str],
    observed_at: datetime,
) -> CurrentMatchSourceState:
    if public_info is not None and live_stats is not None:
        status = CurrentMatchSourceStatus.FRESH
        reason = None
    elif public_info is not None or live_stats is not None:
        status = CurrentMatchSourceStatus.DEGRADED
        reason = reasons[0] if reasons else "crcon-api-partial"
    else:
        status = CurrentMatchSourceStatus.UNAVAILABLE
        reason = reasons[0] if reasons else "crcon-api-unavailable"
    return CurrentMatchSourceState(
        source="crcon-api",
        status=status,
        observed_at=observed_at,
        reason=reason,
    )


def _log_stream_degraded_reason(window: CrconLogStreamWindow) -> str | None:
    if window.gap_detected:
        return "crcon-log-stream-gap-detected"
    if window.status == CrconLogStreamStatus.AVAILABLE:
        return None
    if window.status == CrconLogStreamStatus.DISABLED:
        return "crcon-log-stream-disabled"
    if window.status == CrconLogStreamStatus.AUTH_FAILED:
        return "crcon-log-stream-auth-failed"
    return window.reason or "crcon-log-stream-unavailable"


def _canonical_match_id(map_id: int) -> str:
    encoded = base64.urlsafe_b64encode(str(map_id).encode("ascii")).decode("ascii")
    return f"cm1.{encoded.rstrip('=')}"


def _ephemeral_match_id(server_slug: str, started_at: datetime, layer: str) -> str:
    material = "\0".join((server_slug, _iso(started_at), layer.casefold()))
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    return f"em1.{digest}"


def _snapshot_version(snapshot: CurrentMatchSnapshot) -> str:
    newest_cursor = snapshot.kills[-1].cursor if snapshot.kills else None
    material = {
        "match_id": snapshot.match_id,
        "summary": {
            "map": snapshot.summary.map_name,
            "layer": snapshot.summary.layer,
            "mode": snapshot.summary.mode,
            "started_at": _iso(snapshot.summary.started_at),
            "score": [snapshot.summary.allied_score, snapshot.summary.axis_score],
            "players": [
                snapshot.summary.player_count,
                snapshot.summary.allied_count,
                snapshot.summary.axis_count,
            ],
        },
        "players": [player.to_dict() for player in snapshot.players],
        "newest_cursor": newest_cursor,
        "killfeed_truncated": snapshot.killfeed_truncated,
        "killfeed": (
            snapshot.killfeed_state.to_dict()
            if snapshot.killfeed_state is not None
            else None
        ),
        "sources": [
            [state.source, state.status.value, state.reason]
            for state in snapshot.source_states
        ],
        "degraded_reasons": snapshot.degraded_reasons,
    }
    encoded = json.dumps(material, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return f"sv1.{hashlib.sha256(encoded).hexdigest()[:24]}"


def _indexed_team(
    index: Mapping[str, str | None],
    player_id: str | None,
    name: str | None,
) -> str | None:
    if player_id and f"id:{player_id}" in index:
        return index[f"id:{player_id}"]
    if name:
        return index.get(f"name:{name.casefold()}")
    return None


def _player_key(player_id: str | None, name: str) -> str:
    return f"id:{player_id}" if player_id else f"name:{name.casefold()}"


def _team(value: object) -> str | None:
    normalized = _text(value)
    if normalized is None:
        return None
    folded = normalized.casefold()
    if folded in {"allies", "allied", "aliados"}:
        return "allies"
    if folded in {"axis", "eje"}:
        return "axis"
    return normalized


def _text(value: object) -> str | None:
    if value is None or isinstance(value, Mapping):
        return None
    normalized = str(value).strip()
    return normalized or None


def _integer(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _count_mapping(value: object) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    counts: dict[str, int] = {}
    for raw_name, raw_count in value.items():
        name = _text(raw_name)
        count = _integer(raw_count)
        if name is not None and count is not None:
            counts[name] = count
    return counts


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return _ensure_utc(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(float(value), UTC)
    if isinstance(value, str) and value.strip():
        try:
            return _ensure_utc(datetime.fromisoformat(value.strip().replace("Z", "+00:00")))
        except ValueError:
            return None
    return None


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso(value: datetime) -> str:
    return _ensure_utc(value).isoformat().replace("+00:00", "Z")
