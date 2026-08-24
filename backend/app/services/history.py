"""CRCON-backed historical match browsing with legacy-compatible serializers."""

from __future__ import annotations

import atexit
import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from ..config import (
    get_crcon_api_timeout_seconds,
    get_crcon_current_match_bindings,
    get_crcon_database_connect_timeout_seconds,
    get_crcon_database_lock_timeout_ms,
    get_crcon_database_pool_size,
    get_crcon_database_statement_timeout_ms,
    get_crcon_database_url,
)
from ..crcon.api import CrconApiClient
from ..crcon.cache import TtlCache
from ..crcon.dto import CrconHistoricalMap, CrconMapPage, CrconMapScoreboard
from ..crcon.models import CrconApiError, CrconDatabaseError, CrconUnavailableError
from ..crcon.postgres_repository import PostgresCrconRepository
from ..crcon.repository import (
    CrconExplicitPlayerIdentity,
    CrconHistoricalMatchLookup,
    CrconReadRepository,
    resolve_server_scope,
)
from ..player_external_profiles import build_external_player_profile_fields
from ..server_targets import ServerTarget, load_server_targets


ALL_SERVERS_SLUG = "all-servers"


MAX_PAGE_SIZE = 100
MAX_AGGREGATE_ROWS_PER_TARGET = 1000
LIST_CACHE_TTL_SECONDS = 30.0
DETAIL_CACHE_TTL_SECONDS = 3600.0


@dataclass(frozen=True, slots=True)
class HistoryBinding:
    target: ServerTarget
    api_headers: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class HistoricalMatchRecord:
    target: ServerTarget
    match: CrconHistoricalMap
    player_count: int | None = None
    player_count_status: str = "unknown-on-scoreboard-maps"


@dataclass(frozen=True, slots=True)
class HistoricalMatchPage:
    items: tuple[HistoricalMatchRecord, ...]
    page: int
    page_size: int
    total: int
    degraded_reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HistoricalMatchDetail:
    target: ServerTarget
    scoreboard: CrconMapScoreboard
    explicit_identities: Mapping[str, CrconExplicitPlayerIdentity] = field(
        default_factory=dict
    )
    degraded_reasons: tuple[str, ...] = ()


class HistoryTargetNotFoundError(LookupError):
    pass


class HistoryUnavailableError(RuntimeError):
    pass


class HistoryMatchNotFoundError(LookupError):
    pass


ApiFactory = Callable[[HistoryBinding], Any]


