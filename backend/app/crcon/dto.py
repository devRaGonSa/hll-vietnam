"""Version-aware internal DTOs for verified CRCON API responses.

The HLL shapes in this module were verified against two authorized CRCON
12.0.1 targets. HLLV remains unverified and is represented separately in the
capability matrix. Parsers still tolerate absent optional data because live and
historical endpoints have legitimate empty/null states.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from ..domain import PlayerIdentity, player_id_from
from .models import CrconContractStatus


CRCON_MAP_HISTORY_DEFAULT_MAX_ENTRIES = 500


@dataclass(frozen=True, slots=True)
class CrconEndpointDocumentation:
    endpoint: str
    arguments: tuple[str, ...] = ()
    return_type: str | None = None
    doc_string: str | None = None
    permissions_required: tuple[str, ...] = ()
    allowed_http_methods: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CrconApiDocumentation:
    endpoints: tuple[CrconEndpointDocumentation, ...] = ()
    contract_status: CrconContractStatus = CrconContractStatus.SUPPORTED


@dataclass(frozen=True, slots=True)
class CrconScore:
    allied: int | None = None
    axis: int | None = None


@dataclass(frozen=True, slots=True)
class CrconMapRef:
    layer: str | None = None
    map_name: str | None = None
    mode: str | None = None
    started_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CrconPublicInfo:
    current_map: CrconMapRef
    next_map: CrconMapRef
    score: CrconScore
    player_count: int | None = None
    max_player_count: int | None = None
    allied_count: int | None = None
    axis_count: int | None = None
    remaining_seconds: int | None = None
    server_name: str | None = None
    game: str | None = None
    contract_status: CrconContractStatus = CrconContractStatus.SUPPORTED


@dataclass(frozen=True, slots=True)
class CrconLiveUnit:
    team: str | None = None
    squad: str | None = None
    role: str | None = None


@dataclass(frozen=True, slots=True)
class CrconLivePlayer:
    identity: PlayerIdentity | None
    name: str | None = None
    team: str | None = None
    status: str | None = None
    level: int | None = None
    combat: int | None = None
    offense: int | None = None
    defense: int | None = None
    support: int | None = None
    kills: int | None = None
    deaths: int | None = None
    teamkills: int | None = None
    deaths_by_teamkill: int | None = None
    weapon_counts: tuple[tuple[str, int], ...] = ()
    units: tuple[CrconLiveUnit, ...] = ()

    def to_current_match_mapping(self) -> dict[str, object]:
        """Temporary normalized bridge for the existing current-match service."""
        latest_unit = self.units[-1] if self.units else None
        return {
            "player_id": str(self.identity.player_id) if self.identity else None,
            "player": self.name,
            "team": self.team,
            "status": self.status,
            "level": self.level,
            "combat": self.combat,
            "offense": self.offense,
            "defense": self.defense,
            "support": self.support,
            "kills": self.kills,
            "deaths": self.deaths,
            "teamkills": self.teamkills,
            "deaths_by_teamkill": self.deaths_by_teamkill,
            "weapons": dict(self.weapon_counts),
            "unit": latest_unit.squad if latest_unit else None,
            "role": latest_unit.role if latest_unit else None,
        }


@dataclass(frozen=True, slots=True)
class CrconLiveGameStats:
    players: tuple[CrconLivePlayer, ...] = ()
    observed_at: datetime | None = None
    refresh_interval_seconds: int | None = None
    contract_status: CrconContractStatus = CrconContractStatus.SUPPORTED


@dataclass(frozen=True, slots=True)
class CrconLiveScoreboard:
    players: tuple[CrconLivePlayer, ...] = ()
    observed_at: datetime | None = None
    refresh_interval_seconds: int | None = None
    contract_status: CrconContractStatus = CrconContractStatus.SUPPORTED


@dataclass(frozen=True, slots=True)
class CrconHistoricalMap:
    map_id: str | None = None
    server_number: int | None = None
    game: str | None = None
    layer: str | None = None
    map_name: str | None = None
    mode: str | None = None
    creation_time: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    score: CrconScore = CrconScore()
    player_stats_count: int = 0
    guessed: bool | None = None
    match_time_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class CrconMapPage:
    maps: tuple[CrconHistoricalMap, ...] = ()
    page: int | None = None
    page_size: int | None = None
    total: int | None = None
    contract_status: CrconContractStatus = CrconContractStatus.SUPPORTED


@dataclass(frozen=True, slots=True)
class CrconEncounter:
    action: str | None = None
    player_id: str | None = None
    player_name: str | None = None
    timestamp_seconds: int | None = None
    weapon: str | None = None


@dataclass(frozen=True, slots=True)
class CrconHistoricalUnit:
    timestamp_seconds: int | None = None
    team: object = None
    squad: object = None
    role: object = None


@dataclass(frozen=True, slots=True)
class CrconPlayerMatchStats:
    identity: PlayerIdentity | None
    name: str | None = None
    kills: int | None = None
    deaths: int | None = None
    teamkills: int | None = None
    deaths_by_teamkill: int | None = None
    team: str | None = None
    level: int | None = None
    combat: int | None = None
    offense: int | None = None
    defense: int | None = None
    support: int | None = None
    vehicle_kills: int | None = None
    vehicles_destroyed: int | None = None
    time_seconds: int | None = None
    kills_per_minute: float | None = None
    kill_death_ratio: float | None = None
    weapons: tuple[tuple[str, int], ...] = ()
    most_killed: tuple[tuple[str, int], ...] = ()
    death_by: tuple[tuple[str, int], ...] = ()
    units: tuple[CrconHistoricalUnit, ...] = ()
    encounters: tuple[CrconEncounter, ...] = ()


@dataclass(frozen=True, slots=True)
class CrconMapScoreboard:
    match: CrconHistoricalMap | None = None
    players: tuple[CrconPlayerMatchStats, ...] = ()
    contract_status: CrconContractStatus = CrconContractStatus.SUPPORTED

    @property
    def supports_match_detail(self) -> bool:
        """The verified endpoint carries match metadata and per-player detail."""
        return self.match is not None


@dataclass(frozen=True, slots=True)
class CrconMapHistory:
    maps: tuple[CrconHistoricalMap, ...] = ()
    recent_only: bool = True
    default_max_entries: int = CRCON_MAP_HISTORY_DEFAULT_MAX_ENTRIES
    contract_status: CrconContractStatus = CrconContractStatus.SUPPORTED


@dataclass(frozen=True, slots=True)
class CrconPreviousMap:
    match: CrconHistoricalMap | None = None
    contract_status: CrconContractStatus = CrconContractStatus.SUPPORTED


@dataclass(frozen=True, slots=True)
class CrconPlayerHistoryEntry:
    """Safe subset of one CRCON player-history row.

    Moderation, account and session fields in the upstream response are
    intentionally not represented by this DTO.
    """

    identity: PlayerIdentity
    names: tuple[str, ...] = ()
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CrconPlayerHistoryPage:
    players: tuple[CrconPlayerHistoryEntry, ...] = ()
    page: int = 1
    page_size: int = 1
    total: int = 0
    contract_status: CrconContractStatus = CrconContractStatus.SUPPORTED


def parse_api_documentation(payload: object) -> CrconApiDocumentation:
    rows = _mapping_rows(payload)
    return CrconApiDocumentation(
        endpoints=tuple(
            CrconEndpointDocumentation(
                endpoint=_text(row.get("endpoint")) or "",
                arguments=tuple(_mapping(row.get("arguments")).keys()),
                return_type=_text(row.get("return_type")),
                doc_string=_text(row.get("doc_string")),
                permissions_required=tuple(
                    text
                    for value in _sequence(row.get("permissions_required"))
                    if (text := _text(value)) is not None
                ),
                allowed_http_methods=tuple(
                    text
                    for value in _sequence(row.get("allowed_http_methods"))
                    if (text := _text(value)) is not None
                ),
            )
            for row in rows
            if _text(row.get("endpoint"))
        )
    )


def parse_public_info(payload: Mapping[str, object]) -> CrconPublicInfo:
    current_map = _mapping(payload.get("current_map"))
    next_map = _mapping(payload.get("next_map"))
    score = _mapping(payload.get("score"))
    counts = _mapping(payload.get("player_count_by_team"))
    name = _mapping(payload.get("name"))
    config = _mapping(payload.get("config"))
    return CrconPublicInfo(
        current_map=_map_ref(current_map),
        next_map=_map_ref(next_map),
        score=CrconScore(_integer(score.get("allied")), _integer(score.get("axis"))),
        player_count=_integer(payload.get("player_count")),
        max_player_count=_integer(payload.get("max_player_count")),
        allied_count=_integer(counts.get("allied")),
        axis_count=_integer(counts.get("axis")),
        remaining_seconds=_integer(payload.get("time_remaining")),
        server_name=_text(name.get("name") or name.get("short_name")),
        game=_text(config.get("game") or payload.get("game")),
    )


def parse_live_game_stats(payload: Mapping[str, object]) -> CrconLiveGameStats:
    return CrconLiveGameStats(
        players=_live_players(payload),
        observed_at=_datetime(payload.get("snapshot_timestamp")),
        refresh_interval_seconds=_integer(payload.get("refresh_interval_sec")),
    )


def parse_live_scoreboard(payload: Mapping[str, object]) -> CrconLiveScoreboard:
    return CrconLiveScoreboard(
        players=_live_players(payload),
        observed_at=_datetime(payload.get("snapshot_timestamp")),
        refresh_interval_seconds=_integer(payload.get("refresh_interval_sec")),
    )


def parse_scoreboard_maps(payload: Mapping[str, object]) -> CrconMapPage:
    return CrconMapPage(
        maps=tuple(_historical_map(row) for row in _mapping_rows(payload.get("maps"))),
        page=_integer(payload.get("page")),
        page_size=_integer(payload.get("page_size")),
        total=_integer(payload.get("total")),
    )


def parse_map_scoreboard(payload: Mapping[str, object]) -> CrconMapScoreboard:
    rows = _mapping_rows(payload.get("player_stats"))
    return CrconMapScoreboard(
        match=_historical_map(payload),
        players=tuple(_player_match_stats(row) for row in rows),
    )


def parse_map_history(payload: object) -> CrconMapHistory:
    rows = (
        _mapping_rows(payload.get("maps") or payload.get("history"))
        if isinstance(payload, Mapping)
        else _mapping_rows(payload)
    )
    return CrconMapHistory(maps=tuple(_historical_map(row) for row in rows))


def parse_previous_map(payload: Mapping[str, object] | None) -> CrconPreviousMap:
    if not payload:
        return CrconPreviousMap(match=None)
    candidate = payload.get("map") or payload.get("previous_map")
    row = _mapping(candidate) if isinstance(candidate, Mapping) else payload
    return CrconPreviousMap(match=_historical_map(row) if row else None)


def parse_players_history(payload: Mapping[str, object]) -> CrconPlayerHistoryPage:
    """Parse only public identity/search fields from `get_players_history`."""
    raw_players = payload.get("players")
    page_number = _integer(payload.get("page"))
    page_size = _integer(payload.get("page_size"))
    total = _integer(payload.get("total"))
    if (
        not isinstance(raw_players, Sequence)
        or isinstance(raw_players, (str, bytes, bytearray))
        or page_number is None
        or page_number < 1
        or page_size is None
        or page_size < 1
        or total is None
        or total < 0
        or any(not isinstance(row, Mapping) for row in raw_players)
    ):
        raise ValueError("CRCON player-history response is malformed.")
    players: list[CrconPlayerHistoryEntry] = []
    for row in _mapping_rows(raw_players):
        player_id = player_id_from(row.get("player_id"))
        if player_id is None:
            continue
        soldier = _mapping(row.get("soldier"))
        account = _mapping(row.get("account"))
        names = tuple(
            dict.fromkeys(
                name
                for value in _sequence(row.get("names_by_match"))
                if (name := _text(value)) is not None
            )
        )
        display_name = (
            (names[0] if names else None)
            or _text(soldier.get("name"))
            or _text(account.get("name"))
        )
        players.append(
            CrconPlayerHistoryEntry(
                identity=PlayerIdentity(
                    player_id=player_id,
                    steam_id=_text(row.get("steam_id")),
                    eos_id=_text(soldier.get("eos_id")),
                    platform=_text(soldier.get("platform")),
                    display_name=display_name,
                ),
                names=names,
                first_seen_at=_datetime_milliseconds(
                    row.get("first_seen_timestamp_ms")
                ),
                last_seen_at=_datetime_milliseconds(
                    row.get("last_seen_timestamp_ms")
                ),
            )
        )
    return CrconPlayerHistoryPage(
        players=tuple(players),
        page=page_number,
        page_size=page_size,
        total=total,
    )


def _live_players(payload: Mapping[str, object]) -> tuple[CrconLivePlayer, ...]:
    rows = _mapping_rows(payload.get("stats") or payload.get("players"))
    return tuple(_live_player(row) for row in rows)


def _live_player(row: Mapping[str, object]) -> CrconLivePlayer:
    identity = _identity(row)
    return CrconLivePlayer(
        identity=identity,
        name=_text(row.get("player") or row.get("name")),
        team=_text(row.get("team")),
        status=_text(row.get("status")),
        level=_integer(row.get("level")),
        combat=_integer(row.get("combat")),
        offense=_integer(row.get("offense")),
        defense=_integer(row.get("defense")),
        support=_integer(row.get("support")),
        kills=_integer(row.get("kills")),
        deaths=_integer(row.get("deaths")),
        teamkills=_integer(row.get("teamkills")),
        deaths_by_teamkill=_integer(row.get("deaths_by_tk")),
        weapon_counts=_count_pairs(row.get("weapons")),
        units=tuple(
            CrconLiveUnit(
                team=_text(unit.get("team")),
                squad=_text(unit.get("squad") or unit.get("unit")),
                role=_text(unit.get("role")),
            )
            for unit in _mapping_rows(row.get("units"))
        ),
    )


def _identity(row: Mapping[str, object]) -> PlayerIdentity | None:
    player_id = player_id_from(row.get("player_id"))
    if player_id is None:
        return None
    steam_info = _mapping(row.get("steaminfo"))
    steam_profile = _mapping(steam_info.get("profile"))
    return PlayerIdentity(
        player_id=player_id,
        steam_id=_text(
            row.get("steam_id")
            or steam_profile.get("steamid")
            or steam_profile.get("steam_id")
        ),
        eos_id=_text(row.get("eos_id")),
        platform=_text(row.get("platform")),
        display_name=_text(row.get("player") or row.get("name")),
    )


def _historical_map(row: Mapping[str, object]) -> CrconHistoricalMap:
    map_data = _mapping(row.get("map"))
    map_metadata = _mapping(map_data.get("map"))
    score = _mapping(row.get("result") or row.get("score"))
    player_stats = row.get("player_stats")
    if isinstance(player_stats, Mapping):
        player_stats_count = len(player_stats)
    else:
        player_stats_count = len(_sequence(player_stats))
    return CrconHistoricalMap(
        map_id=_text(row.get("id")),
        server_number=_integer(row.get("server_number")),
        game=_text(row.get("game")),
        layer=_text(map_data.get("id") or row.get("map_name") or row.get("name")),
        map_name=_text(
            map_metadata.get("pretty_name")
            or map_metadata.get("name")
            or row.get("map_name")
            or row.get("name")
        ),
        mode=_text(map_data.get("game_mode") or row.get("game_mode")),
        creation_time=_datetime(row.get("creation_time")),
        started_at=_datetime(row.get("start")),
        ended_at=_datetime(row.get("end")),
        score=CrconScore(_integer(score.get("allied")), _integer(score.get("axis"))),
        player_stats_count=player_stats_count,
        guessed=_boolean(row.get("guessed")),
        match_time_seconds=_integer(row.get("match_time")),
    )


def _player_match_stats(row: Mapping[str, object]) -> CrconPlayerMatchStats:
    return CrconPlayerMatchStats(
        identity=_identity(row),
        name=_text(row.get("player") or row.get("name")),
        kills=_integer(row.get("kills")),
        deaths=_integer(row.get("deaths")),
        teamkills=_integer(row.get("teamkills")),
        deaths_by_teamkill=_integer(row.get("deaths_by_tk")),
        team=_text(_mapping(row.get("team")).get("side") or row.get("team")),
        level=_integer(row.get("level")),
        combat=_integer(row.get("combat")),
        offense=_integer(row.get("offense")),
        defense=_integer(row.get("defense")),
        support=_integer(row.get("support")),
        vehicle_kills=_integer(row.get("vehicle_kills")),
        vehicles_destroyed=_integer(row.get("vehicles_destroyed")),
        time_seconds=_integer(row.get("time_seconds")),
        kills_per_minute=_float(row.get("kills_per_minute")),
        kill_death_ratio=_float(row.get("kill_death_ratio")),
        weapons=_count_pairs(row.get("weapons")),
        most_killed=_count_pairs(row.get("most_killed")),
        death_by=_count_pairs(row.get("death_by")),
        units=tuple(
            CrconHistoricalUnit(
                timestamp_seconds=_integer(unit.get("ts")),
                team=unit.get("team"),
                squad=unit.get("squad"),
                role=unit.get("role"),
            )
            for unit in _mapping_rows(row.get("units"))
        ),
        encounters=tuple(
            CrconEncounter(
                action=_text(encounter.get("action")),
                player_id=_text(encounter.get("player_id")),
                player_name=_text(encounter.get("player_name")),
                timestamp_seconds=_integer(encounter.get("ts")),
                weapon=_text(encounter.get("weapon")),
            )
            for encounter in _mapping_rows(row.get("encounters"))
        ),
    )


def _map_ref(row: Mapping[str, object]) -> CrconMapRef:
    raw_map = row.get("map")
    details = _mapping(raw_map)
    map_metadata = _mapping(details.get("map"))
    layer = _text(details.get("id") or details.get("layer") or raw_map)
    return CrconMapRef(
        layer=layer,
        map_name=_text(
            map_metadata.get("pretty_name")
            or map_metadata.get("name")
            or details.get("name")
            or layer
        ),
        mode=_text(details.get("game_mode") or details.get("mode")),
        started_at=_datetime(row.get("start")),
    )


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mapping_rows(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _sequence(value: object) -> tuple[object, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(value)


def _text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _integer(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return None


def _float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _boolean(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _count_pairs(value: object) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, Mapping):
        return ()
    pairs = []
    for raw_name, raw_count in value.items():
        name = _text(raw_name)
        count = _integer(raw_count)
        if name is not None and count is not None:
            pairs.append((name, count))
    return tuple(sorted(pairs))


def _datetime(value: object) -> datetime | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(float(value), tz=UTC)
        except (OSError, OverflowError, ValueError):
            return None
    text = _text(value)
    if text is None:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _datetime_milliseconds(value: object) -> datetime | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return datetime.fromtimestamp(float(value) / 1000, tz=UTC)
    except (TypeError, OSError, OverflowError, ValueError):
        return None
