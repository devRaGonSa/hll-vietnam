from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from app.crcon.dto import (
    CrconEncounter,
    CrconHistoricalMap,
    CrconLiveGameStats,
    CrconLivePlayer,
    CrconMapPage,
    CrconMapScoreboard,
    CrconPlayerMatchStats,
)
from app.current_match import (
    CurrentMatchSnapshot,
    CurrentMatchSummary,
    CurrentPlayer,
    MatchIdentityKind,
)
from app.current_match_shadow import FinalMatchVerifier
from app.domain import PlayerId, PlayerIdentity
from app.observe_current_match_parity import (
    CurrentMatchParityObserver,
    LifecycleEvent,
    MatchLifecycle,
    MatchStateMachine,
    PlayerSetStabilizer,
    TargetEvidence,
    _TargetRuntime,
    _with_stateless_live_combat,
)
from app.server_targets import ServerTarget


NOW = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
START = NOW - timedelta(minutes=30)


def _target(key: str = "community-01", number: int = 1) -> ServerTarget:
    return ServerTarget(
        key=key,
        display_name=key,
        server_number=number,
        game="hll",
        crcon_base_url=f"https://{key}.example.test",
        capabilities=frozenset({"live_state"}),
    )


def _player(player_id: str, *, kills: int = 10, combat: int = 100) -> CurrentPlayer:
    return CurrentPlayer(
        player_id=player_id,
        name="Synthetic",
        team="allies",
        unit="Able",
        role="Rifleman",
        level=50,
        status="connected",
        combat=combat,
        offense=20,
        defense=30,
        support=40,
        kills=kills,
        deaths=4,
        teamkills=0,
        deaths_by_teamkill=0,
        favorite_weapon=None,
        weapon_counts=(),
    )


def _snapshot(
    match_id: str = "match-a",
    *,
    layer: str = "carentan_warfare",
    players: tuple[CurrentPlayer, ...] = (_player("opaque-a"),),
    observed_at: datetime = NOW,
) -> CurrentMatchSnapshot:
    return CurrentMatchSnapshot(
        server_slug="community-01",
        match_id=match_id,
        identity_kind=MatchIdentityKind.EPHEMERAL,
        summary=CurrentMatchSummary(
            server_slug="community-01",
            server_name="Community",
            map_name="Carentan",
            layer=layer,
            mode="warfare",
            started_at=START,
            allied_score=2,
            axis_score=1,
            remaining_seconds=1800,
            player_count=len(players),
            max_player_count=100,
            allied_count=len(players),
            axis_count=0,
        ),
        players=players,
        kills=(),
        killfeed_truncated=False,
        version="v1",
        observed_at=observed_at,
        source_states=(),
        degraded=False,
        degraded_reasons=(),
    )


def _legacy_player(player_id: str, *, kills: int = 10, combat: int = 100) -> dict[str, object]:
    return {
        "player_id": player_id,
        "player_name": "Synthetic",
        "kills": kills,
        "deaths": 4,
        "teamkills": 0,
        "combat": combat,
        "offense": 20,
        "defense": 30,
        "support": 40,
    }


def _legacy_summary(snapshot: CurrentMatchSnapshot) -> dict[str, object]:
    return {
        "map": snapshot.summary.map_name,
        "map_id": snapshot.summary.layer,
        "game_mode": snapshot.summary.mode,
        "allied_score": snapshot.summary.allied_score,
        "axis_score": snapshot.summary.axis_score,
        "players": snapshot.summary.player_count,
        "max_players": snapshot.summary.max_player_count,
        "started_at": START.isoformat(),
        "remaining_match_time_seconds": snapshot.summary.remaining_seconds,
        "status": "online",
    }


