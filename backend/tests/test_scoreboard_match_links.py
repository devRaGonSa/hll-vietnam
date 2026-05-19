"""Regression checks for persisted public-scoreboard match links."""

from __future__ import annotations

import gc
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

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


class PersistedScoreboardMatchLinkTests(unittest.TestCase):
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


def _persist_match(
    db_path: Path,
    *,
    server_slug: str,
    match_id: str,
    map_name: str = "carentan",
    started_at: str = "2026-05-01T10:00:00Z",
    ended_at: str = "2026-05-01T11:20:00Z",
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
            "player_stats": [],
        },
        db_path=db_path,
    )


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
