"""Strictly read-only PostgreSQL implementation of the CRCON repository."""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime, timedelta
from threading import Condition
from typing import Any

from ..domain import PlayerIdentity
from .capabilities import PROBED_TABLES, build_capability_report
from .models import CrconCapabilityReport, CrconDatabaseError, CrconUnavailableError
from .repository import (
    CrconCurrentMap,
    CrconMatchCombatStats,
    CrconMatchLogEvent,
    CrconPlayerAggregate,
    CrconPlayerProfileAggregate,
    CrconRankingRow,
    CrconServerAggregate,
    CrconServerScope,
)


APPLICATION_NAME = "hll-vietnam-bff"
SCHEMA_COLUMNS_SQL = """
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_schema = current_schema()
  AND table_name = ANY(%s)
ORDER BY table_name, ordinal_position
"""
CURRENT_MAP_MATCH_SQL = """
SELECT id, start, end, server_number, map_name, result
FROM map_history
WHERE server_number = %s
  AND end IS NULL
  AND lower(map_name) = lower(%s)
  AND start >= %s
  AND start <= %s
ORDER BY start DESC, id DESC
LIMIT 2
"""
CURRENT_OPEN_MAP_SQL = """
SELECT id, start, end, server_number, map_name, result
FROM map_history
WHERE server_number = %s
  AND end IS NULL
ORDER BY start DESC, id DESC
LIMIT 2
"""
MATCH_LOG_EVENTS_SQL = """
SELECT
    logs.id,
    logs.event_time,
    logs.type,
    logs.player1_name,
    player1.steam_id_64 AS player1_id,
    logs.player2_name,
    player2.steam_id_64 AS player2_id,
    logs.weapon
FROM log_lines AS logs
LEFT JOIN steam_id_64 AS player1 ON player1.id = logs.player1_steamid
LEFT JOIN steam_id_64 AS player2 ON player2.id = logs.player2_steamid
WHERE logs.server = %s
  AND logs.game = %s
  AND logs.event_time >= %s
  AND logs.event_time <= %s
  AND logs.type = ANY(%s)
ORDER BY logs.event_time DESC, logs.id DESC
LIMIT %s
"""
MATCH_COMBAT_AGGREGATE_SQL = """
WITH bounded_events AS (
    SELECT
        logs.type,
        logs.player1_name,
        player1.steam_id_64 AS player1_id,
        logs.player2_name,
        player2.steam_id_64 AS player2_id,
        logs.weapon
    FROM log_lines AS logs
    LEFT JOIN steam_id_64 AS player1 ON player1.id = logs.player1_steamid
    LEFT JOIN steam_id_64 AS player2 ON player2.id = logs.player2_steamid
    WHERE logs.server = %s
      AND logs.game = %s
      AND logs.event_time >= %s
      AND logs.event_time <= %s
      AND logs.type = ANY(%s)
),
player_facts AS (
    SELECT
        CASE
            WHEN NULLIF(player1_id, '') IS NOT NULL THEN 'id:' || player1_id
            ELSE 'name:' || lower(COALESCE(NULLIF(btrim(player1_name), ''), 'Unknown player'))
        END AS player_key,
        NULLIF(player1_id, '') AS player_id,
        COALESCE(NULLIF(btrim(player1_name), ''), 'Unknown player') AS player_name,
        CASE WHEN type = 'KILL' THEN 1 ELSE 0 END AS kills,
        0 AS deaths,
        CASE WHEN type = 'TEAM KILL' THEN 1 ELSE 0 END AS teamkills,
        0 AS deaths_by_teamkill
    FROM bounded_events
    UNION ALL
    SELECT
        CASE
            WHEN NULLIF(player2_id, '') IS NOT NULL THEN 'id:' || player2_id
            ELSE 'name:' || lower(COALESCE(NULLIF(btrim(player2_name), ''), 'Unknown player'))
        END AS player_key,
        NULLIF(player2_id, '') AS player_id,
        COALESCE(NULLIF(btrim(player2_name), ''), 'Unknown player') AS player_name,
        0 AS kills,
        CASE WHEN type = 'KILL' THEN 1 ELSE 0 END AS deaths,
        0 AS teamkills,
        CASE WHEN type = 'TEAM KILL' THEN 1 ELSE 0 END AS deaths_by_teamkill
    FROM bounded_events
),
player_totals AS (
    SELECT
        player_key,
        max(player_id) AS player_id,
        max(player_name) AS player_name,
        sum(kills)::bigint AS kills,
        sum(deaths)::bigint AS deaths,
        sum(teamkills)::bigint AS teamkills,
        sum(deaths_by_teamkill)::bigint AS deaths_by_teamkill
    FROM player_facts
    GROUP BY player_key
),
weapon_totals AS (
    SELECT
        CASE
            WHEN NULLIF(player1_id, '') IS NOT NULL THEN 'id:' || player1_id
            ELSE 'name:' || lower(COALESCE(NULLIF(btrim(player1_name), ''), 'Unknown player'))
        END AS player_key,
        weapon,
        count(*)::bigint AS weapon_count
    FROM bounded_events
    WHERE type = 'KILL'
      AND NULLIF(btrim(weapon), '') IS NOT NULL
    GROUP BY player_key, weapon
),
weapon_maps AS (
    SELECT
        player_key,
        jsonb_object_agg(weapon, weapon_count ORDER BY weapon) AS weapon_counts
    FROM weapon_totals
    GROUP BY player_key
)
SELECT
    totals.player_id,
    totals.player_name,
    totals.kills,
    totals.deaths,
    totals.teamkills,
    totals.deaths_by_teamkill,
    COALESCE(weapons.weapon_counts, '{}'::jsonb) AS weapon_counts
FROM player_totals AS totals
LEFT JOIN weapon_maps AS weapons USING (player_key)
ORDER BY totals.player_key ASC
"""