class MatchStateMachineTests(unittest.TestCase):
    def test_start_transition_end_and_next_match_states(self) -> None:
        machine = MatchStateMachine()

        self.assertEqual(machine.step(None).state, MatchLifecycle.PRE_MATCH)
        self.assertEqual(machine.step(_snapshot()).state, MatchLifecycle.MATCH_RUNNING)
        transition = machine.step(_snapshot("match-b", layer="foy_warfare"))
        self.assertEqual(transition.state, MatchLifecycle.MAP_TRANSITION)
        self.assertEqual(transition.ended_match_id, "match-a")
        self.assertEqual(
            machine.step(_snapshot("match-b", layer="foy_warfare")).state,
            MatchLifecycle.NEXT_MATCH,
        )
        ended = machine.step(None)
        self.assertEqual(ended.state, MatchLifecycle.MATCH_ENDED)
        self.assertEqual(ended.ended_match_id, "match-b")
        self.assertEqual(
            machine.step(_snapshot("match-c", layer="kursk_warfare")).state,
            MatchLifecycle.NEXT_MATCH,
        )

    def test_player_count_change_never_creates_new_match(self) -> None:
        machine = MatchStateMachine()
        machine.step(_snapshot(players=(_player("a"),)))
        same_identity = _snapshot(players=(_player("a"), _player("b")))

        self.assertEqual(machine.step(same_identity).state, MatchLifecycle.MATCH_RUNNING)

    def test_transport_outage_never_marks_running_match_ended(self) -> None:
        machine = MatchStateMachine()
        machine.step(_snapshot())

        outage = machine.unavailable()
        recovered = machine.step(_snapshot())

        self.assertEqual(outage.state, MatchLifecycle.MATCH_RUNNING)
        self.assertIsNone(outage.ended_match_id)
        self.assertEqual(recovered.state, MatchLifecycle.MATCH_RUNNING)


class StabilizationTests(unittest.TestCase):
    def test_single_poll_churn_is_transient_and_repeated_churn_persistent(self) -> None:
        stabilizer = PlayerSetStabilizer(stabilization_polls=2)

        first = stabilizer.observe(only_legacy={"p:a"}, only_crcon=set())
        second = stabilizer.observe(only_legacy={"p:a"}, only_crcon={"p:b"})

        self.assertEqual(first["transient_only_legacy"], 1)
        self.assertEqual(first["persistent_only_legacy"], 0)
        self.assertEqual(second["persistent_only_legacy"], 1)
        self.assertEqual(second["transient_only_crcon"], 1)


class TargetEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence = TargetEvidence(
            target=_target(),
            salt=b"execution-salt",
            stabilization_polls=2,
        )

    def observe(
        self,
        *,
        snapshot: CurrentMatchSnapshot | None,
        legacy_players: list[dict[str, object]],
        legacy_time: datetime | None = NOW,
        crcon_time: datetime | None = NOW,
        legacy_summary: dict[str, object] | None = None,
    ) -> None:
        self.evidence.observe_poll(
            now=NOW,
            lifecycle=LifecycleEvent(
                MatchLifecycle.MATCH_RUNNING if snapshot else MatchLifecycle.PRE_MATCH,
                snapshot.match_id if snapshot else None,
            ),
            legacy_summary=(
                legacy_summary
                if legacy_summary is not None
                else _legacy_summary(snapshot) if snapshot else None
            ),
            legacy_players=legacy_players,
            legacy_timestamp=legacy_time,
            crcon_snapshot=snapshot,
            crcon_timestamp=crcon_time,
            timing_tolerance_seconds=5,
            transition_tolerance_seconds=30,
        )

    def test_exact_kills_deaths_teamkills_and_scores(self) -> None:
        self.observe(snapshot=_snapshot(), legacy_players=[_legacy_player("opaque-a")])
        result = self.evidence.to_dict()

        for field in ("kills", "deaths", "teamkills", "combat", "offense", "defense", "support"):
            self.assertEqual(result["stats"][field]["exact"], 1)

    def test_delayed_kill_converges_on_later_poll(self) -> None:
        self.observe(
            snapshot=_snapshot(players=(_player("opaque-a", kills=10),)),
            legacy_players=[_legacy_player("opaque-a", kills=9)],
        )
        self.observe(
            snapshot=_snapshot(players=(_player("opaque-a", kills=10),)),
            legacy_players=[_legacy_player("opaque-a", kills=10)],
        )

        kills = self.evidence.to_dict()["stats"]["kills"]
        self.assertEqual(kills["differing"], 1)
        self.assertEqual(kills["eventually_consistent"], 1)
        self.assertEqual(kills["systematically_different"], 0)

    def test_score_dimension_converges_on_later_poll(self) -> None:
        self.observe(
            snapshot=_snapshot(players=(_player("opaque-a", combat=110),)),
            legacy_players=[_legacy_player("opaque-a", combat=100)],
        )
        self.observe(
            snapshot=_snapshot(players=(_player("opaque-a", combat=110),)),
            legacy_players=[_legacy_player("opaque-a", combat=110)],
        )

        combat = self.evidence.to_dict()["stats"]["combat"]
        self.assertEqual(combat["eventually_consistent"], 1)
        self.assertEqual(combat["systematically_different"], 0)

    def test_transition_records_bounded_convergence_time(self) -> None:
        self.evidence.add_transition(
            LifecycleEvent(MatchLifecycle.MAP_TRANSITION, "next", "previous"),
            NOW,
        )
        self.evidence.add_transition(
            LifecycleEvent(MatchLifecycle.NEXT_MATCH, "next"),
            NOW + timedelta(seconds=6),
        )

        transitions = self.evidence.to_dict()["transitions"]
        self.assertEqual(transitions[-1]["convergence_seconds"], 6.0)
        self.assertNotIn("previous", str(transitions))

    def test_repeated_kill_loss_is_systematic(self) -> None:
        for _ in range(2):
            self.observe(
                snapshot=_snapshot(players=(_player("opaque-a", kills=8),)),
                legacy_players=[_legacy_player("opaque-a", kills=10)],
            )

        kills = self.evidence.to_dict()["stats"]["kills"]
        self.assertEqual(kills["systematically_different"], 1)
        self.assertEqual(kills["max_absolute_delta"], 2)

    def test_timing_mismatch_does_not_create_false_stat_difference(self) -> None:
        self.observe(
            snapshot=_snapshot(players=(_player("opaque-a", kills=20),)),
            legacy_players=[_legacy_player("opaque-a", kills=1)],
            legacy_time=NOW - timedelta(seconds=20),
        )

        result = self.evidence.to_dict()
        self.assertEqual(result["timing_mismatches"], 1)
        self.assertEqual(result["stats"]["kills"]["comparisons"], 0)

    def test_unavailable_sources_are_counted_without_exception(self) -> None:
        self.observe(snapshot=None, legacy_players=[])
        self.observe(
            snapshot=_snapshot(),
            legacy_players=[],
            legacy_summary=None,
            legacy_time=None,
        )

        result = self.evidence.to_dict()
        self.assertGreaterEqual(result["legacy_unavailable_polls"], 1)
        self.assertGreaterEqual(result["crcon_unavailable_polls"], 1)

    def test_diagnostics_never_contain_raw_player_id_or_name(self) -> None:
        raw_id = "76561198000000001"
        self.observe(
            snapshot=_snapshot(players=(_player(raw_id),)),
            legacy_players=[_legacy_player(raw_id)],
        )

        serialized = str(self.evidence.to_dict())
        self.assertNotIn(raw_id, serialized)
        self.assertNotIn("Synthetic", serialized)