class HistoryService:
    """Bounded CRCON REST reader for recent maps and one selected map detail."""

    def __init__(
        self,
        *,
        bindings: Mapping[str, HistoryBinding],
        api_factory: ApiFactory,
        repository: CrconReadRepository | None = None,
        list_cache: TtlCache[tuple[str, int, int], HistoricalMatchPage] | None = None,
        detail_cache: TtlCache[tuple[str, str], HistoricalMatchDetail] | None = None,
    ) -> None:
        self._bindings = dict(bindings)
        self._api_factory = api_factory
        self._repository = repository
        self._list_cache = (
            list_cache
            if list_cache is not None
            else TtlCache(
                max_entries=64,
                ttl_seconds=LIST_CACHE_TTL_SECONDS,
            )
        )
        self._detail_cache = (
            detail_cache
            if detail_cache is not None
            else TtlCache(
                max_entries=256,
                ttl_seconds=DETAIL_CACHE_TTL_SECONDS,
            )
        )

    def list_recent_matches(
        self,
        *,
        server_slug: str | None,
        page: int = 1,
        page_size: int = 100,
    ) -> HistoricalMatchPage:
        resolved_page, resolved_size = _validate_pagination(page, page_size)
        scope = _normalize_scope(server_slug)
        cache_key = (scope, resolved_page, resolved_size)
        cached = self._list_cache.get(cache_key)
        if cached is not None:
            return cached

        bindings = self._resolve_list_bindings(scope)
        if len(bindings) == 1:
            result = self._read_single_target_page(
                bindings[0], page=resolved_page, page_size=resolved_size
            )
        else:
            result = self._read_aggregate_page(
                bindings, page=resolved_page, page_size=resolved_size
            )
        result = self._enrich_player_counts(result)
        self._list_cache.put(cache_key, result)
        return result

    def get_match_detail(
        self,
        *,
        server_slug: str,
        match_id: str,
    ) -> HistoricalMatchDetail:
        normalized_match_id = str(match_id or "").strip()
        if not normalized_match_id:
            raise HistoryMatchNotFoundError("historical-match-id-empty")
        binding = self._bindings.get(str(server_slug or "").strip())
        if binding is None:
            raise HistoryTargetNotFoundError("historical-target-not-configured")

        cache_key = (binding.target.key, normalized_match_id)
        cached = self._detail_cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            scoreboard = self._api_factory(binding).get_map_scoreboard(
                map_id=normalized_match_id
            )
        except CrconApiError as error:
            raise HistoryUnavailableError("crcon-map-scoreboard-unavailable") from error
        except (OSError, TimeoutError) as error:
            raise HistoryUnavailableError("crcon-map-scoreboard-unavailable") from error

        match = scoreboard.match
        if match is None or match.map_id is None:
            raise HistoryMatchNotFoundError("historical-match-not-found")
        if match.map_id != normalized_match_id:
            raise HistoryMatchNotFoundError("historical-match-id-mismatch")
        if match.server_number != binding.target.server_number:
            raise HistoryMatchNotFoundError("historical-match-wrong-target")
        if match.started_at is None:
            raise HistoryUnavailableError("crcon-map-scoreboard-malformed")

        identities: dict[str, CrconExplicitPlayerIdentity] = {}
        degraded_reasons: tuple[str, ...] = ()
        lookup = _historical_match_lookup(binding.target, match.map_id)
        player_ids = tuple(
            str(player.identity.player_id)
            for player in scoreboard.players
            if player.identity is not None
        )
        if self._repository is not None and lookup is not None and player_ids:
            try:
                identities = {
                    identity.player_id: identity
                    for identity in self._repository.list_match_player_identities(
                        match=lookup,
                        player_ids=player_ids,
                    )
                }
            except (CrconDatabaseError, CrconUnavailableError, ValueError):
                degraded_reasons = ("unknown-crcon-db-identity-unavailable",)

        detail = HistoricalMatchDetail(
            target=binding.target,
            scoreboard=scoreboard,
            explicit_identities=identities,
            degraded_reasons=degraded_reasons,
        )
        if match.ended_at is not None:
            self._detail_cache.put(cache_key, detail)
        return detail

    def _enrich_player_counts(
        self, page: HistoricalMatchPage
    ) -> HistoricalMatchPage:
        if self._repository is None or not page.items:
            return page
        lookups = tuple(
            lookup
            for record in page.items
            if (lookup := _historical_match_lookup(record.target, record.match.map_id))
            is not None
        )
        if not lookups:
            return page
        try:
            counts = {
                row.map_id: row.player_count
                for row in self._repository.list_match_player_counts(matches=lookups)
            }
        except (CrconDatabaseError, CrconUnavailableError, ValueError):
            return replace(
                page,
                items=tuple(
                    replace(
                        record,
                        player_count=None,
                        player_count_status="unknown-crcon-db-unavailable",
                    )
                    for record in page.items
                ),
                degraded_reasons=tuple(
                    dict.fromkeys(
                        (*page.degraded_reasons, "unknown-crcon-db-player-count-unavailable")
                    )
                ),
            )
        return replace(
            page,
            items=tuple(
                replace(
                    record,
                    player_count=counts.get(int(record.match.map_id)),
                    player_count_status=(
                        "complete-crcon-db-player-stats"
                        if int(record.match.map_id) in counts
                        else "unknown-crcon-db-no-match"
                    ),
                )
                if _numeric_map_id(record.match.map_id) is not None
                else record
                for record in page.items
            ),
        )

    def _resolve_list_bindings(self, scope: str) -> tuple[HistoryBinding, ...]:
        if scope == ALL_SERVERS_SLUG:
            bindings = tuple(self._bindings.values())
            if not bindings:
                raise HistoryUnavailableError("no-enabled-crcon-history-targets")
            return bindings
        binding = self._bindings.get(scope)
        if binding is None:
            raise HistoryTargetNotFoundError("historical-target-not-configured")
        return (binding,)

    def close(self) -> None:
        if self._repository is not None:
            self._repository.close()

    def _read_single_target_page(
        self,
        binding: HistoryBinding,
        *,
        page: int,
        page_size: int,
    ) -> HistoricalMatchPage:
        response = self._get_map_page(
            binding,
            page=page,
            page_size=page_size,
        )
        records, reasons = _validated_records(binding.target, response.maps)
        return HistoricalMatchPage(
            items=records,
            page=response.page or page,
            page_size=response.page_size or page_size,
            total=max(0, response.total or 0),
            degraded_reasons=reasons,
        )

    def _read_aggregate_page(
        self,
        bindings: Sequence[HistoryBinding],
        *,
        page: int,
        page_size: int,
    ) -> HistoricalMatchPage:
        if page * page_size > MAX_AGGREGATE_ROWS_PER_TARGET:
            raise ValueError("historical-aggregate-page-window-exceeded")
        rows_needed = min(page * page_size, MAX_AGGREGATE_ROWS_PER_TARGET)
        records: list[HistoricalMatchRecord] = []
        reasons: list[str] = []
        total = 0
        successful_targets = 0
        for binding in bindings:
            try:
                response = self._get_map_page(
                    binding,
                    page=1,
                    page_size=rows_needed,
                )
            except HistoryUnavailableError:
                reasons.append(f"crcon-target-unavailable:{binding.target.key}")
                continue
            successful_targets += 1
            target_records, target_reasons = _validated_records(
                binding.target, response.maps
            )
            records.extend(target_records)
            reasons.extend(target_reasons)
            total += max(0, response.total or 0)
        if successful_targets == 0:
            raise HistoryUnavailableError("all-crcon-history-targets-unavailable")
        records.sort(key=_record_sort_key, reverse=True)
        offset = (page - 1) * page_size
        return HistoricalMatchPage(
            items=tuple(records[offset : offset + page_size]),
            page=page,
            page_size=page_size,
            total=total,
            degraded_reasons=tuple(dict.fromkeys(reasons)),
        )

    def _get_map_page(
        self,
        binding: HistoryBinding,
        *,
        page: int,
        page_size: int,
    ) -> CrconMapPage:
        try:
            response = self._api_factory(binding).get_scoreboard_maps(
                page=page,
                limit=page_size,
                server_number=binding.target.server_number,
            )
        except CrconApiError as error:
            raise HistoryUnavailableError("crcon-scoreboard-maps-unavailable") from error
        except (OSError, TimeoutError) as error:
            raise HistoryUnavailableError("crcon-scoreboard-maps-unavailable") from error
        if (
            response.page != page
            or response.page_size is None
            or response.page_size < 1
            or response.page_size > MAX_AGGREGATE_ROWS_PER_TARGET
            or response.total is None
            or response.total < 0
        ):
            raise HistoryUnavailableError("crcon-scoreboard-maps-malformed")
        return response


