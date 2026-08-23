from __future__ import annotations

import unittest
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from app.api.payloads import current_match as payloads
from app.crcon.dto import (
    CrconHistoricalMap,
    CrconMapPage,
    CrconMapScoreboard,
    CrconPlayerMatchStats,
    parse_map_scoreboard,
    parse_scoreboard_maps,
)
from app.services.current_match import (
    CurrentMatchSnapshot,
    CurrentMatchSummary,
    CurrentPlayer,
    MatchIdentityKind,
    legacy_players_projection,
    legacy_summary_projection,
)
from app.services.current_match_shadow import (
    FinalMatchVerifier,
    ParityClassification,
    compare_current_match,
    get_latest_current_match_parity,
)
from app.domain import PlayerIdentity, PlayerId
from app.server_targets import ServerTarget


NOW = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
START = NOW - timedelta(minutes=30)
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "crcon_12_0_1"


def _player(
    player_id: str,
    *,
    name: str = "Synthetic Player",
    kills: int | None = 10,
    deaths: int | None = 4,
    teamkills: int | None = 0,
) -> CurrentPlayer:
    return CurrentPlayer(
        player_id=player_id,
        name=name,
        team="allies",
        unit="Able",
        role="Rifleman",
        level=50,
        status="connected",
        combat=100,
        offense=20,
        defense=30,
        support=40,
        kills=kills,
        deaths=deaths,
        teamkills=teamkills,
        deaths_by_teamkill=0,
        favorite_weapon=None,
        weapon_counts=(),
    )


