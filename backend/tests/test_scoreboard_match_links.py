"""Regression checks for persisted public-scoreboard match links."""

from __future__ import annotations

import gc
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.scoreboard_candidate_backfill import run_backfill
from app.historical_storage import (
    get_historical_match_detail,
    initialize_historical_storage,
    list_recent_historical_matches,
    upsert_historical_match,
)
from app.rcon_historical_storage import initialize_rcon_historical_storage
from app.rcon_historical_storage import persist_rcon_historical_sample
from app.rcon_historical_storage import start_rcon_historical_capture_run
from app.rcon_historical_read_model import get_rcon_historical_match_detail
from app.rcon_admin_log_materialization import materialize_rcon_admin_log
from app.rcon_admin_log_storage import persist_rcon_admin_log_entries
from app.rcon_scoreboard_relink import relink_materialized_matches
from app.scoreboard_correlation_diagnostics import inspect_materialized_match_correlation


class PersistedScoreboardMatchLinkTests(unittest.TestCase):
    def test_list_backfill_persists_foy_candidate_before_detail_fetch_failure(self) -> None:
        stored: dict[tuple[str, str], dict[str, object]] = {}

        class FoyListProvider:
            def fetch_match_page(self, *, base_url: str, page: int, limit: int) -> dict[str, object]:
                return {"maps": [_foy_list_match()]} if page == 1 else {"maps": []}

            def fetch_match_details(
                self,
                *,
                base_url: str,
                match_ids: list[str],
                max_workers: int,
            ) -> list[dict[str, object]]:
                raise RuntimeError("detail endpoint unavailable")

        def fake_upsert(*, server_slug: str, candidate: dict[str, object]) -> str:
            key = (server_slug, str(candidate["external_match_id"]))
            outcome = "updated" if key in stored else "inserted"
            stored[key] = dict(candidate)
            return outcome

        server = {
            "slug": "comunidad-hispana-02",
            "scoreboard_base_url": "https://scoreboard.comunidadhll.es:5443",
            "server_number": 2,
        }
        with (
            patch("app.scoreboard_candidate_backfill.initialize_historical_storage"),
            patch(
                "app.scoreboard_candidate_backfill.PublicScoreboardHistoricalDataSource",
                return_value=FoyListProvider(),
            ),
            patch(
                "app.scoreboard_candidate_backfill.upsert_scoreboard_candidate",
                side_effect=fake_upsert,
            ),
        ):
            first = run_backfill(
                server=server,
                start_at=_backfill_timestamp("2026-05-20T00:00:00Z"),
                end_at=_backfill_timestamp("2026-05-21T23:59:59Z"),
                max_pages=2,
                page_size=100,
                detail_workers=1,
            )
            second = run_backfill(
                server=server,
                start_at=_backfill_timestamp("2026-05-20T00:00:00Z"),
                end_at=_backfill_timestamp("2026-05-21T23:59:59Z"),
                max_pages=2,
                page_size=100,
                detail_workers=1,
            )

        candidate = stored[("comunidad-hispana-02", "1562115")]
        self.assertEqual(
            candidate["match_url"],
            "https://scoreboard.comunidadhll.es:5443/games/1562115",
        )
        self.assertEqual(first["list_candidates_inserted"], 1)
        self.assertEqual(first["list_candidates_updated"], 0)
        self.assertEqual(first["errors"][0]["stage"], "fetch_match_details")
        self.assertEqual(second["list_candidates_inserted"], 0)
        self.assertEqual(second["list_candidates_updated"], 1)
        self.assertEqual(len(stored), 1)

    def test_recent_and_detail_payloads_expose_safe_persisted_match_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            match_url = "https://scoreboard.comunidadhll.es:5443/games/12345"
            _persist_match(db_path, server_slug="comunidad-hispana-02", match_id="12345")

            recent_items = list_recent_historical_matches(
                server_slug="comunidad-hispana-02",
                limit=5,
                db_path=db_path,
            )
            detail = get_historical_match_detail(
                server_slug="comunidad-hispana-02",
                match_id="12345",
                db_path=db_path,
            )

            self.assertEqual(recent_items[0]["match_url"], match_url)
            self.assertIsNotNone(detail)
            self.assertEqual(detail["match_url"], match_url)
            gc.collect()

    def test_untrusted_persisted_match_url_is_not_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            _persist_match(db_path, server_slug="comunidad-hispana-01", match_id="999")
            _set_raw_payload_ref(
                db_path,
                match_id="999",
                raw_payload_ref="https://scoreboard.comunidadhll.es:3443/games/999",
            )

            recent_items = list_recent_historical_matches(
                server_slug="comunidad-hispana-01",
                limit=5,
                db_path=db_path,
            )
            detail = get_historical_match_detail(
                server_slug="comunidad-hispana-01",
                match_id="999",
                db_path=db_path,
            )

            self.assertIsNone(recent_items[0]["match_url"])
            self.assertIsNotNone(detail)
            self.assertIsNone(detail["match_url"])
            gc.collect()

    def test_detail_player_links_use_trusted_scoreboard_steam_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            _persist_match(
                db_path,
                server_slug="comunidad-hispana-02",
                match_id="steam-player-match",
                player_stats=[
                    {
                        "player": "Steam Player",
                        "steaminfo": {"profile": {"steamid": "76561198000000009"}},
                        "team": {"side": "allies"},
                        "kills": 4,
                        "deaths": 2,
                    }
                ],
            )

            detail = get_historical_match_detail(
                server_slug="comunidad-hispana-02",
                match_id="steam-player-match",
                db_path=db_path,
            )

            self.assertIsNotNone(detail)
            player = detail["players"][0]
            self.assertEqual(player["steam_id_64"], "76561198000000009")
            self.assertEqual(player["platform"], "steam")
            self.assertEqual(
                player["external_profile_links"]["hll_records"],
                "https://hllrecords.com/profiles/76561198000000009",
            )
            gc.collect()

    def test_rcon_match_detail_does_not_fabricate_external_scoreboard_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            previous_storage_path = os.environ.get("HLL_BACKEND_STORAGE_PATH")
            os.environ["HLL_BACKEND_STORAGE_PATH"] = str(db_path)
            try:
                initialize_rcon_historical_storage(db_path=db_path)
                detail = get_rcon_historical_match_detail(
                    server_key="comunidad-hispana-01",
                    match_id="rcon:synthetic-window",
                )
            finally:
                if previous_storage_path is None:
                    os.environ.pop("HLL_BACKEND_STORAGE_PATH", None)
                else:
                    os.environ["HLL_BACKEND_STORAGE_PATH"] = previous_storage_path

            self.assertIsNone(detail)
            gc.collect()

    def test_rcon_match_detail_exposes_correlated_scoreboard_url_on_strong_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            previous_storage_path = os.environ.get("HLL_BACKEND_STORAGE_PATH")
            os.environ["HLL_BACKEND_STORAGE_PATH"] = str(db_path)
            try:
                _persist_match(
                    db_path,
                    server_slug="comunidad-hispana-01",
                    match_id="1561515",
                    map_name="St. Mere Eglise",
                    started_at="2026-04-12T16:20:00Z",
                    ended_at="2026-04-12T17:45:00Z",
                )
                session_key = _persist_rcon_window(
                    db_path,
                    map_name="St. Mere Eglise",
                    first_seen_at="2026-04-12T16:28:55.761810Z",
                    last_seen_at="2026-04-12T16:43:55.761810Z",
                    players=94,
                    max_players=98,
                )

                detail = get_rcon_historical_match_detail(
                    server_key="comunidad-hispana-01",
                    match_id=session_key,
                )
            finally:
                if previous_storage_path is None:
                    os.environ.pop("HLL_BACKEND_STORAGE_PATH", None)
                else:
                    os.environ["HLL_BACKEND_STORAGE_PATH"] = previous_storage_path

            self.assertIsNotNone(detail)
            self.assertEqual(
                detail["match_url"],
                "https://scoreboard.comunidadhll.es/games/1561515",
            )
            gc.collect()

    def test_rcon_match_detail_keeps_low_confidence_correlation_unlinked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            previous_storage_path = os.environ.get("HLL_BACKEND_STORAGE_PATH")
            os.environ["HLL_BACKEND_STORAGE_PATH"] = str(db_path)
            try:
                _persist_match(
                    db_path,
                    server_slug="comunidad-hispana-01",
                    match_id="1561515",
                    map_name="Carentan",
                    started_at="2026-04-12T10:00:00Z",
                    ended_at="2026-04-12T11:30:00Z",
                )
                session_key = _persist_rcon_window(
                    db_path,
                    map_name="St. Mere Eglise",
                    first_seen_at="2026-04-12T16:28:55.761810Z",
                    last_seen_at="2026-04-12T16:43:55.761810Z",
                    players=94,
                    max_players=98,
                )

                detail = get_rcon_historical_match_detail(
                    server_key="comunidad-hispana-01",
                    match_id=session_key,
                )
            finally:
                if previous_storage_path is None:
                    os.environ.pop("HLL_BACKEND_STORAGE_PATH", None)
                else:
                    os.environ["HLL_BACKEND_STORAGE_PATH"] = previous_storage_path

            self.assertIsNotNone(detail)
            self.assertIsNone(detail["match_url"])
            gc.collect()

    def test_foy_relink_reports_existing_materialized_match_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            previous_storage_path = os.environ.get("HLL_BACKEND_STORAGE_PATH")
            os.environ["HLL_BACKEND_STORAGE_PATH"] = str(db_path)
            try:
                _persist_match(
                    db_path,
                    server_slug="comunidad-hispana-02",
                    match_id="1562115",
                    map_name="Foy Warfare",
                    started_at="2026-05-20T20:54:11Z",
                    ended_at="2026-05-20T22:24:11Z",
                )
                persist_rcon_admin_log_entries(
                    target={
                        "target_key": "comunidad-hispana-02",
                        "external_server_id": "comunidad-hispana-02",
                    },
                    entries=[
                        {
                            "timestamp": "2026-05-20T20:54:11Z",
                            "message": "[1 min (1779310451)] MATCH START Foy Warfare",
                        },
                        {
                            "timestamp": "2026-05-20T22:24:11Z",
                            "message": "[91 min (1779315851)] MATCH ENDED `Foy Warfare` ALLIED (4 - 1) AXIS",
                        },
                    ],
                    db_path=db_path,
                )
                materialize_rcon_admin_log(db_path=db_path)
                report = relink_materialized_matches(
                    server_key="comunidad-hispana-02",
                    db_path=db_path,
                )
                detail = get_rcon_historical_match_detail(
                    server_key="comunidad-hispana-02",
                    match_id="comunidad-hispana-02:1779310451:1779315851:foywarfare",
                )
                diagnostics = inspect_materialized_match_correlation(
                    server_key="comunidad-hispana-02",
                    match_key="comunidad-hispana-02:1779310451:1779315851:foywarfare",
                    db_path=db_path,
                )
            finally:
                if previous_storage_path is None:
                    os.environ.pop("HLL_BACKEND_STORAGE_PATH", None)
                else:
                    os.environ["HLL_BACKEND_STORAGE_PATH"] = previous_storage_path

            self.assertEqual(report["matches_scanned"], 1)
            self.assertEqual(report["matches_linked"], 1)
            self.assertGreaterEqual(report["candidates_scanned"], 1)
            self.assertIsNotNone(detail)
            self.assertEqual(
                detail["match_url"],
                "https://scoreboard.comunidadhll.es:5443/games/1562115",
            )
            self.assertEqual(diagnostics["final_reason"], "linked")
            self.assertEqual(diagnostics["selected_candidate"]["external_match_id"], "1562115")
            self.assertEqual(diagnostics["top_candidates"][0]["map"], "Foy Warfare")
            gc.collect()