def build_crcon_recent_matches_payload(
    *,
    limit: int,
    server_slug: str | None,
    page: int = 1,
    service: HistoryService | None = None,
) -> dict[str, object]:
    resolved_service = service or get_history_service()
    scope = _normalize_scope(server_slug)
    try:
        result = resolved_service.list_recent_matches(
            server_slug=scope,
            page=page,
            page_size=limit,
        )
    except HistoryTargetNotFoundError as error:
        return _recent_error_payload(scope, page, limit, str(error), not_found=True)
    except (HistoryUnavailableError, ValueError) as error:
        return _recent_error_payload(scope, page, limit, str(error))

    reasons = list(result.degraded_reasons)
    items = [_serialize_recent(record) for record in result.items]
    return {
        "status": "ok",
        "data": {
            "title": "Snapshot historico de partidas recientes por servidor",
            "context": "historical-recent-matches-snapshot",
            "source": "crcon-scoreboard-maps",
            "historical_match_source": "crcon",
            "server_slug": scope,
            "found": True,
            "degraded": bool(reasons),
            "degraded_reasons": reasons,
            "page": result.page,
            "page_size": result.page_size,
            "total": result.total,
            "total_pages": _total_pages(result.total, result.page_size),
            "snapshot_limit": None,
            "limit": limit,
            "generated_at": _iso(datetime.now(UTC)),
            **_source_policy("success" if items else "empty", "crcon-scoreboard-maps"),
            "items": items,
        },
    }


