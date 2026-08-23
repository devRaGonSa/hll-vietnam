"""Bounded in-memory parity diagnostics for legacy and CRCON current match."""

from __future__ import annotations

import hashlib
import logging
import secrets
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from threading import Lock
from typing import Protocol

from .crcon.dto import CrconMapPage, CrconMapScoreboard
from .current_match import CurrentMatchSnapshot, CurrentPlayer
from .normalizers import normalize_map_name
from .server_targets import ServerTarget


LOGGER = logging.getLogger(__name__)
MATCH_TIMING_TOLERANCE_SECONDS = 5
FINAL_MATCH_TOLERANCE_SECONDS = 300
FINAL_LIVE_WINDOW_SECONDS = 30
MAX_DIAGNOSTIC_PLAYER_KEYS = 20
PLAYER_FIELDS = (
    "name",
    "team",
    "unit",
    "role",
    "level",
    "kills",
    "deaths",
    "teamkills",
    "combat",
    "offense",
    "defense",
    "support",
)
STAT_FIELDS = ("kills", "deaths", "teamkills", "combat", "offense", "defense", "support")


class ParityClassification(StrEnum):
    MATCH = "MATCH"
    PLAYER_SET = "PLAYER_SET"
    STAT = "STAT"
    TIMING = "TIMING"
    EXPECTED_SOURCE_DIFFERENCE = "EXPECTED_SOURCE_DIFFERENCE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class PlayerStatDelta:
    player_key: str
    field: str
    legacy_value: int
    crcon_value: int
    absolute_difference: int
    percentage_difference: float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "player_key": self.player_key,
            "field": self.field,
            "legacy_value": self.legacy_value,
            "crcon_value": self.crcon_value,
            "absolute_difference": self.absolute_difference,
            "percentage_difference": self.percentage_difference,
        }


@dataclass(frozen=True, slots=True)
class CurrentMatchParityReport:
    server_key: str
    timestamp: datetime
    legacy_available: bool
    crcon_available: bool
    equal_match_fields: tuple[str, ...]
    different_match_fields: tuple[str, ...]
    unavailable_match_fields: tuple[str, ...]
    legacy_player_count: int
    crcon_player_count: int
    only_legacy: tuple[str, ...]
    only_crcon: tuple[str, ...]
    compared_players: int
    kills_exact: int
    kills_different: int
    max_kill_delta: int
    total_kill_delta: int
    stat_deltas: tuple[PlayerStatDelta, ...]
    classification: tuple[ParityClassification, ...]
    confidence: str

    def to_dict(self) -> dict[str, object]:
        return {
            "server_key": self.server_key,
            "timestamp": _iso(self.timestamp),
            "legacy_available": self.legacy_available,
            "crcon_available": self.crcon_available,
            "match": {
                "equal_fields": list(self.equal_match_fields),
                "different_fields": list(self.different_match_fields),
                "unavailable_fields": list(self.unavailable_match_fields),
            },
            "players": {
                "legacy_count": self.legacy_player_count,
                "crcon_count": self.crcon_player_count,
                "only_legacy": list(self.only_legacy),
                "only_crcon": list(self.only_crcon),
            },
            "stats": {
                "compared_players": self.compared_players,
                "kills_exact": self.kills_exact,
                "kills_different": self.kills_different,
                "max_kill_delta": self.max_kill_delta,
                "total_kill_delta": self.total_kill_delta,
                "deltas": [delta.to_dict() for delta in self.stat_deltas],
            },
            "classification": [value.value for value in self.classification],
            "confidence": self.confidence,
        }


