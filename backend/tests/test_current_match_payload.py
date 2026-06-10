from http import HTTPStatus
from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from app import payloads
from app.payloads import build_current_match_payload
from app.rcon_admin_log_storage import list_current_match_player_stats, persist_rcon_admin_log_entries
from app.rcon_client import RconServerTarget
from app.routes import resolve_get_payload


TARGET = RconServerTarget(
    name="Comunidad Hispana #01",
    host="127.0.0.1",
    port=7779,
    password="test-password",
    source_name="test-rcon",
    external_server_id="comunidad-hispana-01",
)


def test_current_match_payload_projects_rich_live_rcon_session_fields():
    data = _build_with_rcon_sample(
        {
            "normalized": {
                "server_name": "Comunidad Hispana #01",
                "status": "online",
                "current_map": "carentan_warfare",
                "game_mode": "Warfare",
                "allied_score": 2,
                "axis_score": 2,
                "allied_players": 0,
                "axis_players": 0,
                "players": 0,
                "max_players": 100,
                "match_time_seconds": 5400,
                "remaining_match_time_seconds": 0,
            },
            "raw_session": {"mapId": "carentan_warfare", "mapName": "CARENTAN"},
        }
    )

    assert data["map"] == "Carentan"
    assert data["map_id"] == "carentan_warfare"
    assert data["map_pretty_name"] == "Carentan"
    assert data["game_mode"] == "Warfare"
    assert data["allied_score"] == 2
    assert data["axis_score"] == 2
    assert data["players"] == 0
    assert data["player_count_quality"] == "rcon-session-unverified"
    assert data["player_count_source"] == "rcon-session"
    assert data["score_source"] == "rcon-session"
    assert data["map_source"] == "rcon-session"
    assert data["public_scoreboard_url"] == "https://scoreboard.comunidadhll.es"
    assert "/games" not in data["public_scoreboard_url"]


def test_current_match_payload_preserves_missing_values_as_null():
    data = _build_with_rcon_sample(
        {
            "normalized": {
                "server_name": "Comunidad Hispana #01",
                "status": "online",
                "current_map": None,
                "game_mode": None,
                "players": None,
                "max_players": None,
            },
            "raw_session": {},
        }
    )

    assert data["map"] is None
    assert data["map_id"] is None
    assert data["game_mode"] is None
    assert data["allied_score"] is None
    assert data["axis_score"] is None
    assert data["players"] is None
    assert data["player_count_quality"] is None
    assert data["player_count_source"] is None
    assert data["score_source"] is None
    assert data["map_source"] is None


def test_current_match_payload_keeps_explicit_zero_score():
    data = _build_with_rcon_sample(
        {
            "normalized": {
                "server_name": "Comunidad Hispana #01",
                "status": "online",
                "current_map": "stmariedumont_warfare",
                "allied_score": 0,
                "axis_score": 0,
            },
            "raw_session": {
                "mapId": "stmariedumont_warfare",
                "mapName": "ST MARIE DU MONT",
            },
        }
    )

    assert data["map"] == "St. Marie Du Mont"
    assert data["allied_score"] == 0
    assert data["axis_score"] == 0
    assert data["score_source"] == "rcon-session"


def test_current_match_payload_fallback_resolves_legacy_rcon_external_id_for_01():
    data = _build_with_snapshot_fallback(
        "comunidad-hispana-01",
        {
            "external_server_id": "rcon:152.114.195.174:7779",
            "server_name": "#01 [ESP] Comunidad Hispana",
            "status": "online",
            "current_map": "St. Marie Du Mont",
            "players": 0,
            "max_players": 100,
            "captured_at": "2026-03-24T14:08:41.008487Z",
        },
    )

    assert data["found"] is True
    assert data["map"] == "St. Marie Du Mont"
    assert data["map_pretty_name"] == "St. Marie Du Mont"
    assert data["status"] == "online"
    assert data["players"] == 0
    assert data["max_players"] == 100
    assert data["captured_at"] == "2026-03-24T14:08:41.008487Z"
    assert data["updated_at"] == "2026-03-24T14:08:41.008487Z"
    assert data["public_scoreboard_url"] == "https://scoreboard.comunidadhll.es"


