import unittest
from contextlib import nullcontext
from unittest.mock import patch

from app.rcon_historical_leaderboards import get_latest_ranking_snapshot


class RankingSnapshotPayloadTests(unittest.TestCase):
    def test_get_latest_ranking_snapshot_skips_storage_init_on_postgres_read(self):
        with (
            patch("app.rcon_historical_leaderboards.use_postgres_rcon_storage", return_value=True),
            patch("app.rcon_historical_leaderboards.initialize_ranking_snapshot_storage") as init_mock,
            patch(
                "app.rcon_historical_leaderboards._open_ranking_snapshot_read_connection",
                return_value=nullcontext(object()),
            ),
            patch("app.rcon_historical_leaderboards._find_latest_snapshot", return_value=None),
        ):
            result = get_latest_ranking_snapshot(
                server_key="all",
                timeframe="weekly",
                metric="kills",
                limit=20,
            )

        init_mock.assert_not_called()
        self.assertEqual(result["snapshot_status"], "missing")
        self.assertEqual(result["source"], "ranking-snapshot")
        self.assertEqual(result["requested_limit"], 20)


if __name__ == "__main__":
    unittest.main()