def compare_current_match(
    *,
    server_key: str,
    legacy_summary: Mapping[str, object] | None,
    legacy_players: Sequence[Mapping[str, object]] | None,
    crcon_snapshot: CurrentMatchSnapshot | None,
    timestamp: datetime | None = None,
) -> CurrentMatchParityReport:
    """Compare public legacy projections with one CRCON candidate without raw IDs."""
    observed_at = _utc(timestamp or datetime.now(UTC))
    legacy_data = _payload_data(legacy_summary)
    legacy_available = bool(legacy_data and legacy_data.get("found", True))
    crcon_available = crcon_snapshot is not None
    equal_fields: list[str] = []
    different_fields: list[str] = []
    unavailable_fields: list[str] = []

    if legacy_available and crcon_snapshot is not None:
        crcon_summary = crcon_snapshot.summary
        match_pairs = {
            "match_identity": (legacy_data.get("map_id"), crcon_summary.layer),
            "map": (
                normalize_map_name(legacy_data.get("map") or legacy_data.get("map_pretty_name")),
                normalize_map_name(crcon_summary.map_name or crcon_summary.layer),
            ),
            "game_mode": (legacy_data.get("game_mode"), crcon_summary.mode),
            "score_allies": (legacy_data.get("allied_score"), crcon_summary.allied_score),
            "score_axis": (legacy_data.get("axis_score"), crcon_summary.axis_score),
            "player_count": (legacy_data.get("players"), crcon_summary.player_count),
            "max_players": (legacy_data.get("max_players"), crcon_summary.max_player_count),
            "match_start": (legacy_data.get("started_at"), _iso(crcon_summary.started_at)),
            "time_remaining": (
                legacy_data.get("remaining_match_time_seconds"),
                crcon_summary.remaining_seconds,
            ),
            "match_status": (
                legacy_data.get("status"),
                "degraded" if crcon_snapshot.degraded else "online",
            ),
        }
        for field, values in match_pairs.items():
            left, right = values
            if left is None or right is None:
                unavailable_fields.append(field)
            elif field in {"match_start", "time_remaining"}:
                if _timing_equal(left, right):
                    equal_fields.append(field)
                else:
                    different_fields.append(field)
            elif _comparable_text(left) == _comparable_text(right):
                equal_fields.append(field)
            else:
                different_fields.append(field)

    legacy_index = _legacy_player_index(legacy_players or ())
    crcon_index = _crcon_player_index(crcon_snapshot.players if crcon_snapshot else ())
    legacy_ids = set(legacy_index)
    crcon_ids = set(crcon_index)
    shared_ids = sorted(legacy_ids & crcon_ids)
    only_legacy = tuple(_opaque_key(value) for value in sorted(legacy_ids - crcon_ids))[
        :MAX_DIAGNOSTIC_PLAYER_KEYS
    ]
    only_crcon = tuple(_opaque_key(value) for value in sorted(crcon_ids - legacy_ids))[
        :MAX_DIAGNOSTIC_PLAYER_KEYS
    ]
    stat_deltas: list[PlayerStatDelta] = []
    kills_exact = 0
    kills_different = 0
    kill_deltas: list[int] = []
    expected_differences = bool(unavailable_fields)
    for player_id in shared_ids:
        legacy_player = legacy_index[player_id]
        crcon_player = crcon_index[player_id]
        for field in PLAYER_FIELDS:
            left = _legacy_player_value(legacy_player, field)
            right = getattr(crcon_player, field)
            if left is None or right is None:
                expected_differences = True
                continue
            if field not in STAT_FIELDS:
                if _comparable_text(left) != _comparable_text(right):
                    expected_differences = True
                continue
            try:
                legacy_value = int(left)
                crcon_value = int(right)
            except (TypeError, ValueError):
                expected_differences = True
                continue
            difference = abs(legacy_value - crcon_value)
            if field == "kills":
                kill_deltas.append(difference)
                if difference == 0:
                    kills_exact += 1
                else:
                    kills_different += 1
            if difference:
                stat_deltas.append(
                    PlayerStatDelta(
                        player_key=_opaque_key(player_id),
                        field=field,
                        legacy_value=legacy_value,
                        crcon_value=crcon_value,
                        absolute_difference=difference,
                        percentage_difference=_percentage_difference(legacy_value, crcon_value),
                    )
                )

    classifications: list[ParityClassification] = []
    if not legacy_available or not crcon_available:
        classifications.append(ParityClassification.UNKNOWN)
    if only_legacy or only_crcon:
        classifications.append(ParityClassification.PLAYER_SET)
    if stat_deltas:
        classifications.append(ParityClassification.STAT)
    if any(field in {"match_start", "time_remaining"} for field in different_fields):
        classifications.append(ParityClassification.TIMING)
    if any(field not in {"match_start", "time_remaining"} for field in different_fields):
        classifications.append(ParityClassification.MATCH)
    if expected_differences:
        classifications.append(ParityClassification.EXPECTED_SOURCE_DIFFERENCE)
    if not classifications:
        classifications.append(ParityClassification.MATCH)

    report = CurrentMatchParityReport(
        server_key=server_key,
        timestamp=observed_at,
        legacy_available=legacy_available,
        crcon_available=crcon_available,
        equal_match_fields=tuple(equal_fields),
        different_match_fields=tuple(different_fields),
        unavailable_match_fields=tuple(unavailable_fields),
        legacy_player_count=len(legacy_index),
        crcon_player_count=len(crcon_index),
        only_legacy=only_legacy,
        only_crcon=only_crcon,
        compared_players=len(shared_ids),
        kills_exact=kills_exact,
        kills_different=kills_different,
        max_kill_delta=max(kill_deltas, default=0),
        total_kill_delta=sum(kill_deltas),
        stat_deltas=tuple(stat_deltas[:100]),
        classification=tuple(dict.fromkeys(classifications)),
        confidence=(
            "low"
            if not legacy_available or not crcon_available
            else "high"
            if not different_fields and not only_legacy and not only_crcon and not stat_deltas
            else "medium"
        ),
    )
    LOGGER.debug(
        "current_match_shadow server=%s legacy=%s crcon=%s shared=%s only_legacy=%s "
        "only_crcon=%s kills_different=%s max_kill_delta=%s classifications=%s",
        server_key,
        legacy_available,
        crcon_available,
        report.compared_players,
        len(only_legacy),
        len(only_crcon),
        kills_different,
        report.max_kill_delta,
        ",".join(value.value for value in report.classification),
    )
    return report