def build_crcon_match_detail_payload(
    *,
    server_slug: str,
    match_id: str,
    service: HistoryService | None = None,
) -> dict[str, object]:
    resolved_service = service or get_history_service()
    try:
        detail = resolved_service.get_match_detail(
            server_slug=server_slug,
            match_id=match_id,
        )
    except (HistoryTargetNotFoundError, HistoryMatchNotFoundError) as error:
        return _detail_error_payload(server_slug, match_id, str(error), unavailable=False)
    except HistoryUnavailableError as error:
        return _detail_error_payload(server_slug, match_id, str(error), unavailable=True)
    return {
        "status": "ok",
        "data": {
            "title": "Detalle de partida historica",
            "context": "historical-match-detail",
            "source": "crcon-map-scoreboard",
            "historical_match_source": "crcon",
            "server_slug": server_slug,
            "match_id": str(match_id),
            "found": True,
            "degraded": bool(detail.degraded_reasons),
            "degraded_reasons": list(detail.degraded_reasons),
            **_source_policy("success", "crcon-map-scoreboard"),
            "item": _serialize_detail(detail),
        },
    }


def _serialize_recent(record: HistoricalMatchRecord) -> dict[str, object]:
    target, match = record.target, record.match
    winner = _winner(match)
    return {
        "server": _server_mapping(target),
        "match_id": match.map_id,
        "internal_detail_match_id": match.map_id,
        "started_at": _iso(match.started_at),
        "ended_at": _iso(match.ended_at),
        "closed_at": _iso(match.ended_at or match.started_at),
        "duration_seconds": _duration_seconds(match),
        "map": {"name": match.layer, "pretty_name": match.map_name or match.layer},
        "game": (match.game or target.game).lower(),
        "game_mode": match.mode,
        "result": {
            "allied_score": match.score.allied,
            "axis_score": match.score.axis,
            "winner": winner,
        },
        "winner": winner,
        "player_count": record.player_count,
        "player_count_status": record.player_count_status,
        "capture_basis": "crcon-scoreboard-maps",
        "source_basis": "crcon-rest",
        "result_source": "crcon-scoreboard-maps",
        "match_url": None,
        "game_contract_status": "supported" if target.game == "hll" else "unverified",
    }