class StatelessLiveCombatTests(unittest.TestCase):
    def test_observer_restores_typed_live_kills_without_database(self) -> None:
        snapshot = _snapshot(
            players=(
                replace(
                    _player("opaque-live"),
                    kills=None,
                    deaths=None,
                    teamkills=None,
                ),
            )
        )
        live = CrconLiveGameStats(
            players=(
                CrconLivePlayer(
                    identity=PlayerIdentity(PlayerId("opaque-live"), display_name="Synthetic"),
                    kills=12,
                    deaths=5,
                    teamkills=1,
                ),
            ),
            observed_at=NOW,
        )

        result = _with_stateless_live_combat(snapshot, live)

        self.assertEqual(
            (result.players[0].kills, result.players[0].deaths, result.players[0].teamkills),
            (12, 5, 1),
        )
        self.assertIsNone(snapshot.players[0].kills)


class _FinalApi:
    def __init__(self, match: CrconHistoricalMap, final_player: CrconPlayerMatchStats) -> None:
        self.match = match
        self.final_player = final_player

    def get_scoreboard_maps(self, **_kwargs: object) -> CrconMapPage:
        return CrconMapPage(maps=(self.match,))

    def get_map_scoreboard(self, **_kwargs: object) -> CrconMapScoreboard:
        return CrconMapScoreboard(match=self.match, players=(self.final_player,))


class FinalWindowTests(unittest.TestCase):
    def _verify(self, *, encounters: tuple[CrconEncounter, ...]) -> object:
        live = _snapshot(
            players=(_player("opaque-final", kills=10),),
            observed_at=NOW - timedelta(seconds=10),
        )
        match = CrconHistoricalMap(
            map_id="9001",
            server_number=1,
            game="hll",
            layer="carentan_warfare",
            started_at=START,
            ended_at=NOW,
        )
        final_player = CrconPlayerMatchStats(
            identity=PlayerIdentity(PlayerId("opaque-final"), display_name="Synthetic"),
            kills=11,
            deaths=4,
            teamkills=0,
            combat=100,
            offense=20,
            defense=30,
            support=40,
            encounters=encounters,
        )
        verifier = FinalMatchVerifier(tolerance_seconds=60, final_window_seconds=30)
        verifier.record_live(live)
        return verifier.verify(target=_target(), api=_FinalApi(match, final_player))

    def test_event_after_last_poll_explains_final_kill_delta(self) -> None:
        report = self._verify(
            encounters=(
                CrconEncounter(action="KILL", timestamp_seconds=1795),
            )
        )

        self.assertTrue(report.close_to_final)
        self.assertEqual(report.expected_final_window_deltas, 1)
        self.assertEqual(report.unexplained_deltas, 0)

    def test_final_kill_delta_without_later_event_is_unexplained(self) -> None:
        report = self._verify(encounters=())

        self.assertEqual(report.expected_final_window_deltas, 0)
        self.assertEqual(report.unexplained_deltas, 1)


class ObserverDecisionTests(unittest.TestCase):
    def test_no_completed_match_is_insufficient_for_multiple_targets(self) -> None:
        runtimes = []
        for key, number in (("community-01", 1), ("community-02", 2)):
            target = _target(key, number)
            runtimes.append(
                _TargetRuntime(
                    target=target,
                    api=object(),  # type: ignore[arg-type]
                    service=object(),  # type: ignore[arg-type]
                    evidence=TargetEvidence(
                        target=target,
                        salt=f"salt-{number}".encode(),
                        stabilization_polls=2,
                        polls=1,
                    ),
                )
            )
        observer = CurrentMatchParityObserver(
            runtimes=runtimes,
            max_duration_seconds=1,
        )

        report = observer._build_report(interrupted=False)

        self.assertEqual(report["aggregate"]["targets_observed"], 2)
        self.assertEqual(report["decision"]["current_match_hll"], "INSUFFICIENT EVIDENCE")
        self.assertEqual(report["decision"]["current_match_hllv"], "UNVERIFIED")
        self.assertEqual(report["decision"]["server_list_hll"], "GO")


if __name__ == "__main__":
    unittest.main()