def test_current_match_payload_fallback_resolves_legacy_rcon_source_ref_for_02():
    data = _build_with_snapshot_fallback(
        "comunidad-hispana-02",
        {
            "external_server_id": "snapshot-server-02",
            "source_ref": "rcon://152.114.195.150:7879",
            "status": "online",
            "current_map": "Elsenborn Ridge",
            "captured_at": "2026-03-24T14:08:41.008487Z",
        },
    )

    assert data["found"] is True
    assert data["server_slug"] == "comunidad-hispana-02"
    assert data["map"] == "Elsenborn Ridge"
    assert data["map_pretty_name"] == "Elsenborn Ridge"
    assert data["public_scoreboard_url"] == "https://scoreboard.comunidadhll.es:5443"


def test_current_match_payload_fallback_resolves_community_server_names():
    number_first = _build_with_snapshot_fallback(
        "comunidad-hispana-01",
        {
            "external_server_id": "snapshot-server-01",
            "server_name": "#01 [ESP] Comunidad Hispana - Spa Onl",
            "current_map": "Mortain",
        },
    )
    community_first = _build_with_snapshot_fallback(
        "comunidad-hispana-02",
        {
            "external_server_id": "snapshot-server-02",
            "name": "Comunidad Hispana #02",
            "current_map": "Carentan",
        },
    )

    assert number_first["found"] is True
    assert number_first["map"] == "Mortain"
    assert community_first["found"] is True
    assert community_first["map"] == "Carentan"


def test_current_match_payload_fallback_does_not_match_unknown_snapshot():
    data = _build_with_snapshot_fallback(
        "comunidad-hispana-01",
        {
            "external_server_id": "rcon:203.0.113.10:9000",
            "source_ref": "rcon://203.0.113.10:9000",
            "server_name": "#03 Comunidad Hispana",
            "current_map": "Unknown Match",
        },
    )

    assert data["found"] is False
    assert data["map"] is None
    assert data["status"] == "unavailable"


def test_current_match_route_rejects_unsupported_server():
    status, payload = resolve_get_payload("/api/current-match?server=not-trusted")

    assert status == HTTPStatus.NOT_FOUND
    assert payload["status"] == "error"


def test_current_match_player_route_rejects_unsupported_server():
    status, payload = resolve_get_payload("/api/current-match/players?server=not-trusted")

    assert status == HTTPStatus.NOT_FOUND
    assert payload["status"] == "error"


def test_current_match_player_stats_aggregate_safe_admin_log_rows(tmp_path):
    db_path = tmp_path / "admin-log.sqlite3"
    persist_rcon_admin_log_entries(
        target={
            "target_key": "comunidad-hispana-01",
            "external_server_id": "comunidad-hispana-01",
        },
        entries=[
            {
                "timestamp": "2026-05-21T10:00:00Z",
                "message": "[1:00 min (100)] MATCH START Mortain Warfare",
            },
            {
                "timestamp": "2026-05-21T10:01:00Z",
                "message": (
                    "[2:00 min (120)] KILL: Bravo(Axis/steam-bravo) -> "
                    "Alpha(Allies/steam-alpha) with MP40"
                ),
            },
            {
                "timestamp": "2026-05-21T10:02:00Z",
                "message": (
                    "[3:00 min (140)] KILL: Alpha(Allies/steam-alpha) -> "
                    "Charlie(Allies/steam-charlie) with M1 GARAND"
                ),
            },
            {
                "timestamp": "2026-05-21T10:03:00Z",
                "message": (
                    "[4:00 min (160)] KILL: Alpha(Allies/steam-alpha) -> "
                    "Bravo(Axis/steam-bravo) with M1 GARAND"
                ),
            },
        ],
        db_path=db_path,
    )

    stats = list_current_match_player_stats(
        server_key="comunidad-hispana-01",
        db_path=db_path,
    )

    assert stats["scope"] == "open-admin-log-match-window"
    assert stats["confidence"] == "admin-log-boundary"
    assert stats["source"] == "rcon-admin-log-current-match-summary"
    assert [item["player_name"] for item in stats["items"]] == ["Alpha", "Bravo", "Charlie"]
    assert stats["items"][0] == {
        "player_name": "Alpha",
        "player_id": "steam-alpha",
        "team": "Allies",
        "kills": 1,
        "deaths": 1,
        "teamkills": 1,
        "deaths_by_teamkill": 0,
        "is_connected": None,
        "connected": None,
        "last_seen_at": "2026-05-21T10:03:00Z",
        "favorite_weapon": "M1 GARAND",
        "source": "kill",
        "confidence": "admin-log-boundary",
    }
    assert "raw_message" not in stats["items"][0]