PLAYER_AGGREGATE_SQL = """
SELECT
    count(DISTINCT stats.map_id)::bigint AS matches_played,
    COALESCE(max(stats.kills), 0)::bigint AS record_kills,
    COALESCE(sum(stats.kills), 0)::bigint AS total_kills,
    COALESCE(sum(stats.deaths), 0)::bigint AS deaths,
    COALESCE(sum(stats.combat), 0)::bigint AS combat,
    COALESCE(sum(stats.offense), 0)::bigint AS offense,
    COALESCE(sum(stats.defense), 0)::bigint AS defense,
    COALESCE(sum(stats.support), 0)::bigint AS support,
    COALESCE(sum(stats.vehicle_kills), 0)::bigint AS vehicle_kills,
    COALESCE(sum(stats.vehicles_destroyed), 0)::bigint AS vehicles_destroyed
FROM player_stats AS stats
JOIN map_history AS maps ON maps.id = stats.map_id
JOIN steam_id_64 AS identities ON identities.id = stats.playersteamid_id
WHERE identities.steam_id_64 = %s
  AND maps.server_number = %s
"""
SERVER_AGGREGATE_SQL = """
WITH scoped_maps AS (
    SELECT id, start, "end", map_name
    FROM map_history
    WHERE server_number = ANY(%s)
      AND game = %s
      AND "end" IS NOT NULL
)
SELECT count(DISTINCT maps.id)::bigint AS matches_count,
       count(DISTINCT stats.playersteamid_id)::bigint AS unique_players,
       min(maps.start) AS first_match_at,
       max(maps."end") AS last_match_at
FROM scoped_maps AS maps
LEFT JOIN player_stats AS stats ON stats.map_id = maps.id
"""

SERVER_TOP_MAPS_SQL = """
SELECT map_name, count(*)::bigint AS matches_count
FROM map_history
WHERE server_number = ANY(%s)
  AND game = %s
  AND "end" IS NOT NULL
GROUP BY map_name
ORDER BY matches_count DESC, map_name ASC
LIMIT 5
"""

RANKING_METRIC_SQL = {
    "kills": "kills",
    "deaths": "deaths",
    "teamkills": "teamkills",
    "matches_considered": "matches_played",
    "kd_ratio": "CASE WHEN deaths > 0 THEN kills::numeric / deaths ELSE kills::numeric END",
    "kills_per_match": "CASE WHEN matches_played > 0 THEN kills::numeric / matches_played ELSE 0 END",
    "kpm": "CASE WHEN time_seconds > 0 THEN kills::numeric * 60 / time_seconds ELSE 0 END",
    "combat": "combat",
    "offense": "offense",
    "defense": "defense",
    "support": "support",
    "vehicle_kills": "vehicle_kills",
    "vehicles_destroyed": "vehicles_destroyed",
    "playtime": "time_seconds",
    "matches_over_100_kills": "matches_over_100_kills",
}

