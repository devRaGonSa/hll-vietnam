from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app import payloads
from app.crcon.dto import CrconMapRef, CrconPublicInfo, CrconScore
from app.server_service import CrconServerListService, build_crcon_server_list_payload
from app.server_targets import ServerTarget, ServerTargetRegistry


NOW = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)


def _target(
    key: str,
    number: int,
    *,
    game: str = "hll",
    enabled: bool = True,
) -> ServerTarget:
    return ServerTarget(
        key=key,
        display_name=f"Server #{number:02d}",
        server_number=number,
        game=game,  # type: ignore[arg-type]
        crcon_base_url=f"https://crcon-{number}.example.test",
        enabled=enabled,
        capabilities=frozenset({"live_state"}),
    )


def _info(*, game: str = "hll", players: int = 42) -> CrconPublicInfo:
    return CrconPublicInfo(
        current_map=CrconMapRef(
            layer="carentan_warfare",
            map_name="Carentan",
            mode="warfare",
            started_at=NOW - timedelta(minutes=20),
        ),
        next_map=CrconMapRef(layer="foy_warfare", map_name="Foy", mode="warfare"),
        score=CrconScore(allied=2, axis=1),
        player_count=players,
        max_player_count=100,
        allied_count=21,
        axis_count=21,
        remaining_seconds=2400,
        server_name="CRCON Public Name",
        game=game,
    )


class _Client:
    def __init__(self, result: CrconPublicInfo | Exception) -> None:
        self.result = result
        self.calls = 0

    def get_public_info(self) -> CrconPublicInfo:
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class CrconServerListTests(unittest.TestCase):
    def test_one_online_target_preserves_frontend_contract(self) -> None:
        target = _target("community-01", 1)
        client = _Client(_info())
        service = CrconServerListService(
            registry=ServerTargetRegistry((target,)),
            client_factory=lambda _target: client,
            now=lambda: NOW,
        )

        payload = build_crcon_server_list_payload(service)
        data = payload["data"]
        item = data["items"][0]

        self.assertEqual(data["source"], "crcon")
        self.assertEqual(data["selected_source"], "crcon")
        self.assertFalse(data["fallback_used"])
        self.assertEqual(item["external_server_id"], "community-01")
        self.assertEqual(item["server_name"], "CRCON Public Name")
        self.assertEqual(item["status"], "online")
        self.assertTrue(item["online"])
        self.assertEqual(item["players"], 42)
        self.assertEqual(item["max_players"], 100)
        self.assertEqual(item["current_map"], "Carentan")
        self.assertEqual(item["game"], "hll")
        self.assertEqual(item["snapshot_origin"], "real-rcon")
        self.assertEqual(item["producer"], "crcon")
        for field in (
            "key",
            "slug",
            "title",
            "display_name",
            "region",
            "freshness",
            "source",
        ):
            self.assertIn(field, item)

    def test_multiple_targets_are_iterated_and_disabled_target_is_skipped(self) -> None:
        targets = (
            _target("community-01", 1),
            _target("community-02", 2),
            _target("community-03", 3, enabled=False),
        )
        calls: list[str] = []

        def factory(target: ServerTarget) -> _Client:
            calls.append(target.key)
            return _Client(_info(players=target.server_number))

        result = CrconServerListService(
            registry=ServerTargetRegistry(targets),
            client_factory=factory,
            now=lambda: NOW,
        ).get_server_list()

        self.assertEqual(calls, ["community-01", "community-02"])
        self.assertEqual([item.target.key for item in result.items], calls)

    def test_hllv_game_comes_from_public_info_without_code_branch(self) -> None:
        target = _target("community-02", 2, game="hllv")
        service = CrconServerListService(
            registry=ServerTargetRegistry((target,)),
            client_factory=lambda _target: _Client(_info(game="hllv")),
            now=lambda: NOW,
        )

        item = build_crcon_server_list_payload(service)["data"]["items"][0]

        self.assertEqual(item["game"], "hllv")
        self.assertEqual(item["server_number"], 2)

    def test_unavailable_target_never_invents_live_values_or_falls_back(self) -> None:
        target = _target("community-01", 1)
        service = CrconServerListService(
            registry=ServerTargetRegistry((target,)),
            client_factory=lambda _target: _Client(TimeoutError("timed out")),
            now=lambda: NOW,
        )

        data = build_crcon_server_list_payload(service)["data"]
        item = data["items"][0]

        self.assertEqual(data["source"], "crcon")
        self.assertFalse(data["fallback_used"])
        self.assertEqual(data["refresh_status"], "failed")
        self.assertEqual(item["status"], "unavailable")
        self.assertIsNone(item["players"])
        self.assertIsNone(item["current_map"])

    def test_failed_refresh_uses_stale_process_local_last_good(self) -> None:
        target = _target("community-01", 1)
        clock = [NOW]
        client = _Client(_info(players=75))
        service = CrconServerListService(
            registry=ServerTargetRegistry((target,)),
            client_factory=lambda _target: client,
            now=lambda: clock[0],
            ttl_seconds=1,
        )
        service.get_server_list()
        clock[0] += timedelta(seconds=2)
        client.result = RuntimeError("offline")

        result = service.get_server_list()
        item = result.items[0]

        self.assertEqual(item.status, "stale")
        self.assertTrue(item.stale)
        self.assertEqual(item.public_info.player_count, 75)
        self.assertEqual(result.refresh_status, "degraded")

    def test_short_ttl_reuses_cached_batch(self) -> None:
        client = _Client(_info())
        service = CrconServerListService(
            registry=ServerTargetRegistry((_target("community-01", 1),)),
            client_factory=lambda _target: client,
            now=lambda: NOW,
        )

        first = service.get_server_list()
        second = service.get_server_list()

        self.assertFalse(first.cache_hit)
        self.assertTrue(second.cache_hit)
        self.assertEqual(client.calls, 1)

    def test_payload_selector_uses_crcon_service_without_legacy_refresh(self) -> None:
        service = CrconServerListService(
            registry=ServerTargetRegistry((_target("community-01", 1),)),
            client_factory=lambda _target: _Client(_info()),
            now=lambda: NOW,
        )
        with (
            patch.object(payloads, "get_server_list_source", return_value="crcon"),
            patch.object(payloads, "get_crcon_server_list_service", return_value=service),
            patch.object(payloads, "_build_legacy_servers_payload") as legacy,
        ):
            result = payloads.build_servers_payload()

        self.assertEqual(result["data"]["source"], "crcon")
        legacy.assert_not_called()


if __name__ == "__main__":
    unittest.main()