def test_current_match_player_stats_include_connected_players_without_kills(tmp_path):
    db_path = tmp_path / "admin-log.sqlite3"
    persist_rcon_admin_log_entries(
        target={
            "target_key": "comunidad-hispana-01",
            "external_server_id": "comunidad-hispana-01",
        },
        entries=[
            {
                "timestamp": "2026-05-21T10:00:00Z",
                "message": "[1:00 min (100)] MATCH START Mortain Warfare",
            },
            {
                "timestamp": "2026-05-21T10:01:00Z",
                "message": "[2:00 min (120)] CONNECTED Quiet Player (steam-quiet)",
            },
        ],
        db_path=db_path,
    )

    stats = list_current_match_player_stats(
        server_key="comunidad-hispana-01",
        db_path=db_path,
    )

    assert stats["scope"] == "open-admin-log-match-window"
    assert stats["items"] == [
        {
            "player_name": "Quiet Player",
            "player_id": "steam-quiet",
            "team": None,
            "kills": 0,
            "deaths": 0,
            "teamkills": 0,
            "deaths_by_teamkill": 0,
            "favorite_weapon": None,
            "last_seen_at": "2026-05-21T10:01:00Z",
            "is_connected": True,
            "connected": True,
            "source": "connected",
            "confidence": "admin-log-boundary",
        }
    ]


def test_current_match_player_stats_keep_disconnected_participants_visible(tmp_path):
    db_path = tmp_path / "admin-log.sqlite3"
    persist_rcon_admin_log_entries(
        target={
            "target_key": "comunidad-hispana-01",
            "external_server_id": "comunidad-hispana-01",
        },
        entries=[
            {
                "timestamp": "2026-05-21T10:00:00Z",
                "message": "[1:00 min (100)] MATCH START Mortain Warfare",
            },
            {
                "timestamp": "2026-05-21T10:01:00Z",
                "message": "[2:00 min (120)] CONNECTED Brief Player (steam-brief)",
            },
            {
                "timestamp": "2026-05-21T10:05:00Z",
                "message": "[6:00 min (180)] DISCONNECTED Brief Player (steam-brief)",
            },
        ],
        db_path=db_path,
    )

    stats = list_current_match_player_stats(
        server_key="comunidad-hispana-01",
        db_path=db_path,
    )

    assert stats["items"] == [
        {
            "player_name": "Brief Player",
            "player_id": "steam-brief",
            "team": None,
            "kills": 0,
            "deaths": 0,
            "teamkills": 0,
            "deaths_by_teamkill": 0,
            "favorite_weapon": None,
            "last_seen_at": "2026-05-21T10:05:00Z",
            "is_connected": False,
            "connected": False,
            "source": "connected,disconnected",
            "confidence": "admin-log-boundary",
        }
    ]