RANKING_AGGREGATE_CTE = """
WITH scoped_maps AS (
    SELECT id, "end"
    FROM map_history
    WHERE server_number = ANY(%s)
      AND game = %s
      AND "end" IS NOT NULL
      AND (%s IS NULL OR "end" >= %s)
      AND (%s IS NULL OR "end" < %s)
), aggregate_rows AS (
    SELECT identities.steam_id_64 AS player_id,
           COALESCE(
               (array_agg(NULLIF(btrim(stats.name), '') ORDER BY maps."end" DESC, stats.map_id DESC))[1],
               identities.steam_id_64
           ) AS player_name,
           count(DISTINCT stats.map_id)::bigint AS matches_played,
           COALESCE(max(stats.kills), 0)::bigint AS record_kills,
           COALESCE(sum(stats.kills), 0)::bigint AS kills,
           COALESCE(sum(stats.deaths), 0)::bigint AS deaths,
           COALESCE(sum(stats.teamkills), 0)::bigint AS teamkills,
           COALESCE(sum(stats.deaths_by_tk), 0)::bigint AS deaths_by_teamkill,
           COALESCE(sum(stats.time_seconds), 0)::bigint AS time_seconds,
           COALESCE(sum(stats.combat), 0)::bigint AS combat,
           COALESCE(sum(stats.offense), 0)::bigint AS offense,
           COALESCE(sum(stats.defense), 0)::bigint AS defense,
           COALESCE(sum(stats.support), 0)::bigint AS support,
           COALESCE(sum(stats.vehicle_kills), 0)::bigint AS vehicle_kills,
           COALESCE(sum(stats.vehicles_destroyed), 0)::bigint AS vehicles_destroyed,
           count(*) FILTER (WHERE stats.kills > 100)::bigint AS matches_over_100_kills
    FROM player_stats AS stats
    JOIN scoped_maps AS maps ON maps.id = stats.map_id
    JOIN steam_id_64 AS identities ON identities.id = stats.playersteamid_id
    GROUP BY identities.id, identities.steam_id_64
)
"""

PLAYER_PROFILE_SQL = RANKING_AGGREGATE_CTE + """
, ranked AS (
    SELECT aggregate_rows.*,
           dense_rank() OVER (ORDER BY kills DESC) AS kills_ranking_position
    FROM aggregate_rows
)
SELECT ranked.player_id, ranked.player_name,
       identities.steam_id, soldier.eos_id, soldier.platform,
       ranked.matches_played, ranked.record_kills, ranked.kills, ranked.deaths,
       ranked.teamkills, ranked.deaths_by_teamkill, ranked.time_seconds,
       ranked.combat, ranked.offense, ranked.defense, ranked.support,
       ranked.vehicle_kills, ranked.vehicles_destroyed,
       latest.last_seen_at, latest.servers_seen, ranked.kills_ranking_position
FROM ranked
JOIN steam_id_64 AS identities ON identities.steam_id_64 = ranked.player_id
LEFT JOIN player_soldier AS soldier ON soldier.playersteamid_id = identities.id
LEFT JOIN LATERAL (
    SELECT max(maps."end") AS last_seen_at,
           array_agg(DISTINCT maps.server_number ORDER BY maps.server_number) AS servers_seen
    FROM player_stats AS stats
    JOIN map_history AS maps ON maps.id = stats.map_id
    WHERE stats.playersteamid_id = identities.id
      AND maps.server_number = ANY(%s)
      AND maps.game = %s
      AND maps."end" IS NOT NULL
) AS latest ON true
WHERE ranked.player_id = %s
"""

Connector = Callable[..., Any]