def _serialize_detail(detail: HistoricalMatchDetail) -> dict[str, object]:
    match = detail.scoreboard.match
    if match is None:  # Protected by HistoryService; keeps this serializer total.
        raise ValueError("Historical match detail has no match metadata.")
    names = {
        str(player.identity.player_id): player.name
        for player in detail.scoreboard.players
        if player.identity is not None and player.name
    }
    players = [
        _serialize_player(
            player,
            names,
            explicit_identity=(
                detail.explicit_identities.get(str(player.identity.player_id))
                if player.identity is not None
                else None
            ),
        )
        for player in detail.scoreboard.players
    ]
    recent = _serialize_recent(HistoricalMatchRecord(detail.target, match))
    encounters = [
        {**encounter, "owner_player_id": player["player_id"]}
        for player in players
        for encounter in player["encounters"]
    ]
    return {
        **recent,
        "player_count": len(players),
        "player_count_status": "complete-map-scoreboard",
        "players": players,
        "encounters": encounters,
        "timeline": {"encounters": encounters},
        "capture_basis": "crcon-map-scoreboard",
        "source_basis": "crcon-rest",
        "result_source": "crcon-map-scoreboard",
    }


def _serialize_player(
    player: Any,
    names: Mapping[str, str],
    *,
    explicit_identity: CrconExplicitPlayerIdentity | None = None,
) -> dict[str, object]:
    player_id = str(player.identity.player_id) if player.identity is not None else None
    external = build_external_player_profile_fields(
        steam_id=(
            explicit_identity.steam_id_64
            if explicit_identity is not None
            else player.identity.steam_id if player.identity is not None else None
        ),
        eos_id=(
            explicit_identity.eos_id
            if explicit_identity is not None
            else player.identity.eos_id if player.identity is not None else None
        ),
        platform=(
            explicit_identity.platform
            if explicit_identity is not None
            else player.identity.platform if player.identity is not None else None
        ),
    )
    kpm = player.kills_per_minute
    if kpm is None and player.kills is not None and player.time_seconds:
        kpm = player.kills / (player.time_seconds / 60)
    kd = player.kill_death_ratio
    if kd is None and player.kills is not None and player.deaths is not None:
        kd = player.kills / player.deaths if player.deaths else float(player.kills)
    return {
        "player_id": player_id,
        "stable_player_key": player_id,
        "player_name": player.name,
        "name": player.name,
        "team": player.team,
        "team_side": player.team,
        "level": player.level,
        "kills": player.kills,
        "deaths": player.deaths,
        "teamkills": player.teamkills,
        "deaths_by_teamkill": player.deaths_by_teamkill,
        "combat": player.combat,
        "offense": player.offense,
        "defense": player.defense,
        "support": player.support,
        "vehicle_kills": player.vehicle_kills,
        "vehicles_destroyed": player.vehicles_destroyed,
        "time_seconds": player.time_seconds,
        "player_active_seconds": player.time_seconds,
        "player_active_minutes": (
            round(player.time_seconds / 60, 3) if player.time_seconds is not None else None
        ),
        "kpm": round(kpm, 3) if kpm is not None else None,
        "kpm_status": "ready" if kpm is not None else "missing_active_time",
        "kd_ratio": round(kd, 3) if kd is not None else None,
        "top_weapons": _named_counts(player.weapons),
        "weapons": dict(player.weapons),
        "most_killed": _named_counts(player.most_killed, names=names),
        "death_by": _named_counts(player.death_by, names=names),
        "units": [
            {
                "ts": unit.timestamp_seconds,
                "team": unit.team,
                "squad": unit.squad,
                "role": unit.role,
            }
            for unit in player.units
        ],
        "encounters": [
            {
                "action": encounter.action,
                "player_id": encounter.player_id,
                "player_name": encounter.player_name,
                "ts": encounter.timestamp_seconds,
                "weapon": encounter.weapon,
            }
            for encounter in player.encounters
        ],
        **external,
    }


def _recent_error_payload(
    scope: str,
    page: int,
    limit: int,
    reason: str,
    *,
    not_found: bool = False,
) -> dict[str, object]:
    return {
        "status": "ok",
        "data": {
            "title": "Snapshot historico de partidas recientes por servidor",
            "context": "historical-recent-matches-snapshot",
            "source": "crcon-scoreboard-maps",
            "historical_match_source": "crcon",
            "server_slug": scope,
            "found": False,
            "degraded": True,
            "degraded_reasons": [reason],
            "not_found": not_found,
            "page": page,
            "page_size": limit,
            "total": 0,
            "total_pages": 0,
            "snapshot_limit": None,
            "limit": limit,
            **_source_policy("unavailable", reason),
            "items": [],
        },
    }