def test_current_match_player_stats_include_victim_only_players(tmp_path):
    db_path = tmp_path / "admin-log.sqlite3"
    persist_rcon_admin_log_entries(
        target={
            "target_key": "comunidad-hispana-01",
            "external_server_id": "comunidad-hispana-01",
        },
        entries=[
            {
                "timestamp": "2026-05-21T10:00:00Z",
                "message": "[1:00 min (100)] MATCH START Mortain Warfare",
            },
            {
                "timestamp": "2026-05-21T10:01:00Z",
                "message": (
                    "[2:00 min (120)] KILL: Killer One(Axis/steam-killer) -> "
                    "Victim Only(Allies/steam-victim) with MP40"
                ),
            },
        ],
        db_path=db_path,
    )

    stats = list_current_match_player_stats(
        server_key="comunidad-hispana-01",
        db_path=db_path,
    )
    by_name = {item["player_name"]: item for item in stats["items"]}

    assert by_name["Victim Only"]["kills"] == 0
    assert by_name["Victim Only"]["deaths"] == 1
    assert by_name["Victim Only"]["favorite_weapon"] is None


def test_current_match_player_stats_exclude_players_before_open_match_start(tmp_path):
    db_path = tmp_path / "admin-log.sqlite3"
    persist_rcon_admin_log_entries(
        target={
            "target_key": "comunidad-hispana-01",
            "external_server_id": "comunidad-hispana-01",
        },
        entries=[
            {
                "timestamp": "2026-05-21T09:55:00Z",
                "message": "[0:30 min (90)] CONNECTED Old Match Player (steam-old)",
            },
            {
                "timestamp": "2026-05-21T10:00:00Z",
                "message": "[1:00 min (100)] MATCH START Mortain Warfare",
            },
            {
                "timestamp": "2026-05-21T10:01:00Z",
                "message": "[2:00 min (120)] CONNECTED New Match Player (steam-new)",
            },
        ],
        db_path=db_path,
    )

    stats = list_current_match_player_stats(
        server_key="comunidad-hispana-01",
        db_path=db_path,
    )

    assert [item["player_name"] for item in stats["items"]] == ["New Match Player"]


def test_current_match_player_stats_sort_connected_before_disconnected_with_same_stats(tmp_path):
    db_path = tmp_path / "admin-log.sqlite3"
    persist_rcon_admin_log_entries(
        target={
            "target_key": "comunidad-hispana-01",
            "external_server_id": "comunidad-hispana-01",
        },
        entries=[
            {
                "timestamp": "2026-05-21T10:00:00Z",
                "message": "[1:00 min (100)] MATCH START Mortain Warfare",
            },
            {
                "timestamp": "2026-05-21T10:01:00Z",
                "message": "[2:00 min (120)] CONNECTED Connected Alpha (steam-connected)",
            },
            {
                "timestamp": "2026-05-21T10:02:00Z",
                "message": "[3:00 min (140)] CONNECTED Disconnected Bravo (steam-disconnected)",
            },
            {
                "timestamp": "2026-05-21T10:03:00Z",
                "message": "[4:00 min (160)] DISCONNECTED Disconnected Bravo (steam-disconnected)",
            },
        ],
        db_path=db_path,
    )

    stats = list_current_match_player_stats(
        server_key="comunidad-hispana-01",
        db_path=db_path,
    )

    assert [item["player_name"] for item in stats["items"]] == [
        "Connected Alpha",
        "Disconnected Bravo",
    ]


def test_current_match_player_stats_filter_stale_recent_events(tmp_path):
    db_path = tmp_path / "admin-log.sqlite3"
    persist_rcon_admin_log_entries(
        target={
            "target_key": "comunidad-hispana-01",
            "external_server_id": "comunidad-hispana-01",
        },
        entries=[
            {
                "timestamp": "2026-05-21T09:30:00Z",
                "message": (
                    "[1:00 min (1779355800)] KILL: Old Killer(Allies/steam-old) -> "
                    "Old Victim(Axis/steam-victim-old) with M1 GARAND"
                ),
            }
        ],
        db_path=db_path,
    )

    stats = list_current_match_player_stats(
        server_key="comunidad-hispana-01",
        db_path=db_path,
        now=datetime(2026, 5, 21, 10, 0, tzinfo=timezone.utc),
    )

    assert stats["scope"] == "no-current-match-events"
    assert stats["confidence"] == "stale-filtered"
    assert stats["items"] == []


