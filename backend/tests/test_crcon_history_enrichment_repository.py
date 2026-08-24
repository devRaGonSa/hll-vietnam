from __future__ import annotations

import unittest

from app.crcon.postgres_repository import (
    MATCH_PLAYER_COUNTS_SQL,
    MATCH_PLAYER_IDENTITIES_SQL,
    PostgresCrconRepository,
)
from app.crcon.repository import CrconHistoricalMatchLookup, CrconServerScope


class _Cursor:
    def __init__(self, *, one=None, many=None):
        self.one = one
        self.many = many or []

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.many


class _Connection:
    def __init__(self):
        self.statements = []
        self.rollback_calls = 0
        self.closed = False

    def execute(self, statement, params=None):
        self.statements.append((statement, params))
        if statement == "SHOW transaction_read_only":
            return _Cursor(one=("on",))
        if statement == MATCH_PLAYER_COUNTS_SQL:
            return _Cursor(many=[(9001, 81), (9002, 0)])
        if statement == MATCH_PLAYER_IDENTITIES_SQL:
            return _Cursor(
                many=[
                    ("opaque-player", "76561198000000000", None, "steam"),
                    ("opaque-epic", None, "a" * 32, "epic"),
                ]
            )
        return _Cursor()

    def rollback(self):
        self.rollback_calls += 1

    def close(self):
        self.closed = True


class CrconHistoryEnrichmentRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.connection = _Connection()
        self.repository = PostgresCrconRepository(
            dsn="postgresql://fixture.invalid/crcon",
            connect_timeout_seconds=1,
            statement_timeout_ms=1000,
            lock_timeout_ms=10,
            connector=lambda *_args, **_kwargs: self.connection,
        )

    def test_match_counts_use_one_parameterized_distinct_scoped_query(self):
        rows = self.repository.list_match_player_counts(
            matches=(
                CrconHistoricalMatchLookup(9001, CrconServerScope(1, "hll")),
                CrconHistoricalMatchLookup(9002, CrconServerScope(3, "hllv")),
            )
        )

        self.assertEqual([(row.map_id, row.player_count) for row in rows], [(9001, 81), (9002, 0)])
        query_calls = [row for row in self.connection.statements if row[0] == MATCH_PLAYER_COUNTS_SQL]
        self.assertEqual(len(query_calls), 1)
        self.assertEqual(query_calls[0][1], ([9001, 9002], [1, 3], [1, 2]))
        self.assertIn("count(DISTINCT stats.playersteamid_id)", MATCH_PLAYER_COUNTS_SQL)

    def test_match_identities_use_one_bounded_map_participant_query(self):
        rows = self.repository.list_match_player_identities(
            match=CrconHistoricalMatchLookup(9001, CrconServerScope(1, "hll")),
            player_ids=("opaque-player", "opaque-epic", "opaque-player"),
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].steam_id_64, "76561198000000000")
        self.assertEqual(rows[1].eos_id, "a" * 32)
        query_calls = [row for row in self.connection.statements if row[0] == MATCH_PLAYER_IDENTITIES_SQL]
        self.assertEqual(len(query_calls), 1)
        self.assertEqual(query_calls[0][1], (9001, 1, 1, ["opaque-player", "opaque-epic"]))
        self.assertIn("stats.map_id = maps.id", MATCH_PLAYER_IDENTITIES_SQL)
        self.assertIn("soldier.playersteamid_id = identities.id", MATCH_PLAYER_IDENTITIES_SQL)

    def test_enrichment_sql_is_select_only(self):
        sql = f"{MATCH_PLAYER_COUNTS_SQL}\n{MATCH_PLAYER_IDENTITIES_SQL}".upper()
        for keyword in ("INSERT ", "UPDATE ", "DELETE ", "ALTER ", "CREATE ", "DROP ", "TRUNCATE "):
            self.assertNotIn(keyword, sql)

    def test_lookup_bounds_fail_before_query(self):
        with self.assertRaisesRegex(ValueError, "at most 100"):
            self.repository.list_match_player_counts(
                matches=tuple(
                    CrconHistoricalMatchLookup(index, CrconServerScope(1, "hll"))
                    for index in range(1, 102)
                )
            )
        self.assertEqual(self.connection.statements, [])


if __name__ == "__main__":
    unittest.main()