class PostgresCrconRepository:
    """Capability-only PostgreSQL boundary with fail-closed read-only sessions."""

    def __init__(
        self,
        *,
        dsn: str | None,
        connect_timeout_seconds: int,
        statement_timeout_ms: int,
        lock_timeout_ms: int,
        pool_size: int = 2,
        connector: Connector | None = None,
    ) -> None:
        if connect_timeout_seconds <= 0:
            raise ValueError("connect_timeout_seconds must be positive.")
        if statement_timeout_ms <= 0:
            raise ValueError("statement_timeout_ms must be positive.")
        if lock_timeout_ms < 0:
            raise ValueError("lock_timeout_ms must be zero or positive.")
        if pool_size < 1 or pool_size > 8:
            raise ValueError("pool_size must be between one and eight.")
        self._dsn = str(dsn or "").strip() or None
        self._connect_timeout_seconds = connect_timeout_seconds
        self._statement_timeout_ms = statement_timeout_ms
        self._lock_timeout_ms = lock_timeout_ms
        self._connector = connector
        self._pool = (
            _ReadConnectionPool(
                connector=_load_connector,
                connect=self._connect,
                max_size=pool_size,
                wait_timeout_seconds=float(connect_timeout_seconds),
            )
            if connector is None and self._dsn is not None
            else None
        )

    @property
    def configured(self) -> bool:
        return self._dsn is not None

    def probe_capabilities(self, *, api_configured: bool = False) -> CrconCapabilityReport:
        """Inspect only allowlisted schema metadata and report each capability."""
        if not self.configured:
            return build_capability_report(
                schema_columns=None,
                database_configured=False,
                api_configured=api_configured,
            )

        schema_columns: dict[str, set[str]] = {}
        with self._read_only_connection() as connection:
            cursor = connection.execute(SCHEMA_COLUMNS_SQL, (sorted(PROBED_TABLES),))
            for row in cursor.fetchall():
                table_name, column_name = _schema_row(row)
                schema_columns.setdefault(table_name, set()).add(column_name)

        return build_capability_report(
            schema_columns=schema_columns,
            database_configured=True,
            api_configured=api_configured,
        )

    def find_current_map(
        self,
        *,
        server_number: int,
        map_name: str | None,
        started_at: datetime | None,
        tolerance_seconds: int = 180,
    ) -> CrconCurrentMap | None:
        """Return one unambiguous open map matching current API state."""
        self._require_configured()
        if server_number <= 0:
            raise ValueError("server_number must be positive.")
        if tolerance_seconds < 0 or tolerance_seconds > 900:
            raise ValueError("tolerance_seconds must be between zero and 900.")

        normalized_map = str(map_name or "").strip()
        with self._read_only_connection() as connection:
            if normalized_map and started_at is not None:
                tolerance = timedelta(seconds=tolerance_seconds)
                cursor = connection.execute(
                    CURRENT_MAP_MATCH_SQL,
                    (
                        server_number,
                        normalized_map,
                        started_at - tolerance,
                        started_at + tolerance,
                    ),
                )
            else:
                cursor = connection.execute(CURRENT_OPEN_MAP_SQL, (server_number,))
            rows = cursor.fetchall()

        if len(rows) != 1:
            return None
        return _current_map_row(rows[0])

    def list_match_log_events(
        self,
        *,
        scope: CrconServerScope,
        started_at: datetime,
        ended_at: datetime,
        limit: int = 500,
    ) -> tuple[CrconMatchLogEvent, ...]:
        """Read the newest bounded current-match combat window, newest first."""
        self._require_configured()
        if scope.server_number <= 0:
            raise ValueError("server_number must be positive.")
        if ended_at < started_at:
            raise ValueError("ended_at must not precede started_at.")
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between one and 500.")

        log_server, log_game = scope.require_log_discriminators()
        with self._read_only_connection() as connection:
            cursor = connection.execute(
                MATCH_LOG_EVENTS_SQL,
                (
                    log_server,
                    log_game,
                    started_at,
                    ended_at,
                    ["KILL", "TEAM KILL"],
                    limit,
                ),
            )
            rows = cursor.fetchall()
        return tuple(_match_log_event_row(row) for row in rows)

    def aggregate_match_combat_stats(
        self,
        *,
        scope: CrconServerScope,
        started_at: datetime,
        ended_at: datetime,
    ) -> tuple[CrconMatchCombatStats, ...]:
        """Aggregate complete bounded current-match combat without raw-row materialization."""
        self._require_configured()
        if scope.server_number <= 0:
            raise ValueError("server_number must be positive.")
        if ended_at < started_at:
            raise ValueError("ended_at must not precede started_at.")

        log_server, log_game = scope.require_log_discriminators()
        with self._read_only_connection() as connection:
            cursor = connection.execute(
                MATCH_COMBAT_AGGREGATE_SQL,
                (
                    log_server,
                    log_game,
                    started_at,
                    ended_at,
                    ["KILL", "TEAM KILL"],
                ),
            )
            rows = cursor.fetchall()
        return tuple(_match_combat_stats_row(row) for row in rows)

    def get_player_aggregate(
        self,
        *,
        identity: PlayerIdentity,
        scope: CrconServerScope,
    ) -> CrconPlayerAggregate:
        """Return fixed, bounded aggregates without interpreting the opaque player ID."""
        self._require_configured()
        if scope.server_number <= 0:
            raise ValueError("server_number must be positive.")
        with self._read_only_connection() as connection:
            row = connection.execute(
                PLAYER_AGGREGATE_SQL,
                (str(identity.player_id), scope.server_number),
            ).fetchone()
        values = _player_aggregate_row(row)
        return CrconPlayerAggregate(identity=identity, scope=scope, **values)

    def get_server_aggregate(
        self,
        *,
        scopes: tuple[CrconServerScope, ...],
    ) -> CrconServerAggregate:
        server_numbers, game = _scope_query_values(scopes)
        with self._read_only_connection() as connection:
            row = connection.execute(
                SERVER_AGGREGATE_SQL, (list(server_numbers), game)
            ).fetchone()
            map_rows = connection.execute(
                SERVER_TOP_MAPS_SQL, (list(server_numbers), game)
            ).fetchall()
        values = _row_values(
            row,
            ("matches_count", "unique_players", "first_match_at", "last_match_at"),
        )
        top_maps = tuple(
            (str(values[0]), int(values[1] or 0))
            for values in (
                _row_values(item, ("map_name", "matches_count")) for item in map_rows
            )
        )
        return CrconServerAggregate(
            matches_count=int(values[0] or 0),
            unique_players=int(values[1] or 0),
            first_match_at=values[2] if isinstance(values[2], datetime) else None,
            last_match_at=values[3] if isinstance(values[3], datetime) else None,
            top_maps=top_maps,
        )

    def list_rankings(
        self,
        *,
        scopes: tuple[CrconServerScope, ...],
        started_at: datetime | None,
        ended_at: datetime | None,
        metric: str,
        limit: int,
        offset: int = 0,
    ) -> tuple[CrconRankingRow, ...]:
        server_numbers, game = _scope_query_values(scopes)
        metric_sql = RANKING_METRIC_SQL.get(metric)
        if metric_sql is None:
            raise ValueError("Unsupported CRCON ranking metric.")
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between one and 100.")
        if offset < 0 or offset > 10_000:
            raise ValueError("offset must be between zero and 10000.")
        query = RANKING_AGGREGATE_CTE + f"""
, ranked AS (
    SELECT aggregate_rows.*,
           ({metric_sql}) AS metric_value,
           dense_rank() OVER (ORDER BY ({metric_sql}) DESC) AS ranking_position,
           count(*) OVER () AS total_rows,
           (SELECT count(*)::bigint FROM scoped_maps) AS source_matches_count
    FROM aggregate_rows
)
SELECT player_id, player_name, matches_played, record_kills, kills, deaths,
       teamkills, time_seconds, combat, offense, defense, support, vehicle_kills,
       vehicles_destroyed, matches_over_100_kills, ranking_position,
       metric_value, total_rows, source_matches_count
FROM ranked
ORDER BY metric_value DESC, player_id ASC
LIMIT %s OFFSET %s
"""
        params = _aggregate_query_params(
            server_numbers, game, started_at, ended_at
        ) + (limit, offset)
        with self._read_only_connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return tuple(_ranking_row(row) for row in rows)

    def get_player_profile_aggregate(
        self,
        *,
        player_id: str,
        scopes: tuple[CrconServerScope, ...],
        started_at: datetime | None,
        ended_at: datetime | None,
    ) -> CrconPlayerProfileAggregate | None:
        normalized_id = str(player_id or "").strip()
        if not normalized_id:
            raise ValueError("player_id is required.")
        server_numbers, game = _scope_query_values(scopes)
        params = _aggregate_query_params(
            server_numbers, game, started_at, ended_at
        ) + (list(server_numbers), game, normalized_id)
        with self._read_only_connection() as connection:
            row = connection.execute(PLAYER_PROFILE_SQL, params).fetchone()
        return _player_profile_row(row) if row is not None else None

    def close(self) -> None:
        """Close idle pooled runtime connections; injected test connections are not pooled."""
        if self._pool is not None:
            self._pool.close()

    def _require_configured(self) -> None:
        if not self.configured:
            raise CrconUnavailableError("CRCON database is not configured.")

    def _connect(self, connector: Connector) -> Any:
        return connector(
            self._dsn,
            connect_timeout=self._connect_timeout_seconds,
            application_name=APPLICATION_NAME,
            options=(
                "-c default_transaction_read_only=on "
                f"-c statement_timeout={self._statement_timeout_ms} "
                f"-c lock_timeout={self._lock_timeout_ms}"
            ),
        )

    @contextmanager
    def _read_only_connection(self) -> Iterator[Any]:
        connection = None
        pooled = False
        try:
            if self._pool is not None:
                connection = self._pool.acquire()
                pooled = True
            else:
                connection = self._connect(self._connector or _load_connector())
            connection.execute("BEGIN READ ONLY")
            status_row = connection.execute("SHOW transaction_read_only").fetchone()
            if _read_only_status(status_row) != "on":
                raise CrconDatabaseError("CRCON database did not establish read-only mode.")
            yield connection
        except CrconDatabaseError:
            raise
        except Exception:
            raise CrconDatabaseError("CRCON database operation failed.") from None
        finally:
            if connection is not None:
                had_active_error = sys.exc_info()[0] is not None
                cleanup_failed = False
                try:
                    connection.rollback()
                except Exception:
                    cleanup_failed = True
                if pooled and not cleanup_failed and not had_active_error:
                    self._pool.release(connection)
                else:
                    if pooled:
                        self._pool.discard(connection)
                    else:
                        try:
                            connection.close()
                        except Exception:
                            cleanup_failed = True
                if cleanup_failed and not had_active_error:
                    raise CrconDatabaseError("CRCON database cleanup failed.") from None