def _snapshot(
    players: tuple[CurrentPlayer, ...] = (_player("76561198000000001"),),
    *,
    layer: str = "carentan_warfare",
    allied_score: int | None = 2,
) -> CurrentMatchSnapshot:
    return CurrentMatchSnapshot(
        server_slug="comunidad-hispana-01",
        match_id="crcon:synthetic",
        identity_kind=MatchIdentityKind.EPHEMERAL,
        summary=CurrentMatchSummary(
            server_slug="comunidad-hispana-01",
            server_name="Comunidad Hispana #01",
            map_name="Carentan",
            layer=layer,
            mode="warfare",
            started_at=START,
            allied_score=allied_score,
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
        observed_at=NOW,
        source_states=(),
        degraded=False,
        degraded_reasons=(),
    )


def _legacy(snapshot: CurrentMatchSnapshot) -> tuple[dict[str, object], list[dict[str, object]]]:
    summary = legacy_summary_projection(snapshot)
    players = legacy_players_projection(snapshot)["data"]["items"]
    return summary, players


class CurrentMatchShadowTests(unittest.TestCase):
    def test_identical_sources_have_exact_kills_and_high_confidence(self) -> None:
        snapshot = _snapshot()
        summary, players = _legacy(snapshot)

        report = compare_current_match(
            server_key=snapshot.server_slug,
            legacy_summary=summary,
            legacy_players=players,
            crcon_snapshot=snapshot,
            timestamp=NOW,
        )

        self.assertEqual(report.kills_exact, 1)
        self.assertEqual(report.kills_different, 0)
        self.assertEqual(report.confidence, "high")
        self.assertEqual(report.classification, (ParityClassification.MATCH,))

    def test_kill_difference_records_absolute_and_percentage_delta(self) -> None:
        snapshot = _snapshot()
        summary, players = _legacy(snapshot)
        players[0]["kills"] = 8

        report = compare_current_match(
            server_key=snapshot.server_slug,
            legacy_summary=summary,
            legacy_players=players,
            crcon_snapshot=snapshot,
        )

        kill_delta = next(delta for delta in report.stat_deltas if delta.field == "kills")
        self.assertEqual(kill_delta.absolute_difference, 2)
        self.assertEqual(kill_delta.percentage_difference, 20.0)
        self.assertEqual(report.total_kill_delta, 2)
        self.assertIn(ParityClassification.STAT, report.classification)
        self.assertNotIn("76561198000000001", str(report.to_dict()))

    def test_player_sets_are_compared_by_opaque_id_for_numeric_and_eos_values(self) -> None:
        numeric = "12345678901234567"
        eos = "eos_ABC-def:opaque"
        snapshot = _snapshot((_player(numeric), _player(eos)))
        summary, players = _legacy(snapshot)
        players.pop()
        players.append({**players[0], "player_id": "legacy-only"})

        report = compare_current_match(
            server_key=snapshot.server_slug,
            legacy_summary=summary,
            legacy_players=players,
            crcon_snapshot=snapshot,
        )

        self.assertEqual(report.compared_players, 1)
        self.assertEqual(len(report.only_legacy), 1)
        self.assertEqual(len(report.only_crcon), 1)
        self.assertIn(ParityClassification.PLAYER_SET, report.classification)
        serialized = str(report.to_dict())
        self.assertNotIn(eos, serialized)
        self.assertNotIn("legacy-only", serialized)

    def test_map_transition_and_score_difference_are_match_classified(self) -> None:
        snapshot = _snapshot(layer="carentan_warfare", allied_score=2)
        summary, players = _legacy(snapshot)
        summary["data"]["map_id"] = "foy_warfare"
        summary["data"]["map"] = "Foy"
        summary["data"]["allied_score"] = 1

        report = compare_current_match(
            server_key=snapshot.server_slug,
            legacy_summary=summary,
            legacy_players=players,
            crcon_snapshot=snapshot,
        )

        self.assertIn("map", report.different_match_fields)
        self.assertIn("score_allies", report.different_match_fields)
        self.assertIn(ParityClassification.MATCH, report.classification)

    def test_incomplete_crcon_fields_are_expected_source_differences(self) -> None:
        snapshot = _snapshot((_player("opaque", kills=None),), allied_score=None)
        summary, players = _legacy(_snapshot((_player("opaque"),)))

        report = compare_current_match(
            server_key=snapshot.server_slug,
            legacy_summary=summary,
            legacy_players=players,
            crcon_snapshot=snapshot,
        )

        self.assertIn("score_allies", report.unavailable_match_fields)
        self.assertIn(ParityClassification.EXPECTED_SOURCE_DIFFERENCE, report.classification)

    def test_crcon_or_legacy_unavailable_is_low_confidence_not_an_exception(self) -> None:
        snapshot = _snapshot(())
        report_crcon_down = compare_current_match(
            server_key=snapshot.server_slug,
            legacy_summary=legacy_summary_projection(snapshot),
            legacy_players=[],
            crcon_snapshot=None,
        )
        report_legacy_down = compare_current_match(
            server_key=snapshot.server_slug,
            legacy_summary={"status": "error"},
            legacy_players=[],
            crcon_snapshot=snapshot,
        )

        self.assertEqual(report_crcon_down.confidence, "low")
        self.assertEqual(report_legacy_down.confidence, "low")
        self.assertIn(ParityClassification.UNKNOWN, report_crcon_down.classification)
        self.assertIn(ParityClassification.UNKNOWN, report_legacy_down.classification)

    def test_empty_server_is_comparable(self) -> None:
        snapshot = _snapshot(())
        summary, players = _legacy(snapshot)

        report = compare_current_match(
            server_key=snapshot.server_slug,
            legacy_summary=summary,
            legacy_players=players,
            crcon_snapshot=snapshot,
        )

        self.assertEqual(report.legacy_player_count, 0)
        self.assertEqual(report.crcon_player_count, 0)
        self.assertEqual(report.confidence, "high")

    def test_reconnect_name_change_does_not_break_id_matching(self) -> None:
        snapshot = _snapshot((_player("opaque-id", name="New Name"),))
        summary, players = _legacy(snapshot)
        players[0]["player_name"] = "Old Name"

        report = compare_current_match(
            server_key=snapshot.server_slug,
            legacy_summary=summary,
            legacy_players=players,
            crcon_snapshot=snapshot,
        )

        self.assertEqual(report.compared_players, 1)
        self.assertEqual(report.only_legacy, ())
        self.assertEqual(report.only_crcon, ())
        self.assertIn(ParityClassification.EXPECTED_SOURCE_DIFFERENCE, report.classification)

    def test_shadow_mode_returns_exact_legacy_payload_and_stores_diagnostic(self) -> None:
        snapshot = _snapshot()
        legacy_summary, _players = _legacy(snapshot)
        legacy_player_payload = legacy_players_projection(snapshot)
        service = unittest.mock.Mock()
        service.get_snapshot.return_value = snapshot

        with (
            patch.object(payloads, "get_current_match_source", return_value="shadow"),
            patch.object(
                payloads,
                "_build_legacy_current_match_payload",
                return_value=legacy_summary,
            ),
            patch.object(
                payloads,
                "_build_legacy_current_match_player_stats_payload",
                return_value=legacy_player_payload,
            ),
            patch.object(payloads, "get_current_match_snapshot_service", return_value=service),
        ):
            result = payloads.build_current_match_payload(
                server_slug="comunidad-hispana-01"
            )

        self.assertIs(result, legacy_summary)
        self.assertIsNotNone(get_latest_current_match_parity("comunidad-hispana-01"))


class _FinalApi:
    def __init__(self, page: CrconMapPage, detail: CrconMapScoreboard) -> None:
        self.page = page
        self.detail = detail
        self.requested_map_id: str | None = None

    def get_scoreboard_maps(self, **_kwargs: object) -> CrconMapPage:
        return self.page

    def get_map_scoreboard(self, *, map_id: int | str) -> CrconMapScoreboard:
        self.requested_map_id = str(map_id)
        return self.detail


class FinalMatchVerifierTests(unittest.TestCase):
    def test_verified_1201_final_fixture_compares_with_last_live_observation(self) -> None:
        page_payload = json.loads((FIXTURE_DIR / "scoreboard_maps.json").read_text(encoding="utf-8"))
        detail_payload = json.loads((FIXTURE_DIR / "map_scoreboard.json").read_text(encoding="utf-8"))
        page = parse_scoreboard_maps(page_payload["result"])
        detail = parse_map_scoreboard(detail_payload["result"])
        live = _snapshot(
            (
                replace(
                    _player("opaque-player-001", kills=13, deaths=9, teamkills=1),
                    combat=139,
                    offense=320,
                    defense=80,
                    support=210,
                ),
            ),
            layer="synthetic_valley_offensive",
            allied_score=5,
        )
        live = replace(
            live,
            observed_at=datetime(2026, 8, 21, 9, 29, 50, tzinfo=UTC),
            summary=replace(
                live.summary,
                started_at=datetime(2026, 8, 21, 8, 0, tzinfo=UTC),
                layer="synthetic_valley_offensive",
                map_name="Synthetic Valley Offensive",
            ),
        )
        verifier = FinalMatchVerifier(tolerance_seconds=60)
        verifier.record_live(live)

        report = verifier.verify(
            target=ServerTarget(
                key="comunidad-hispana-01",
                display_name="Server #01",
                server_number=1,
                game="hll",
                crcon_base_url="https://crcon.example.test",
            ),
            api=_FinalApi(page, detail),
        )

        self.assertEqual(report.map_id, "9001")
        self.assertEqual(report.temporal_gap_seconds, 10)
        self.assertIn(("kills", 1), {(delta.field, delta.absolute_difference) for delta in report.stat_deltas})
        self.assertIn(("combat", 1), {(delta.field, delta.absolute_difference) for delta in report.stat_deltas})

    def test_last_live_observation_is_compared_with_final_map_scoreboard(self) -> None:
        player_id = "eos_synthetic-final"
        live = _snapshot((_player(player_id, kills=10, deaths=4),))
        final_match = CrconHistoricalMap(
            map_id="9002",
            server_number=1,
            game="hll",
            layer="carentan_warfare",
            map_name="Carentan",
            mode="warfare",
            started_at=START + timedelta(seconds=20),
            ended_at=NOW + timedelta(seconds=45),
        )
        identity = PlayerIdentity(player_id=PlayerId(player_id), display_name="Synthetic")
        api = _FinalApi(
            CrconMapPage(maps=(final_match,)),
            CrconMapScoreboard(
                match=final_match,
                players=(
                    CrconPlayerMatchStats(
                        identity=identity,
                        name="Synthetic",
                        kills=12,
                        deaths=5,
                        teamkills=0,
                        combat=100,
                        offense=20,
                        defense=30,
                        support=40,
                    ),
                ),
            ),
        )
        verifier = FinalMatchVerifier(tolerance_seconds=60)
        verifier.record_live(live)

        report = verifier.verify(
            target=ServerTarget(
                key="comunidad-hispana-01",
                display_name="Server #01",
                server_number=1,
                game="hll",
                crcon_base_url="https://crcon.example.test",
            ),
            api=api,
        )

        self.assertEqual(report.status, "compared")
        self.assertEqual(api.requested_map_id, "9002")
        self.assertEqual(report.compared_players, 1)
        self.assertEqual(report.temporal_gap_seconds, 45)
        self.assertEqual(
            {(delta.field, delta.absolute_difference) for delta in report.stat_deltas},
            {("kills", 2), ("deaths", 1)},
        )
        self.assertNotIn(player_id, str(report.to_dict()))


if __name__ == "__main__":
    unittest.main()
