import gc
import unittest
import warnings
from contextlib import closing, nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.historical_storage import ALL_SERVERS_SLUG
from app.rcon_admin_log_materialization import (
    MATCH_RESULT_SOURCE,
    initialize_rcon_materialized_storage,
)
from app.rcon_annual_rankings import (
    SUPPORTED_ANNUAL_RANKING_METRICS,
    _normalize_metric,
    generate_annual_ranking_snapshot,
    get_annual_ranking_snapshot,
)
from app.sqlite_utils import connect_sqlite_writer


class AnnualRankingPayloadTests(unittest.TestCase):
    def test_get_annual_ranking_snapshot_skips_storage_init_on_postgres_read(self):
        with (
            patch("app.rcon_annual_rankings.use_postgres_rcon_storage", return_value=True),
            patch("app.rcon_annual_rankings.initialize_rcon_materialized_storage") as init_mock,
            patch(
                "app.rcon_annual_rankings._open_annual_snapshot_read_connection",
                return_value=nullcontext(object()),
            ),
            patch("app.rcon_annual_rankings._find_snapshot", return_value=None),
        ):
            result = get_annual_ranking_snapshot(
                year=2026,
                server_key="all",
                metric="kills",
                limit=30,
            )

        init_mock.assert_not_called()
        self.assertEqual(result["snapshot_status"], "missing")
        self.assertEqual(result["source"], "rcon-annual-ranking-snapshot")
        self.assertEqual(result["requested_limit"], 30)

    def test_normalize_metric_accepts_supported_annual_metrics(self):
        for metric in SUPPORTED_ANNUAL_RANKING_METRICS:
            with self.subTest(metric=metric):
                self.assertEqual(_normalize_metric(metric), metric)

    def test_normalize_metric_rejects_unsupported_annual_metrics(self):
        with self.assertRaises(ValueError):
            _normalize_metric("kills_per_minute")

    def test_generate_annual_snapshot_orders_kd_ratio_and_kills_per_match(self):
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "annual-ranking.sqlite3"
            self._seed_materialized_stats(db_path)

            kd_result = generate_annual_ranking_snapshot(
                year=2026,
                server_key=ALL_SERVERS_SLUG,
                metric="kd_ratio",
                limit=10,
                db_path=db_path,
            )
            kpp_result = generate_annual_ranking_snapshot(
                year=2026,
                server_key=ALL_SERVERS_SLUG,
                metric="kills_per_match",
                limit=10,
                db_path=db_path,
            )

            kd_items = kd_result["items"]
            kpp_items = kpp_result["items"]
            self.assertEqual(kd_items[0]["player_id"], "player-bravo")
            self.assertEqual(kd_items[0]["metric_value"], 10)
            self.assertEqual(kpp_items[0]["player_id"], "player-bravo")
            self.assertEqual(kpp_items[0]["metric_value"], 20)
            self.assertEqual(kpp_items[1]["player_id"], "player-alpha")
            self.assertEqual(kpp_items[1]["metric_value"], 15)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                gc.collect()

    def _seed_materialized_stats(self, db_path: Path) -> None:
        initialize_rcon_materialized_storage(db_path=db_path)
        with closing(connect_sqlite_writer(db_path)) as connection:
            with connection:
                for match_key in ("match-1", "match-2", "match-3"):
                    connection.execute(
                        """
                        INSERT INTO rcon_materialized_matches (
                            target_key,
                            external_server_id,
                            match_key,
                            started_at,
                            ended_at,
                            confidence_mode,
                            source_basis
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            "target-1",
                            "comunidad-hispana-01",
                            match_key,
                            "2026-01-01T19:00:00Z",
                            "2026-01-01T20:00:00Z",
                            "exact",
                            MATCH_RESULT_SOURCE,
                        ],
                    )
                for row in (
                    ("match-1", "player-alpha", "Alpha", 12, 4, 0),
                    ("match-2", "player-alpha", "Alpha", 18, 6, 1),
                    ("match-3", "player-bravo", "Bravo", 20, 2, 0),
                ):
                    connection.execute(
                        """
                        INSERT INTO rcon_match_player_stats (
                            target_key,
                            match_key,
                            player_id,
                            player_name,
                            kills,
                            deaths,
                            teamkills
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        ["target-1", *row],
                    )


if __name__ == "__main__":
    unittest.main()