class _ReadConnectionPool:
    """Tiny bounded pool kept private so the repository remains the only SQL boundary."""

    def __init__(
        self,
        *,
        connector: Callable[[], Connector],
        connect: Callable[[Connector], Any],
        max_size: int,
        wait_timeout_seconds: float,
    ) -> None:
        self._connector = connector
        self._connect = connect
        self._max_size = max_size
        self._wait_timeout_seconds = wait_timeout_seconds
        self._condition = Condition()
        self._idle: list[Any] = []
        self._total = 0
        self._closed = False

    def acquire(self) -> Any:
        deadline = time.monotonic() + self._wait_timeout_seconds
        create = False
        with self._condition:
            while True:
                if self._closed:
                    raise CrconDatabaseError("CRCON database pool is closed.")
                if self._idle:
                    return self._idle.pop()
                if self._total < self._max_size:
                    self._total += 1
                    create = True
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise CrconDatabaseError("CRCON database pool is exhausted.")
                self._condition.wait(remaining)
        if create:
            try:
                return self._connect(self._connector())
            except Exception:
                with self._condition:
                    self._total -= 1
                    self._condition.notify()
                raise
        raise AssertionError("unreachable")

    def release(self, connection: Any) -> None:
        with self._condition:
            if self._closed:
                self._total -= 1
                close_now = True
            else:
                self._idle.append(connection)
                self._condition.notify()
                close_now = False
        if close_now:
            connection.close()

    def discard(self, connection: Any) -> None:
        try:
            connection.close()
        finally:
            with self._condition:
                self._total -= 1
                self._condition.notify()

    def close(self) -> None:
        with self._condition:
            self._closed = True
            idle, self._idle = self._idle, []
            self._total -= len(idle)
            self._condition.notify_all()
        for connection in idle:
            connection.close()


