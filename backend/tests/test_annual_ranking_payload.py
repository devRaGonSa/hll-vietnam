import unittest
from contextlib import nullcontext
from unittest.mock import patch

from app.rcon_annual_rankings import get_annual_ranking_snapshot


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


if __name__ == "__main__":
    unittest.main()