class FinalMatchApi(Protocol):
    def get_scoreboard_maps(
        self, *, page: int = 1, limit: int = 100, server_number: int | str | None = None
    ) -> CrconMapPage: ...

    def get_map_scoreboard(self, *, map_id: int | str) -> CrconMapScoreboard: ...


@dataclass(frozen=True, slots=True)
class FinalMatchParityReport:
    server_key: str
    live_observed_at: datetime | None
    map_id: str | None
    status: str
    compared_players: int
    only_live_count: int
    only_final_count: int
    stat_deltas: tuple[PlayerStatDelta, ...]
    stat_comparisons: tuple[tuple[str, int], ...]
    stat_exact: tuple[tuple[str, int], ...]
    temporal_gap_seconds: int | None
    close_to_final: bool
    expected_final_window_deltas: int
    unexplained_deltas: int
    expected_final_window_by_field: tuple[tuple[str, int], ...]
    unexplained_by_field: tuple[tuple[str, int], ...]
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "server_key": self.server_key,
            "live_observed_at": _iso(self.live_observed_at),
            "map_id": self.map_id,
            "status": self.status,
            "compared_players": self.compared_players,
            "only_live_count": self.only_live_count,
            "only_final_count": self.only_final_count,
            "stat_deltas": [delta.to_dict() for delta in self.stat_deltas],
            "stat_comparisons": dict(self.stat_comparisons),
            "stat_exact": dict(self.stat_exact),
            "temporal_gap_seconds": self.temporal_gap_seconds,
            "close_to_final": self.close_to_final,
            "expected_final_window_deltas": self.expected_final_window_deltas,
            "unexplained_deltas": self.unexplained_deltas,
            "expected_final_window_by_field": dict(self.expected_final_window_by_field),
            "unexplained_by_field": dict(self.unexplained_by_field),
            "reason": self.reason,
        }