def _scope_query_values(
    scopes: tuple[CrconServerScope, ...],
) -> tuple[tuple[int, ...], int]:
    if not scopes:
        raise ValueError("At least one CRCON server scope is required.")
    games = {scope.game for scope in scopes}
    if len(games) != 1:
        raise ValueError("CRCON aggregate reads cannot merge games.")
    game = games.pop()
    game_number = 1 if game == "hll" else 2
    return tuple(sorted({scope.server_number for scope in scopes})), game_number


def _aggregate_query_params(
    server_numbers: tuple[int, ...],
    game: int,
    started_at: datetime | None,
    ended_at: datetime | None,
) -> tuple[object, ...]:
    if started_at is not None and ended_at is not None and ended_at <= started_at:
        raise ValueError("Aggregate window end must be after its start.")
    return (
        list(server_numbers),
        game,
        started_at,
        started_at,
        ended_at,
        ended_at,
    )


def _row_values(row: object, columns: tuple[str, ...]) -> tuple[object, ...]:
    if isinstance(row, Mapping):
        return tuple(row.get(column) for column in columns)
    if isinstance(row, (tuple, list)) and len(row) >= len(columns):
        return tuple(row[: len(columns)])
    raise CrconDatabaseError("CRCON aggregate query returned an unexpected row.")