class CurrentMatchPublicEndpointHardeningTests(unittest.TestCase):
    def test_kill_feed_degrades_when_admin_log_read_fails(self) -> None:
        with patch.object(
            payloads,
            "list_current_match_kill_feed",
            side_effect=TimeoutError("read timed out"),
        ):
            result = payloads.build_current_match_kill_feed_payload(
                server_slug="comunidad-hispana-01",
                limit=30,
            )

        data = result["data"]
        self.assertEqual(result["status"], "ok")
        self.assertEqual(data["items"], [])
        self.assertEqual(data["confidence"], "unavailable")
        self.assertTrue(data["fallback_used"])
        self.assertEqual(data["fallback_reason"], "admin-log-read-timeout")

    def test_player_stats_degrades_when_admin_log_read_fails(self) -> None:
        with patch.object(
            payloads,
            "list_current_match_player_stats",
            side_effect=RuntimeError("no such table: rcon_admin_log_events"),
        ):
            result = payloads.build_current_match_player_stats_payload(
                server_slug="comunidad-hispana-01",
            )

        data = result["data"]
        self.assertEqual(result["status"], "ok")
        self.assertEqual(data["items"], [])
        self.assertEqual(data["updated_at"], None)
        self.assertTrue(data["fallback_used"])
        self.assertEqual(data["fallback_reason"], "admin-log-read-model-unavailable")

    def test_servers_payload_does_not_refresh_live_on_public_get(self) -> None:
        stale_snapshot = {
            "server_name": "Comunidad Hispana #01",
            "external_server_id": "comunidad-hispana-01",
            "captured_at": "2020-01-01T00:00:00Z",
            "snapshot_origin": "real-rcon",
            "current_map": "carentan",
        }
        fake_live_source = type(
            "FakeLiveSource",
            (),
            {"build_target_index": lambda self: {}},
        )()

        with (
            patch.object(payloads, "list_latest_snapshots", return_value=[stale_snapshot]),
            patch.object(payloads, "get_live_data_source", return_value=fake_live_source),
            patch.object(payloads, "_try_collect_real_time_snapshot") as refresh,
        ):
            result = payloads.build_servers_payload()

        refresh.assert_not_called()
        data = result["data"]
        self.assertEqual(result["status"], "ok")
        self.assertEqual(data["items"][0]["external_server_id"], "comunidad-hispana-01")
        self.assertEqual(data["refresh_attempted"], False)
        self.assertEqual(data["refresh_status"], "cache-only")
        self.assertEqual(data["source"], "persisted-stale-snapshot")


def _build_with_rcon_sample(sample: dict[str, object]) -> dict[str, object]:
    with (
        patch("app.payloads.load_rcon_targets", return_value=(TARGET,)),
        patch("app.payloads.query_live_server_sample", return_value=sample),
    ):
        payload = build_current_match_payload(server_slug="comunidad-hispana-01")
    return payload["data"]


def _build_with_snapshot_fallback(
    server_slug: str,
    item: dict[str, object],
) -> dict[str, object]:
    with (
        patch("app.payloads._query_current_match_rcon_sample", return_value=None),
        patch(
            "app.payloads.build_servers_payload",
            return_value={
                "status": "ok",
                "data": {
                    "last_snapshot_at": "2026-03-24T14:08:41.008487Z",
                    "items": [item],
                },
            },
        ),
    ):
        payload = build_current_match_payload(server_slug=server_slug)
    return payload["data"]