class FinalMatchVerifier:
    """Keep the latest live CRCON observation and compare it with final API detail."""

    def __init__(
        self,
        *,
        tolerance_seconds: int = FINAL_MATCH_TOLERANCE_SECONDS,
        final_window_seconds: int = FINAL_LIVE_WINDOW_SECONDS,
    ) -> None:
        if tolerance_seconds < 0:
            raise ValueError("tolerance_seconds must be zero or positive.")
        if final_window_seconds < 0:
            raise ValueError("final_window_seconds must be zero or positive.")
        self._tolerance_seconds = tolerance_seconds
        self._final_window_seconds = final_window_seconds
        self._lock = Lock()
        self._last_live: dict[tuple[str, str], CurrentMatchSnapshot] = {}
        self._latest_match: dict[str, str] = {}

    def record_live(self, snapshot: CurrentMatchSnapshot) -> None:
        with self._lock:
            key = (snapshot.server_slug, snapshot.match_id)
            previous = self._last_live.get(key)
            if previous is None or snapshot.observed_at >= previous.observed_at:
                self._last_live[key] = snapshot
                self._latest_match[snapshot.server_slug] = snapshot.match_id

    def verify(
        self,
        *,
        target: ServerTarget,
        api: FinalMatchApi,
        match_id: str | None = None,
    ) -> FinalMatchParityReport:
        with self._lock:
            selected_match = match_id or self._latest_match.get(target.key)
            live = (
                self._last_live.get((target.key, selected_match))
                if selected_match is not None
                else None
            )
        if live is None:
            return _empty_final_report(target.key, "no-live-observation")
        try:
            maps = api.get_scoreboard_maps(page=1, limit=25, server_number=target.server_number)
            match = next(
                (
                    value
                    for value in maps.maps
                    if value.map_id
                    and value.ended_at is not None
                    and (value.server_number is None or value.server_number == target.server_number)
                    and _same_layer(value.layer, live.summary.layer)
                    and _starts_close(value.started_at, live.summary.started_at, self._tolerance_seconds)
                    and live.observed_at
                    <= _utc(value.ended_at) + timedelta(seconds=self._tolerance_seconds)
                ),
                None,
            )
            if match is None or match.map_id is None:
                return _empty_final_report(
                    target.key,
                    "matching-final-map-not-found",
                    observed_at=live.observed_at,
                )
            detail = api.get_map_scoreboard(map_id=match.map_id)
        except Exception:  # noqa: BLE001 - verifier returns diagnostics and never mutates state
            return _empty_final_report(
                target.key,
                "final-api-unavailable",
                observed_at=live.observed_at,
            )

        live_index = _crcon_player_index(live.players)
        final_index = {
            str(player.identity.player_id): player
            for player in detail.players
            if player.identity is not None
        }
        shared = sorted(set(live_index) & set(final_index))
        deltas: list[PlayerStatDelta] = []
        delta_sources: list[tuple[PlayerStatDelta, object]] = []
        stat_comparisons: Counter[str] = Counter()
        stat_exact: Counter[str] = Counter()
        for player_id in shared:
            live_player = live_index[player_id]
            final_player = final_index[player_id]
            for field in STAT_FIELDS:
                left = getattr(live_player, field)
                right = getattr(final_player, field)
                if left is None or right is None:
                    continue
                stat_comparisons[field] += 1
                difference = abs(int(left) - int(right))
                if not difference:
                    stat_exact[field] += 1
                else:
                    delta = PlayerStatDelta(
                            player_key=_opaque_key(player_id),
                            field=field,
                            legacy_value=int(left),
                            crcon_value=int(right),
                            absolute_difference=difference,
                            percentage_difference=_percentage_difference(int(left), int(right)),
                        )
                    deltas.append(delta)
                    delta_sources.append((delta, final_player))
        temporal_gap = None
        if match.ended_at is not None:
            temporal_gap = max(0, int((match.ended_at - live.observed_at).total_seconds()))
        close_to_final = (
            temporal_gap is not None and temporal_gap <= self._final_window_seconds
        )
        expected_deltas = 0
        unexplained_deltas = 0
        expected_by_field: Counter[str] = Counter()
        unexplained_by_field: Counter[str] = Counter()
        live_offset = (
            (live.observed_at - match.started_at).total_seconds()
            if match.started_at is not None
            else None
        )
        for delta, final_player in delta_sources:
            if delta.crcon_value < delta.legacy_value:
                unexplained_deltas += 1
                unexplained_by_field[delta.field] += 1
                continue
            supported_actions = {
                "kills": {"KILL"},
                "deaths": {"DEATH"},
                "teamkills": {"TEAM KILL", "TEAMKILL"},
            }.get(delta.field, set())
            evidenced_events = 0
            if final_player is not None and live_offset is not None and supported_actions:
                evidenced_events = sum(
                    1
                    for encounter in final_player.encounters
                    if str(encounter.action or "").strip().upper() in supported_actions
                    and encounter.timestamp_seconds is not None
                    and encounter.timestamp_seconds > live_offset
                )
            if (
                delta.crcon_value > delta.legacy_value
                and (
                    (not close_to_final)
                    or evidenced_events >= delta.absolute_difference
                )
            ):
                expected_deltas += 1
                expected_by_field[delta.field] += 1
            else:
                unexplained_deltas += 1
                unexplained_by_field[delta.field] += 1
        return FinalMatchParityReport(
            server_key=target.key,
            live_observed_at=live.observed_at,
            map_id=match.map_id,
            status="compared",
            compared_players=len(shared),
            only_live_count=len(set(live_index) - set(final_index)),
            only_final_count=len(set(final_index) - set(live_index)),
            stat_deltas=tuple(deltas[:100]),
            stat_comparisons=tuple(sorted(stat_comparisons.items())),
            stat_exact=tuple(sorted(stat_exact.items())),
            temporal_gap_seconds=temporal_gap,
            close_to_final=close_to_final,
            expected_final_window_deltas=expected_deltas,
            unexplained_deltas=unexplained_deltas,
            expected_final_window_by_field=tuple(sorted(expected_by_field.items())),
            unexplained_by_field=tuple(sorted(unexplained_by_field.items())),
        )