def _ranking_row(row: object) -> CrconRankingRow:
    columns = (
        "player_id", "player_name", "matches_played", "record_kills", "kills",
        "deaths", "teamkills", "time_seconds", "combat", "offense", "defense",
        "support", "vehicle_kills", "vehicles_destroyed", "matches_over_100_kills",
        "ranking_position", "metric_value", "total_rows", "source_matches_count",
    )
    values = _row_values(row, columns)
    return CrconRankingRow(
        player_id=str(values[0]),
        player_name=str(values[1] or values[0]),
        matches_played=int(values[2] or 0),
        record_kills=int(values[3] or 0),
        kills=int(values[4] or 0),
        deaths=int(values[5] or 0),
        teamkills=int(values[6] or 0),
        time_seconds=int(values[7] or 0),
        combat=int(values[8] or 0),
        offense=int(values[9] or 0),
        defense=int(values[10] or 0),
        support=int(values[11] or 0),
        vehicle_kills=int(values[12] or 0),
        vehicles_destroyed=int(values[13] or 0),
        matches_over_100_kills=int(values[14] or 0),
        ranking_position=int(values[15] or 0),
        metric_value=float(values[16] or 0),
        total_rows=int(values[17] or 0),
        source_matches_count=int(values[18] or 0),
    )


def _player_profile_row(row: object) -> CrconPlayerProfileAggregate:
    columns = (
        "player_id", "player_name", "steam_id", "eos_id", "platform",
        "matches_played", "record_kills", "kills", "deaths", "teamkills",
        "deaths_by_teamkill", "time_seconds", "combat", "offense", "defense",
        "support", "vehicle_kills", "vehicles_destroyed", "last_seen_at",
        "servers_seen", "kills_ranking_position",
    )
    values = _row_values(row, columns)
    raw_servers = values[19] if isinstance(values[19], (list, tuple)) else ()
    return CrconPlayerProfileAggregate(
        player_id=str(values[0]),
        player_name=str(values[1] or values[0]),
        steam_id=str(values[2]) if values[2] is not None else None,
        eos_id=str(values[3]) if values[3] is not None else None,
        platform=str(values[4]) if values[4] is not None else None,
        matches_played=int(values[5] or 0),
        record_kills=int(values[6] or 0),
        kills=int(values[7] or 0),
        deaths=int(values[8] or 0),
        teamkills=int(values[9] or 0),
        deaths_by_teamkill=int(values[10] or 0),
        time_seconds=int(values[11] or 0),
        combat=int(values[12] or 0),
        offense=int(values[13] or 0),
        defense=int(values[14] or 0),
        support=int(values[15] or 0),
        vehicle_kills=int(values[16] or 0),
        vehicles_destroyed=int(values[17] or 0),
        last_seen_at=values[18] if isinstance(values[18], datetime) else None,
        servers_seen=tuple(int(value) for value in raw_servers),
        kills_ranking_position=int(values[20]) if values[20] is not None else None,
    )


def _load_connector() -> Connector:
    try:
        import psycopg
    except ImportError:  # pragma: no cover - environment specific
        raise CrconDatabaseError("CRCON database driver is unavailable.") from None
    return psycopg.connect


def _read_only_status(row: object) -> str | None:
    if isinstance(row, dict):
        value = row.get("transaction_read_only")
    elif isinstance(row, (tuple, list)) and row:
        value = row[0]
    else:
        value = None
    return str(value).strip().lower() if value is not None else None


def _schema_row(row: object) -> tuple[str, str]:
    if isinstance(row, dict):
        return str(row["table_name"]), str(row["column_name"])
    if isinstance(row, (tuple, list)) and len(row) >= 2:
        return str(row[0]), str(row[1])
    raise CrconDatabaseError("CRCON schema probe returned an unexpected row.")