def _detail_error_payload(
    server_slug: str,
    match_id: str,
    reason: str,
    *,
    unavailable: bool,
) -> dict[str, object]:
    return {
        "status": "ok",
        "data": {
            "title": "Detalle de partida historica",
            "context": "historical-match-detail",
            "source": "crcon-map-scoreboard",
            "historical_match_source": "crcon",
            "server_slug": server_slug,
            "match_id": str(match_id),
            "found": False,
            "degraded": unavailable,
            "degraded_reasons": [reason] if unavailable else [],
            "not_found_reason": None if unavailable else reason,
            **_source_policy("unavailable" if unavailable else "empty", reason),
            "item": None,
        },
    }


def _source_policy(status: str, reason: str) -> dict[str, object]:
    return {
        "primary_source": "crcon",
        "selected_source": "crcon",
        "fallback_used": False,
        "fallback_reason": None,
        "source_attempts": [
            {"source": "crcon", "role": "primary", "status": status, "reason": reason}
        ],
    }


def _validated_records(
    target: ServerTarget,
    matches: Sequence[CrconHistoricalMap],
) -> tuple[tuple[HistoricalMatchRecord, ...], tuple[str, ...]]:
    records: list[HistoricalMatchRecord] = []
    reasons: list[str] = []
    for match in matches:
        if match.server_number != target.server_number:
            reasons.append(f"crcon-list-row-wrong-target:{target.key}")
            continue
        if match.map_id is None or match.started_at is None:
            reasons.append(f"crcon-list-row-malformed:{target.key}")
            continue
        records.append(HistoricalMatchRecord(target=target, match=match))
    return tuple(records), tuple(dict.fromkeys(reasons))


def _winner(match: CrconHistoricalMap) -> str | None:
    allied, axis = match.score.allied, match.score.axis
    if allied is None or axis is None:
        return None
    if allied > axis:
        return "allies"
    if axis > allied:
        return "axis"
    return "draw"


def _duration_seconds(match: CrconHistoricalMap) -> int | None:
    if match.match_time_seconds is not None:
        return match.match_time_seconds
    if match.started_at is None or match.ended_at is None:
        return None
    return max(0, int((match.ended_at - match.started_at).total_seconds()))


def _server_mapping(target: ServerTarget) -> dict[str, object]:
    return {
        "slug": target.key,
        "name": target.display_name,
        "server_number": target.server_number,
        "game": target.game,
    }


def _named_counts(
    pairs: Sequence[tuple[str, int]],
    *,
    names: Mapping[str, str] | None = None,
) -> list[dict[str, object]]:
    lookup = names or {}
    return [
        {"name": lookup.get(name, name), "count": count}
        for name, count in sorted(pairs, key=lambda pair: (-pair[1], pair[0]))
    ]


def _record_sort_key(record: HistoricalMatchRecord) -> datetime:
    return record.match.ended_at or record.match.started_at or datetime.min.replace(tzinfo=UTC)


def _validate_pagination(page: int, page_size: int) -> tuple[int, int]:
    if isinstance(page, bool) or page < 1:
        raise ValueError("historical-page-invalid")
    if isinstance(page_size, bool) or page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise ValueError("historical-page-size-invalid")
    return int(page), int(page_size)


def _normalize_scope(server_slug: str | None) -> str:
    normalized = str(server_slug or "").strip()
    return normalized if normalized and normalized != "all" else ALL_SERVERS_SLUG


def _total_pages(total: int, page_size: int) -> int:
    return (total + page_size - 1) // page_size if total else 0


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z") if value else None


