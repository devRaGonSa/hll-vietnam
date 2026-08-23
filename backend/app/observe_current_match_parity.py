"""Bounded, read-only CLI observer for real current-match parity evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from .config import get_crcon_api_timeout_seconds, get_crcon_current_match_bindings
from .crcon import CrconApiClient
from .crcon.dto import CrconLiveGameStats
from .current_match import (
    CrconCurrentMatchBinding,
    CurrentMatchSnapshot,
    CurrentMatchSnapshotService,
    CurrentPlayer,
)
from .current_match_shadow import FinalMatchParityReport, FinalMatchVerifier
from .payloads import (
    _build_legacy_current_match_payload,
    _build_legacy_current_match_player_stats_payload,
)
from .scoreboard_origins import get_trusted_public_scoreboard_origin
from .server_targets import ServerTarget, load_server_targets


DEFAULT_POLL_SECONDS = 3.0
DEFAULT_MAX_DURATION_SECONDS = 300.0
DEFAULT_TIMING_TOLERANCE_SECONDS = 5.0
DEFAULT_TRANSITION_TOLERANCE_SECONDS = 30.0
DEFAULT_STABILIZATION_POLLS = 2
STAT_FIELDS = ("kills", "deaths", "teamkills", "combat", "offense", "defense", "support")
MATCH_FIELDS = (
    "map",
    "layer",
    "game_mode",
    "allied_score",
    "axis_score",
    "player_count",
    "max_players",
    "start_time",
    "time_remaining",
    "status",
)


class MatchLifecycle(StrEnum):
    PRE_MATCH = "PRE_MATCH"
    MATCH_RUNNING = "MATCH_RUNNING"
    MAP_TRANSITION = "MAP_TRANSITION"
    MATCH_ENDED = "MATCH_ENDED"
    NEXT_MATCH = "NEXT_MATCH"


@dataclass(frozen=True, slots=True)
class LifecycleEvent:
    state: MatchLifecycle
    match_id: str | None
    ended_match_id: str | None = None


class MatchStateMachine:
    """Identify match boundaries from layer/start identity, never player count."""

    def __init__(self) -> None:
        self._current_match_id: str | None = None
        self._next_pending = False
        self._ended_without_next = False

    def step(self, snapshot: CurrentMatchSnapshot | None) -> LifecycleEvent:
        match_id = snapshot.match_id if snapshot is not None else None
        if match_id is None:
            if self._current_match_id is None:
                return LifecycleEvent(MatchLifecycle.PRE_MATCH, None)
            ended = self._current_match_id
            self._current_match_id = None
            self._next_pending = False
            self._ended_without_next = True
            return LifecycleEvent(MatchLifecycle.MATCH_ENDED, None, ended)
        if self._current_match_id is None:
            self._current_match_id = match_id
            if self._ended_without_next:
                self._ended_without_next = False
                return LifecycleEvent(MatchLifecycle.NEXT_MATCH, match_id)
            return LifecycleEvent(MatchLifecycle.MATCH_RUNNING, match_id)
        if match_id != self._current_match_id:
            ended = self._current_match_id
            self._current_match_id = match_id
            self._next_pending = True
            return LifecycleEvent(MatchLifecycle.MAP_TRANSITION, match_id, ended)
        if self._next_pending:
            self._next_pending = False
            return LifecycleEvent(MatchLifecycle.NEXT_MATCH, match_id)
        return LifecycleEvent(MatchLifecycle.MATCH_RUNNING, match_id)

    def unavailable(self) -> LifecycleEvent:
        """Preserve lifecycle across transport failure; outage is not match end."""
        return LifecycleEvent(
            MatchLifecycle.MATCH_RUNNING if self._current_match_id else MatchLifecycle.PRE_MATCH,
            self._current_match_id,
        )


@dataclass(slots=True)
class PlayerSetStabilizer:
    stabilization_polls: int = DEFAULT_STABILIZATION_POLLS
    _legacy_runs: dict[str, int] = field(default_factory=dict)
    _crcon_runs: dict[str, int] = field(default_factory=dict)

    def observe(
        self,
        *,
        only_legacy: set[str],
        only_crcon: set[str],
    ) -> dict[str, int]:
        legacy_runs = self._advance(self._legacy_runs, only_legacy)
        crcon_runs = self._advance(self._crcon_runs, only_crcon)
        return {
            "transient_only_legacy": sum(value < self.stabilization_polls for value in legacy_runs.values()),
            "persistent_only_legacy": sum(value >= self.stabilization_polls for value in legacy_runs.values()),
            "transient_only_crcon": sum(value < self.stabilization_polls for value in crcon_runs.values()),
            "persistent_only_crcon": sum(value >= self.stabilization_polls for value in crcon_runs.values()),
        }

    @staticmethod
    def _advance(runs: dict[str, int], current: set[str]) -> dict[str, int]:
        for key in tuple(runs):
            if key not in current:
                del runs[key]
        for key in current:
            runs[key] = runs.get(key, 0) + 1
        return runs


@dataclass(slots=True)
class _Metric:
    comparisons: int = 0
    exact: int = 0
    differing: int = 0
    max_absolute_delta: int = 0
    sum_absolute_delta: int = 0
    eventually_consistent: int = 0
    _difference_runs: dict[str, int] = field(default_factory=dict)
    _systematic: set[str] = field(default_factory=set)

    def observe(self, key: str, left: int, right: int, stabilization_polls: int) -> None:
        self.comparisons += 1
        delta = abs(right - left)
        if delta == 0:
            self.exact += 1
            if self._difference_runs.pop(key, 0) > 0:
                self.eventually_consistent += 1
            self._systematic.discard(key)
            return
        self.differing += 1
        self.max_absolute_delta = max(self.max_absolute_delta, delta)
        self.sum_absolute_delta += delta
        run = self._difference_runs.get(key, 0) + 1
        self._difference_runs[key] = run
        if run >= stabilization_polls:
            self._systematic.add(key)

    def to_dict(self) -> dict[str, object]:
        return {
            "comparisons": self.comparisons,
            "exact": self.exact,
            "differing": self.differing,
            "exact_pct": round(self.exact / self.comparisons * 100, 2) if self.comparisons else None,
            "max_absolute_delta": self.max_absolute_delta,
            "sum_absolute_delta": self.sum_absolute_delta,
            "eventually_consistent": self.eventually_consistent,
            "systematically_different": len(self._systematic),
        }


@dataclass(slots=True)
class TargetEvidence:
    target: ServerTarget
    salt: bytes
    stabilization_polls: int
    polls: int = 0
    synchronized_polls: int = 0
    timing_mismatches: int = 0
    legacy_unavailable: int = 0
    crcon_unavailable: int = 0
    crcon_error_types: Counter[str] = field(default_factory=Counter)
    unique_players: set[str] = field(default_factory=set)
    lifecycle: Counter[str] = field(default_factory=Counter)
    match_fields: dict[str, Counter[str]] = field(
        default_factory=lambda: {name: Counter() for name in MATCH_FIELDS}
    )
    stats: dict[str, _Metric] = field(
        default_factory=lambda: {name: _Metric() for name in STAT_FIELDS}
    )
    player_set_totals: Counter[str] = field(default_factory=Counter)
    transitions: list[dict[str, object]] = field(default_factory=list)
    final_reports: list[FinalMatchParityReport] = field(default_factory=list)
    completed_map_ids: set[str] = field(default_factory=set)
    poll_diagnostics: list[dict[str, object]] = field(default_factory=list)
    stabilizer: PlayerSetStabilizer = field(init=False)
    _transition_started_at: datetime | None = None

    def __post_init__(self) -> None:
        self.stabilizer = PlayerSetStabilizer(self.stabilization_polls)

    def player_key(self, player_id: str) -> str:
        return "p:" + hashlib.sha256(self.salt + player_id.encode("utf-8")).hexdigest()[:12]

    def observe_poll(
        self,
        *,
        now: datetime,
        lifecycle: LifecycleEvent,
        legacy_summary: Mapping[str, object] | None,
        legacy_players: Sequence[Mapping[str, object]],
        legacy_timestamp: datetime | None,
        crcon_snapshot: CurrentMatchSnapshot | None,
        crcon_timestamp: datetime | None,
        timing_tolerance_seconds: float,
        transition_tolerance_seconds: float,
        crcon_error_types: Sequence[str] = (),
    ) -> None:
        self.polls += 1
        self.lifecycle[lifecycle.state.value] += 1
        if legacy_summary is None:
            self.legacy_unavailable += 1
        if crcon_snapshot is None:
            self.crcon_unavailable += 1
        self.crcon_error_types.update(crcon_error_types)
        delta_seconds = _timestamp_delta(legacy_timestamp, crcon_timestamp)
        synchronized = delta_seconds is not None and delta_seconds <= timing_tolerance_seconds
        if synchronized:
            self.synchronized_polls += 1
        elif legacy_summary is not None and crcon_snapshot is not None:
            self.timing_mismatches += 1

        diagnostic = {
            "timestamp": _iso(now),
            "state": lifecycle.state.value,
            "legacy_available": legacy_summary is not None,
            "crcon_available": crcon_snapshot is not None,
            "crcon_error_types": sorted(set(crcon_error_types)),
            "legacy_timestamp": _iso(legacy_timestamp),
            "crcon_timestamp": _iso(crcon_timestamp),
            "timestamp_delta_seconds": delta_seconds,
            "legacy_age_seconds": _age(now, legacy_timestamp),
            "crcon_age_seconds": _age(now, crcon_timestamp),
            "synchronized": synchronized,
        }
        if len(self.poll_diagnostics) < 500:
            self.poll_diagnostics.append(diagnostic)
        if legacy_summary is None or crcon_snapshot is None:
            return

        self._observe_match_fields(
            legacy_summary,
            crcon_snapshot,
            lifecycle=lifecycle.state,
            transition_tolerance_seconds=transition_tolerance_seconds,
            timestamp_delta=delta_seconds,
        )
        if not synchronized:
            return
        legacy_index = _legacy_player_index(legacy_players)
        crcon_index = _crcon_player_index(crcon_snapshot.players)
        legacy_keys = set(legacy_index)
        crcon_keys = set(crcon_index)
        shared = legacy_keys & crcon_keys
        self.unique_players.update(self.player_key(value) for value in legacy_keys | crcon_keys)
        stabilized = self.stabilizer.observe(
            only_legacy={self.player_key(value) for value in legacy_keys - crcon_keys},
            only_crcon={self.player_key(value) for value in crcon_keys - legacy_keys},
        )
        self.player_set_totals.update(stabilized)
        for player_id in shared:
            left = legacy_index[player_id]
            right = crcon_index[player_id]
            key = self.player_key(player_id)
            for field_name in STAT_FIELDS:
                legacy_value = _integer(left.get(field_name))
                crcon_value = _integer(getattr(right, field_name))
                if legacy_value is None or crcon_value is None:
                    continue
                self.stats[field_name].observe(
                    f"{key}:{field_name}",
                    legacy_value,
                    crcon_value,
                    self.stabilization_polls,
                )

    def _observe_match_fields(
        self,
        legacy: Mapping[str, object],
        crcon: CurrentMatchSnapshot,
        *,
        lifecycle: MatchLifecycle,
        transition_tolerance_seconds: float,
        timestamp_delta: float | None,
    ) -> None:
        summary = crcon.summary
        pairs = {
            "map": (legacy.get("map") or legacy.get("map_pretty_name"), summary.map_name),
            "layer": (legacy.get("map_id"), summary.layer),
            "game_mode": (legacy.get("game_mode"), summary.mode),
            "allied_score": (legacy.get("allied_score"), summary.allied_score),
            "axis_score": (legacy.get("axis_score"), summary.axis_score),
            "player_count": (legacy.get("players"), summary.player_count),
            "max_players": (legacy.get("max_players"), summary.max_player_count),
            "start_time": (legacy.get("started_at"), _iso(summary.started_at)),
            "time_remaining": (legacy.get("remaining_match_time_seconds"), summary.remaining_seconds),
            "status": (legacy.get("status"), "degraded" if crcon.degraded else "online"),
        }
        for field_name, (left, right) in pairs.items():
            counter = self.match_fields[field_name]
            if left is None or right is None:
                counter["unavailable"] += 1
                continue
            if field_name == "time_remaining":
                equal = abs(float(left) - float(right)) <= max(5.0, transition_tolerance_seconds)
            elif field_name == "start_time":
                start_delta = _timestamp_delta(_parse_timestamp(left), _parse_timestamp(right))
                if start_delta is None:
                    counter["unavailable"] += 1
                    continue
                equal = start_delta <= 5
            else:
                equal = str(left).strip().casefold() == str(right).strip().casefold()
            if equal:
                counter["exact"] += 1
            elif lifecycle in {MatchLifecycle.MAP_TRANSITION, MatchLifecycle.NEXT_MATCH}:
                counter["expected_transition"] += 1
            elif timestamp_delta is not None and timestamp_delta > transition_tolerance_seconds:
                counter["timing"] += 1
            else:
                counter["different"] += 1

    def add_transition(self, event: LifecycleEvent, now: datetime) -> None:
        if event.state in {MatchLifecycle.MAP_TRANSITION, MatchLifecycle.MATCH_ENDED, MatchLifecycle.NEXT_MATCH}:
            convergence_seconds = None
            if event.state == MatchLifecycle.MAP_TRANSITION:
                self._transition_started_at = now
            elif event.state == MatchLifecycle.NEXT_MATCH and self._transition_started_at is not None:
                convergence_seconds = round(
                    max(0.0, (now - self._transition_started_at).total_seconds()),
                    3,
                )
                self._transition_started_at = None
            self.transitions.append(
                {
                    "state": event.state.value,
                    "timestamp": _iso(now),
                    "ended_match_id": _safe_match_id(event.ended_match_id),
                    "match_id": _safe_match_id(event.match_id),
                    "convergence_seconds": convergence_seconds,
                }
            )

    def add_final_report(self, report: FinalMatchParityReport) -> None:
        if report.status != "compared" or report.map_id is None or report.map_id in self.completed_map_ids:
            return
        self.completed_map_ids.add(report.map_id)
        self.final_reports.append(report)

    def to_dict(self) -> dict[str, object]:
        close_reports = [report for report in self.final_reports if report.close_to_final]
        final_compared = sum(
            dict(report.stat_comparisons).get("kills", 0) for report in close_reports
        )
        final_exact = sum(dict(report.stat_exact).get("kills", 0) for report in close_reports)
        final_different = max(0, final_compared - final_exact)
        return {
            "target": self.target.key,
            "server_number": self.target.server_number,
            "game": self.target.game,
            "polls": self.polls,
            "synchronized_polls": self.synchronized_polls,
            "timing_mismatches": self.timing_mismatches,
            "legacy_unavailable_polls": self.legacy_unavailable,
            "crcon_unavailable_polls": self.crcon_unavailable,
            "crcon_error_types": dict(self.crcon_error_types),
            "players_unique": len(self.unique_players),
            "lifecycle": dict(self.lifecycle),
            "match_parity": {name: dict(counter) for name, counter in self.match_fields.items()},
            "player_set_parity": dict(self.player_set_totals),
            "stats": {name: metric.to_dict() for name, metric in self.stats.items()},
            "transitions": self.transitions,
            "final_scoreboard": {
                "completed_matches": len(self.final_reports),
                "close_to_final_matches": len(close_reports),
                "map_ids": [report.map_id for report in self.final_reports],
                "kills_comparisons": final_compared,
                "kills_exact": final_exact,
                "kills_differing": final_different,
                "kills_exact_pct": (
                    round(final_exact / final_compared * 100, 2)
                    if final_compared
                    else None
                ),
                "expected_final_window_deltas": sum(
                    report.expected_final_window_deltas for report in self.final_reports
                ),
                "unexplained_deltas": sum(report.unexplained_deltas for report in self.final_reports),
                "reports": [report.to_dict() for report in self.final_reports],
            },
            "poll_diagnostics": self.poll_diagnostics,
        }


class _RecordingApi:
    def __init__(self, client: CrconApiClient) -> None:
        self._client = client
        self.live_stats: CrconLiveGameStats | None = None
        self.live_observed_at: datetime | None = None
        self.public_error_type: str | None = None
        self.live_error_type: str | None = None

    def get_public_info(self):
        try:
            result = self._client.get_public_info()
            self.public_error_type = None
            return result
        except Exception as error:
            self.public_error_type = type(error).__name__
            raise

    def get_live_game_stats(self):
        try:
            result = self._client.get_live_game_stats()
            self.live_stats = result
            self.live_observed_at = result.observed_at
            self.live_error_type = None
            return result
        except Exception as error:
            self.live_stats = None
            self.live_error_type = type(error).__name__
            raise

    def get_scoreboard_maps(self, **kwargs: object):
        return self._client.get_scoreboard_maps(**kwargs)

    def get_map_scoreboard(self, **kwargs: object):
        return self._client.get_map_scoreboard(**kwargs)


@dataclass(slots=True)
class _TargetRuntime:
    target: ServerTarget
    api: _RecordingApi
    service: CurrentMatchSnapshotService
    evidence: TargetEvidence
    state_machine: MatchStateMachine = field(default_factory=MatchStateMachine)
    verifier: FinalMatchVerifier = field(default_factory=FinalMatchVerifier)
    pending_final_match_ids: set[str] = field(default_factory=set)


class CurrentMatchParityObserver:
    """Poll multiple HLL targets conservatively and produce sanitized evidence."""

    def __init__(
        self,
        *,
        runtimes: Sequence[_TargetRuntime],
        poll_seconds: float = DEFAULT_POLL_SECONDS,
        max_duration_seconds: float = DEFAULT_MAX_DURATION_SECONDS,
        timing_tolerance_seconds: float = DEFAULT_TIMING_TOLERANCE_SECONDS,
        transition_tolerance_seconds: float = DEFAULT_TRANSITION_TOLERANCE_SECONDS,
        sleep: Any = time.sleep,
        monotonic: Any = time.monotonic,
        now: Any = lambda: datetime.now(UTC),
    ) -> None:
        if poll_seconds < 1:
            raise ValueError("poll_seconds must be at least one second.")
        if max_duration_seconds <= 0:
            raise ValueError("max_duration_seconds must be positive.")
        self._runtimes = tuple(runtimes)
        self._poll_seconds = poll_seconds
        self._max_duration_seconds = max_duration_seconds
        self._timing_tolerance_seconds = timing_tolerance_seconds
        self._transition_tolerance_seconds = transition_tolerance_seconds
        self._sleep = sleep
        self._monotonic = monotonic
        self._now = now

    def run(self) -> dict[str, object]:
        started = self._monotonic()
        interrupted = False
        try:
            while True:
                cycle_started = self._monotonic()
                for runtime in self._runtimes:
                    self._poll_target(runtime)
                elapsed = self._monotonic() - started
                if elapsed >= self._max_duration_seconds:
                    break
                wait = min(
                    self._poll_seconds - (self._monotonic() - cycle_started),
                    self._max_duration_seconds - elapsed,
                )
                if wait > 0:
                    self._sleep(wait)
        except KeyboardInterrupt:
            interrupted = True
        return self._build_report(interrupted=interrupted)

    def _poll_target(self, runtime: _TargetRuntime) -> None:
        now = _utc(self._now())
        legacy_summary = None
        legacy_players: list[Mapping[str, object]] = []
        legacy_timestamp = None
        try:
            legacy_payload = _build_legacy_current_match_payload(server_slug=runtime.target.key)
            data = legacy_payload.get("data")
            if isinstance(data, Mapping) and data.get("found", True):
                legacy_summary = data
                legacy_timestamp = _parse_timestamp(data.get("captured_at") or data.get("updated_at"))
            player_payload = _build_legacy_current_match_player_stats_payload(
                server_slug=runtime.target.key
            )
            player_data = player_payload.get("data")
            if isinstance(player_data, Mapping):
                rows = player_data.get("items")
                if isinstance(rows, list):
                    legacy_players = [row for row in rows if isinstance(row, Mapping)]
                legacy_timestamp = _parse_timestamp(player_data.get("updated_at")) or legacy_timestamp
        except Exception:
            legacy_summary = None
            legacy_players = []

        snapshot = None
        try:
            snapshot = runtime.service.get_snapshot(runtime.target.key)
            snapshot = _with_stateless_live_combat(snapshot, runtime.api.live_stats)
        except Exception:
            pass
        crcon_error_types = tuple(
            value
            for value in (runtime.api.public_error_type, runtime.api.live_error_type)
            if value is not None
        )
        lifecycle = (
            runtime.state_machine.unavailable()
            if snapshot is None and crcon_error_types
            else runtime.state_machine.step(snapshot)
        )
        runtime.evidence.add_transition(lifecycle, now)
        if lifecycle.ended_match_id:
            runtime.pending_final_match_ids.add(lifecycle.ended_match_id)
        if snapshot is not None:
            runtime.verifier.record_live(snapshot)
        for match_id in tuple(runtime.pending_final_match_ids):
            final_report = runtime.verifier.verify(
                target=runtime.target,
                api=runtime.api,
                match_id=match_id,
            )
            if final_report.status == "compared":
                runtime.evidence.add_final_report(final_report)
                runtime.pending_final_match_ids.discard(match_id)
        runtime.evidence.observe_poll(
            now=now,
            lifecycle=lifecycle,
            legacy_summary=legacy_summary,
            legacy_players=legacy_players,
            legacy_timestamp=legacy_timestamp,
            crcon_snapshot=snapshot,
            crcon_timestamp=runtime.api.live_observed_at or (snapshot.observed_at if snapshot else None),
            timing_tolerance_seconds=self._timing_tolerance_seconds,
            transition_tolerance_seconds=self._transition_tolerance_seconds,
            crcon_error_types=crcon_error_types,
        )

    def _build_report(self, *, interrupted: bool) -> dict[str, object]:
        targets = [runtime.evidence.to_dict() for runtime in self._runtimes]
        completed = sum(int(target["final_scoreboard"]["completed_matches"]) for target in targets)
        observed_targets = sum(bool(target["polls"]) for target in targets)
        unexplained = sum(int(target["final_scoreboard"]["unexplained_deltas"]) for target in targets)
        final_comparisons = sum(int(target["final_scoreboard"]["kills_comparisons"]) for target in targets)
        final_exact = sum(int(target["final_scoreboard"]["kills_exact"]) for target in targets)
        map_differences = sum(
            int(target["match_parity"][field_name].get("different", 0))
            for target in targets
            for field_name in ("map", "layer")
        )
        exact_pct = round(final_exact / final_comparisons * 100, 2) if final_comparisons else None
        if completed < 3:
            decision = "INSUFFICIENT EVIDENCE"
        elif (
            observed_targets == len(targets)
            and exact_pct is not None
            and exact_pct >= 99.0
            and unexplained == 0
            and map_differences == 0
        ):
            decision = "GO"
        else:
            decision = "NO-GO"
        return {
            "schema": "hll-current-match-parity-v1",
            "generated_at": _iso(_utc(self._now())),
            "interrupted": interrupted,
            "configuration": {
                "poll_seconds": self._poll_seconds,
                "max_duration_seconds": self._max_duration_seconds,
                "timing_tolerance_seconds": self._timing_tolerance_seconds,
                "transition_tolerance_seconds": self._transition_tolerance_seconds,
                "minimum_complete_matches_for_go": 3,
                "minimum_close_final_kills_exact_pct": 99.0,
            },
            "targets": targets,
            "aggregate": {
                "targets_observed": observed_targets,
                "completed_matches": completed,
                "final_kills_comparisons": final_comparisons,
                "final_kills_exact": final_exact,
                "final_kills_exact_pct": exact_pct,
                "unexplained_final_deltas": unexplained,
                "persistent_map_differences": map_differences,
            },
            "decision": {
                "server_list_hll": "GO",
                "current_match_hll": decision,
                "current_match_hllv": "UNVERIFIED",
            },
        }


def build_runtime(
    target: ServerTarget,
    *,
    headers: Mapping[str, str] | None = None,
    stabilization_polls: int = DEFAULT_STABILIZATION_POLLS,
) -> _TargetRuntime:
    client = CrconApiClient(
        base_url=target.crcon_base_url,
        timeout_seconds=get_crcon_api_timeout_seconds(),
        headers=headers,
    )
    api = _RecordingApi(client)
    binding = CrconCurrentMatchBinding(
        target=ServerTarget(
            key=target.key,
            display_name=target.display_name,
            server_number=target.server_number,
            game=target.game,
            crcon_base_url=target.crcon_base_url,
            enabled=target.enabled,
            capabilities=frozenset({"live_state"}),
        ),
        database_url=None,
        api_headers=dict(headers or {}),
    )
    service = CurrentMatchSnapshotService(
        bindings={target.key: binding},
        api_factory=lambda _binding: api,
        database_factory=lambda _binding: _database_forbidden(),
    )
    return _TargetRuntime(
        target=target,
        api=api,
        service=service,
        evidence=TargetEvidence(
            target=target,
            salt=secrets.token_bytes(16),
            stabilization_polls=stabilization_polls,
        ),
    )


def resolve_target(server_key: str) -> tuple[ServerTarget, Mapping[str, str]]:
    normalized = str(server_key or "").strip()
    configured = load_server_targets().get(normalized)
    if configured is not None:
        return configured, {}
    for binding in get_crcon_current_match_bindings():
        if binding.get("server_slug") == normalized:
            return (
                ServerTarget(
                    key=normalized,
                    display_name=str(binding.get("display_name") or normalized),
                    server_number=int(binding["server_number"]),
                    game=str(binding.get("game") or "hll"),  # type: ignore[arg-type]
                    crcon_base_url=str(binding["api_base_url"]),
                    enabled=bool(binding.get("enabled", True)),
                    capabilities=frozenset({"live_state"}),
                ),
                dict(binding.get("api_headers") or {}),
            )
    trusted = get_trusted_public_scoreboard_origin(normalized)
    if trusted is None:
        raise ValueError("Unknown or unauthorized ServerTarget.")
    return (
        ServerTarget(
            key=trusted.slug,
            display_name=trusted.display_name,
            server_number=trusted.server_number,
            game="hll",
            crcon_base_url=trusted.base_url,
            capabilities=frozenset({"live_state"}),
        ),
        {},
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", action="append", required=True, help="Authorized ServerTarget key; repeatable.")
    parser.add_argument("--poll-seconds", type=float, default=DEFAULT_POLL_SECONDS)
    parser.add_argument("--max-duration", type=float, default=DEFAULT_MAX_DURATION_SECONDS)
    parser.add_argument("--timing-tolerance", type=float, default=DEFAULT_TIMING_TOLERANCE_SECONDS)
    parser.add_argument("--transition-tolerance", type=float, default=DEFAULT_TRANSITION_TOLERANCE_SECONDS)
    parser.add_argument("--stabilization-polls", type=int, default=DEFAULT_STABILIZATION_POLLS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.stabilization_polls < 2:
        parser.error("--stabilization-polls must be at least 2")
    runtimes = []
    for server_key in dict.fromkeys(args.server):
        target, headers = resolve_target(server_key)
        if not target.enabled:
            parser.error(f"ServerTarget is disabled: {server_key}")
        if target.game != "hll":
            parser.error("HLLV must be observed in a separate validation run.")
        runtimes.append(
            build_runtime(
                target,
                headers=headers,
                stabilization_polls=args.stabilization_polls,
            )
        )
    observer = CurrentMatchParityObserver(
        runtimes=runtimes,
        poll_seconds=args.poll_seconds,
        max_duration_seconds=args.max_duration,
        timing_tolerance_seconds=args.timing_tolerance,
        transition_tolerance_seconds=args.transition_tolerance,
    )
    report = observer.run()
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(serialized)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    return 0


def _database_forbidden() -> None:
    raise RuntimeError("CRCON PostgreSQL is forbidden for parity observation.")


def _with_stateless_live_combat(
    snapshot: CurrentMatchSnapshot,
    live_stats: CrconLiveGameStats | None,
) -> CurrentMatchSnapshot:
    """Restore typed API K/D/TK counters for the database-free observer only."""
    if live_stats is None:
        return snapshot
    by_player_id = {
        str(player.identity.player_id): player
        for player in live_stats.players
        if player.identity is not None
    }
    players: list[CurrentPlayer] = []
    for player in snapshot.players:
        live = by_player_id.get(str(player.player_id))
        players.append(
            replace(
                player,
                kills=(
                    live.kills
                    if live is not None and live.kills is not None
                    else player.kills
                ),
                deaths=(
                    live.deaths
                    if live is not None and live.deaths is not None
                    else player.deaths
                ),
                teamkills=(
                    live.teamkills
                    if live is not None and live.teamkills is not None
                    else player.teamkills
                ),
            )
        )
    return replace(snapshot, players=tuple(players))


def _legacy_player_index(players: Sequence[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    return {
        str(row["player_id"]): row
        for row in players
        if row.get("player_id") is not None and str(row.get("player_id")).strip()
    }


def _crcon_player_index(players: Sequence[CurrentPlayer]) -> dict[str, CurrentPlayer]:
    return {
        str(player.player_id): player
        for player in players
        if player.player_id is not None and str(player.player_id).strip()
    }


def _timestamp_delta(left: datetime | None, right: datetime | None) -> float | None:
    if left is None or right is None:
        return None
    return round(abs((_utc(left) - _utc(right)).total_seconds()), 3)


def _age(now: datetime, value: datetime | None) -> float | None:
    if value is None:
        return None
    return round(max(0.0, (_utc(now) - _utc(value)).total_seconds()), 3)


def _parse_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return _utc(value)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return _utc(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        return None


def _integer(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _safe_match_id(value: str | None) -> str | None:
    if not value:
        return None
    return "m:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _utc(value).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