def _current_map_row(row: object) -> CrconCurrentMap:
    if isinstance(row, dict):
        values = (
            row.get("id"),
            row.get("start"),
            row.get("end"),
            row.get("server_number"),
            row.get("map_name"),
            row.get("result"),
        )
    elif isinstance(row, (tuple, list)) and len(row) >= 6:
        values = tuple(row[:6])
    else:
        raise CrconDatabaseError("CRCON current map query returned an unexpected row.")
    map_id, start, end, server_number, map_name, result = values
    if not isinstance(start, datetime):
        raise CrconDatabaseError("CRCON current map query returned an invalid timestamp.")
    normalized_result = dict(result) if isinstance(result, dict) else None
    return CrconCurrentMap(
        id=int(map_id),
        start=start,
        end=end if isinstance(end, datetime) else None,
        server_number=int(server_number),
        map_name=str(map_name),
        result=normalized_result,
    )


def _match_log_event_row(row: object) -> CrconMatchLogEvent:
    if isinstance(row, dict):
        values = (
            row.get("id"),
            row.get("event_time"),
            row.get("type"),
            row.get("player1_name"),
            row.get("player1_id"),
            row.get("player2_name"),
            row.get("player2_id"),
            row.get("weapon"),
        )
    elif isinstance(row, (tuple, list)) and len(row) >= 8:
        values = tuple(row[:8])
    else:
        raise CrconDatabaseError("CRCON event query returned an unexpected row.")
    event_id, event_time, event_type, p1_name, p1_id, p2_name, p2_id, weapon = values
    if not isinstance(event_time, datetime):
        raise CrconDatabaseError("CRCON event query returned an invalid timestamp.")
    return CrconMatchLogEvent(
        id=int(event_id),
        event_time=event_time,
        type=str(event_type),
        player1_name=str(p1_name) if p1_name is not None else None,
        player1_id=str(p1_id) if p1_id is not None else None,
        player2_name=str(p2_name) if p2_name is not None else None,
        player2_id=str(p2_id) if p2_id is not None else None,
        weapon=str(weapon) if weapon is not None else None,
    )


def _match_combat_stats_row(row: object) -> CrconMatchCombatStats:
    if isinstance(row, dict):
        values = (
            row.get("player_id"),
            row.get("player_name"),
            row.get("kills"),
            row.get("deaths"),
            row.get("teamkills"),
            row.get("deaths_by_teamkill"),
            row.get("weapon_counts"),
        )
    elif isinstance(row, (tuple, list)) and len(row) >= 7:
        values = tuple(row[:7])
    else:
        raise CrconDatabaseError("CRCON combat aggregate returned an unexpected row.")
    player_id, player_name, kills, deaths, teamkills, deaths_by_teamkill, raw_weapons = values
    if isinstance(raw_weapons, str):
        try:
            raw_weapons = json.loads(raw_weapons)
        except json.JSONDecodeError:
            raise CrconDatabaseError(
                "CRCON combat aggregate returned invalid weapon counts."
            ) from None
    if raw_weapons is None:
        raw_weapons = {}
    if not isinstance(raw_weapons, Mapping):
        raise CrconDatabaseError("CRCON combat aggregate returned invalid weapon counts.")
    weapon_counts = tuple(
        sorted(
            (str(weapon), int(count))
            for weapon, count in raw_weapons.items()
            if str(weapon).strip() and int(count) > 0
        )
    )
    return CrconMatchCombatStats(
        player_id=str(player_id) if player_id is not None else None,
        player_name=str(player_name or "Unknown player"),
        kills=int(kills),
        deaths=int(deaths),
        teamkills=int(teamkills),
        deaths_by_teamkill=int(deaths_by_teamkill),
        weapon_counts=weapon_counts,
    )


def _player_aggregate_row(row: object) -> dict[str, int]:
    columns = (
        "matches_played",
        "record_kills",
        "total_kills",
        "deaths",
        "combat",
        "offense",
        "defense",
        "support",
        "vehicle_kills",
        "vehicles_destroyed",
    )
    if isinstance(row, Mapping):
        values = tuple(row.get(column) for column in columns)
    elif isinstance(row, (tuple, list)) and len(row) >= len(columns):
        values = tuple(row[: len(columns)])
    elif row is None:
        values = (0,) * len(columns)
    else:
        raise CrconDatabaseError("CRCON player aggregate returned an unexpected row.")
    return {
        column: int(value or 0)
        for column, value in zip(columns, values)
    }