def _persist_match(
    db_path: Path,
    *,
    server_slug: str,
    match_id: str,
    map_name: str = "carentan",
    started_at: str = "2026-05-01T10:00:00Z",
    ended_at: str = "2026-05-01T11:20:00Z",
    player_stats: list[dict[str, object]] | None = None,
) -> None:
    upsert_historical_match(
        server_slug=server_slug,
        match_payload={
            "id": match_id,
            "creation_time": started_at,
            "start": started_at,
            "end": ended_at,
            "map": {"name": map_name},
            "result": {"allied": 3, "axis": 2},
            "player_stats": player_stats or [],
        },
        db_path=db_path,
    )


def _foy_list_match() -> dict[str, object]:
    return {
        "id": 1562115,
        "server_number": 2,
        "start": "2026-05-20T20:54:11+00:00",
        "end": "2026-05-20T22:24:11+00:00",
        "map": {"id": "foywarfare", "pretty_name": "Foy Warfare"},
        "result": {"allied": 4, "axis": 1},
    }


def _backfill_timestamp(raw_value: str):
    from app.scoreboard_candidate_backfill import _parse_timestamp

    return _parse_timestamp(raw_value, option_name="test")


def _persist_rcon_window(
    db_path: Path,
    *,
    map_name: str,
    first_seen_at: str,
    last_seen_at: str,
    players: int,
    max_players: int,
) -> str:
    initialize_rcon_historical_storage(db_path=db_path)
    run_id = start_rcon_historical_capture_run(
        mode="test",
        target_scope="comunidad-hispana-01",
        db_path=db_path,
    )
    target = {
        "target_key": "comunidad-hispana-01",
        "external_server_id": "comunidad-hispana-01",
        "name": "Comunidad Hispana #01",
        "host": "127.0.0.1",
        "port": 7779,
    }
    for captured_at in (first_seen_at, last_seen_at):
        persist_rcon_historical_sample(
            run_id=run_id,
            captured_at=captured_at,
            target=target,
            normalized_payload={
                "status": "online",
                "players": players,
                "max_players": max_players,
                "current_map": map_name,
            },
            raw_payload={},
            db_path=db_path,
        )
    return f"1:{first_seen_at}"


def _set_raw_payload_ref(db_path: Path, *, match_id: str, raw_payload_ref: str) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            UPDATE historical_matches
            SET raw_payload_ref = ?
            WHERE external_match_id = ?
            """,
            (raw_payload_ref, match_id),
        )


if __name__ == "__main__":
    unittest.main()