def _numeric_map_id(value: object) -> int | None:
    normalized = str(value or "").strip()
    if not normalized or not normalized.isdecimal():
        return None
    map_id = int(normalized)
    return map_id if map_id > 0 else None


def _historical_match_lookup(
    target: ServerTarget,
    map_id: object,
) -> CrconHistoricalMatchLookup | None:
    numeric_map_id = _numeric_map_id(map_id)
    if numeric_map_id is None:
        return None
    return CrconHistoricalMatchLookup(
        map_id=numeric_map_id,
        scope=resolve_server_scope(target),
    )


def _load_history_bindings() -> dict[str, HistoryBinding]:
    current_configs = get_crcon_current_match_bindings()
    configs_by_slug = {str(row["server_slug"]): row for row in current_configs}
    canonical = load_server_targets().all(enabled_only=True)
    if not canonical:
        canonical = tuple(
            ServerTarget(
                key=slug,
                display_name=str(config.get("display_name") or slug),
                server_number=int(config["server_number"]),
                game=str(config.get("game") or "hll"),  # type: ignore[arg-type]
                crcon_base_url=str(config["api_base_url"]),
                enabled=bool(config.get("enabled", True)),
                capabilities=frozenset(config.get("capabilities") or ()),
            )
            for slug, config in configs_by_slug.items()
            if bool(config.get("enabled", True))
        )
    return {
        target.key: HistoryBinding(
            target=target,
            api_headers=dict(configs_by_slug.get(target.key, {}).get("api_headers") or {}),
        )
        for target in canonical
    }


_runtime_lock = Lock()
_runtime_fingerprint: str | None = None
_runtime_service: HistoryService | None = None


def get_history_service() -> HistoryService:
    """Build or reuse one process-local service without exposing binding secrets."""
    bindings = _load_history_bindings()
    dsn = get_crcon_database_url()
    database_config = {
        "dsn_digest": hashlib.sha256(dsn.encode("utf-8")).hexdigest() if dsn else None,
        "connect_timeout": get_crcon_database_connect_timeout_seconds(),
        "statement_timeout": get_crcon_database_statement_timeout_ms(),
        "lock_timeout": get_crcon_database_lock_timeout_ms(),
        "pool_size": get_crcon_database_pool_size(),
    }
    fingerprint_payload = [
        {
            "key": binding.target.key,
            "display_name": binding.target.display_name,
            "server_number": binding.target.server_number,
            "game": binding.target.game,
            "crcon_base_url": binding.target.crcon_base_url,
            "enabled": binding.target.enabled,
            "capabilities": sorted(binding.target.capabilities),
            "headers": sorted(binding.api_headers.items()),
        }
        for binding in bindings.values()
    ] + [database_config]
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, default=str, sort_keys=True).encode("utf-8")
    ).hexdigest()
    global _runtime_fingerprint, _runtime_service
    with _runtime_lock:
        if _runtime_service is not None and _runtime_fingerprint == fingerprint:
            return _runtime_service
        if _runtime_service is not None:
            _runtime_service.close()
        timeout = get_crcon_api_timeout_seconds()
        repository = PostgresCrconRepository(
            dsn=dsn,
            connect_timeout_seconds=database_config["connect_timeout"],
            statement_timeout_ms=database_config["statement_timeout"],
            lock_timeout_ms=database_config["lock_timeout"],
            pool_size=database_config["pool_size"],
        )
        _runtime_service = HistoryService(
            bindings=bindings,
            repository=repository,
            api_factory=lambda binding: CrconApiClient(
                base_url=binding.target.crcon_base_url,
                timeout_seconds=timeout,
                headers=binding.api_headers,
            ),
        )
        _runtime_fingerprint = fingerprint
        return _runtime_service


def _close_runtime_service() -> None:
    with _runtime_lock:
        if _runtime_service is not None:
            _runtime_service.close()


atexit.register(_close_runtime_service)