_diagnostic_lock = Lock()
_latest_reports: dict[str, CurrentMatchParityReport] = {}
_final_verifier = FinalMatchVerifier()


def store_current_match_parity(report: CurrentMatchParityReport) -> None:
    with _diagnostic_lock:
        _latest_reports[report.server_key] = report


def get_latest_current_match_parity(server_key: str) -> CurrentMatchParityReport | None:
    with _diagnostic_lock:
        return _latest_reports.get(str(server_key or "").strip())


def get_final_match_verifier() -> FinalMatchVerifier:
    return _final_verifier


def _payload_data(payload: Mapping[str, object] | None) -> Mapping[str, object]:
    if not payload or payload.get("status") != "ok":
        return {}
    data = payload.get("data")
    return data if isinstance(data, Mapping) else {}


def _legacy_player_index(players: Sequence[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    result: dict[str, Mapping[str, object]] = {}
    for player in players:
        player_id = player.get("player_id")
        if player_id is not None and str(player_id).strip():
            result[str(player_id)] = player
    return result


def _crcon_player_index(players: Sequence[CurrentPlayer]) -> dict[str, CurrentPlayer]:
    return {
        str(player.player_id): player
        for player in players
        if player.player_id is not None and str(player.player_id).strip()
    }


def _legacy_player_value(player: Mapping[str, object], field: str) -> object:
    if field == "name":
        return player.get("player_name") if "player_name" in player else player.get("name")
    return player.get(field)


def _opaque_key(player_id: str) -> str:
    return "p:" + hashlib.sha256(_DIAGNOSTIC_SALT + player_id.encode("utf-8")).hexdigest()[:12]


def _percentage_difference(left: int, right: int) -> float | None:
    denominator = max(abs(left), abs(right))
    if denominator == 0:
        return 0.0
    return round(abs(left - right) / denominator * 100, 2)


def _timing_equal(left: object, right: object) -> bool:
    try:
        return abs(float(left) - float(right)) <= MATCH_TIMING_TOLERANCE_SECONDS
    except (TypeError, ValueError):
        left_time = _parse_time(left)
        right_time = _parse_time(right)
        if left_time is None or right_time is None:
            return _comparable_text(left) == _comparable_text(right)
        return abs((left_time - right_time).total_seconds()) <= MATCH_TIMING_TOLERANCE_SECONDS


def _parse_time(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return _utc(value)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return _utc(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        return None


def _comparable_text(value: object) -> str:
    return str(value).strip().casefold()


def _same_layer(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    return _comparable_text(left) == _comparable_text(right)


def _starts_close(left: datetime | None, right: datetime, tolerance: int) -> bool:
    if left is None:
        return True
    return abs((_utc(left) - _utc(right)).total_seconds()) <= tolerance


def _empty_final_report(
    server_key: str,
    reason: str,
    *,
    observed_at: datetime | None = None,
) -> FinalMatchParityReport:
    return FinalMatchParityReport(
        server_key=server_key,
        live_observed_at=observed_at,
        map_id=None,
        status="unavailable",
        compared_players=0,
        only_live_count=0,
        only_final_count=0,
        stat_deltas=(),
        stat_comparisons=(),
        stat_exact=(),
        temporal_gap_seconds=None,
        close_to_final=False,
        expected_final_window_deltas=0,
        unexplained_deltas=0,
        expected_final_window_by_field=(),
        unexplained_by_field=(),
        reason=reason,
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _utc(value).isoformat().replace("+00:00", "Z")


_DIAGNOSTIC_SALT = secrets.token_bytes(16)
