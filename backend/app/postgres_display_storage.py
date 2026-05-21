"""PostgreSQL read/write storage for data displayed outside the RCON write path."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .config import get_database_url, get_historical_weekly_fallback_max_weekday
from .historical_models import HistoricalSnapshotRecord
from .player_external_profiles import build_external_player_profile_fields
from .scoreboard_origins import resolve_trusted_scoreboard_match_url


ALL_SERVERS_SLUG = "all-servers"
ALL_SERVERS_DISPLAY_NAME = "Todos"
SUMMARY_SNAPSHOT_LIMIT = 6


DISPLAY_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS game_sources (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    provider_kind TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS servers (
    id BIGSERIAL PRIMARY KEY,
    game_source_id BIGINT NOT NULL REFERENCES game_sources(id),
    external_server_id TEXT,
    server_name TEXT NOT NULL,
    region TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(game_source_id, external_server_id)
);
CREATE TABLE IF NOT EXISTS server_snapshots (
    id BIGSERIAL PRIMARY KEY,
    server_id BIGINT NOT NULL REFERENCES servers(id),
    captured_at TEXT NOT NULL,
    status TEXT NOT NULL,
    players INTEGER,
    max_players INTEGER,
    current_map TEXT,
    source_name TEXT NOT NULL,
    snapshot_origin TEXT,
    source_ref TEXT,
    raw_payload_ref TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(server_id, captured_at, source_name, source_ref)
);
CREATE INDEX IF NOT EXISTS idx_pg_server_snapshots_server_time
ON server_snapshots(server_id, captured_at DESC);

CREATE TABLE IF NOT EXISTS historical_servers (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    scoreboard_base_url TEXT NOT NULL UNIQUE,
    server_number INTEGER,
    source_kind TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS historical_maps (
    id BIGSERIAL PRIMARY KEY,
    external_map_id TEXT UNIQUE,
    map_name TEXT,
    pretty_name TEXT,
    game_mode TEXT,
    image_name TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS historical_matches (
    id BIGSERIAL PRIMARY KEY,
    historical_server_id BIGINT NOT NULL REFERENCES historical_servers(id),
    external_match_id TEXT NOT NULL,
    historical_map_id BIGINT REFERENCES historical_maps(id),
    created_at_source TEXT,
    started_at TEXT,
    ended_at TEXT,
    map_name TEXT,
    map_pretty_name TEXT,
    game_mode TEXT,
    image_name TEXT,
    allied_score INTEGER,
    axis_score INTEGER,
    last_seen_at TEXT NOT NULL,
    raw_payload_ref TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(historical_server_id, external_match_id)
);
CREATE TABLE IF NOT EXISTS historical_players (
    id BIGSERIAL PRIMARY KEY,
    stable_player_key TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    steam_id TEXT,
    source_player_id TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS historical_player_match_stats (
    id BIGSERIAL PRIMARY KEY,
    historical_match_id BIGINT NOT NULL REFERENCES historical_matches(id),
    historical_player_id BIGINT NOT NULL REFERENCES historical_players(id),
    match_player_ref TEXT,
    team_side TEXT,
    level INTEGER,
    kills INTEGER,
    deaths INTEGER,
    teamkills INTEGER,
    time_seconds INTEGER,
    kills_per_minute DOUBLE PRECISION,
    deaths_per_minute DOUBLE PRECISION,
    kill_death_ratio DOUBLE PRECISION,
    combat INTEGER,
    offense INTEGER,
    defense INTEGER,
    support INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(historical_match_id, historical_player_id)
);
CREATE INDEX IF NOT EXISTS idx_pg_historical_matches_server_end
ON historical_matches(historical_server_id, ended_at DESC, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_pg_historical_player_stats_match
ON historical_player_match_stats(historical_match_id);

CREATE TABLE IF NOT EXISTS displayed_historical_snapshots (
    server_key TEXT NOT NULL,
    snapshot_type TEXT NOT NULL,
    metric TEXT NOT NULL DEFAULT '',
    snapshot_window TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    source_range_start TEXT,
    source_range_end TEXT,
    is_stale BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(server_key, snapshot_type, metric, snapshot_window)
);

CREATE TABLE IF NOT EXISTS player_event_raw_ledger (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    occurred_at TEXT,
    server_slug TEXT NOT NULL,
    external_match_id TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    source_ref TEXT,
    raw_event_ref TEXT,
    killer_player_key TEXT,
    killer_display_name TEXT,
    victim_player_key TEXT,
    victim_display_name TEXT,
    weapon_name TEXT,
    weapon_category TEXT,
    kill_category TEXT,
    is_teamkill BOOLEAN NOT NULL DEFAULT FALSE,
    event_value INTEGER NOT NULL DEFAULT 1,
    inserted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pg_player_event_raw_occurred_at
ON player_event_raw_ledger(occurred_at DESC);
"""


def initialize_postgres_display_storage() -> None:
    with connect_postgres() as connection:
        connection.execute(DISPLAY_SCHEMA_SQL)


def connect_postgres():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as error:  # pragma: no cover - environment-specific
        raise RuntimeError("psycopg is required when HLL_BACKEND_DATABASE_URL is set.") from error
    database_url = get_database_url()
    if not database_url:
        raise RuntimeError("HLL_BACKEND_DATABASE_URL is required for displayed PostgreSQL storage.")
    return psycopg.connect(database_url, row_factory=dict_row)


class PostgresCompatConnection:
    """Small placeholder shim for SQLite-shaped displayed read queries."""

    def __init__(self, connection: Any):
        self.connection = connection

    def execute(self, sql: str, params: Iterable[object] | None = None):
        return self.connection.execute(sql.replace("?", "%s"), tuple(params or ()))


@contextmanager
def connect_postgres_compat():
    initialize_postgres_display_storage()
    with connect_postgres() as connection:
        yield PostgresCompatConnection(connection)


def persist_snapshot_record(snapshot: Mapping[str, object]) -> HistoricalSnapshotRecord:
    initialize_postgres_display_storage()
    generated_at = _iso(snapshot.get("generated_at")) or _utc_now_iso()
    metric = str(snapshot.get("metric") or "")
    window = str(snapshot.get("window") or "")
    payload = snapshot.get("payload")
    payload_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    with connect_postgres() as connection:
        connection.execute(
            """
            INSERT INTO displayed_historical_snapshots (
                server_key, snapshot_type, metric, snapshot_window, payload_json, generated_at,
                source_range_start, source_range_end, is_stale
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(server_key, snapshot_type, metric, snapshot_window) DO UPDATE SET
                payload_json = EXCLUDED.payload_json,
                generated_at = EXCLUDED.generated_at,
                source_range_start = EXCLUDED.source_range_start,
                source_range_end = EXCLUDED.source_range_end,
                is_stale = EXCLUDED.is_stale,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                str(snapshot["server_key"]),
                str(snapshot["snapshot_type"]),
                metric,
                window,
                payload_json,
                generated_at,
                _iso(snapshot.get("source_range_start")),
                _iso(snapshot.get("source_range_end")),
                bool(snapshot.get("is_stale", False)),
            ),
        )
    return HistoricalSnapshotRecord(
        server_key=str(snapshot["server_key"]),
        snapshot_type=str(snapshot["snapshot_type"]),
        metric=metric or None,
        window=window or None,
        payload_json=payload_json,
        generated_at=_parse_datetime(generated_at) or datetime.now(timezone.utc),
        source_range_start=_parse_datetime(_iso(snapshot.get("source_range_start"))),
        source_range_end=_parse_datetime(_iso(snapshot.get("source_range_end"))),
        is_stale=bool(snapshot.get("is_stale", False)),
    )


def get_snapshot(
    *,
    server_key: str,
    snapshot_type: str,
    metric: str | None,
    window: str | None,
) -> dict[str, object] | None:
    initialize_postgres_display_storage()
    with connect_postgres() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM displayed_historical_snapshots
            WHERE server_key = %s AND snapshot_type = %s AND metric = %s AND snapshot_window = %s
            """,
            (server_key, snapshot_type, metric or "", window or ""),
        ).fetchone()
    if not row:
        return None
    return {
        "server_key": row["server_key"],
        "snapshot_type": row["snapshot_type"],
        "metric": row["metric"] or None,
        "window": row["snapshot_window"] or None,
        "generated_at": row["generated_at"],
        "source_range_start": row["source_range_start"],
        "source_range_end": row["source_range_end"],
        "is_stale": bool(row["is_stale"]),
        "payload": json.loads(row["payload_json"]),
    }


def list_latest_server_snapshots() -> list[dict[str, object]]:
    initialize_postgres_display_storage()
    with connect_postgres() as connection:
        rows = connection.execute(
            """
            SELECT s.id AS server_id, s.external_server_id, s.server_name, s.region,
                   g.slug AS context, snap.source_name, snap.snapshot_origin,
                   snap.source_ref, snap.captured_at, snap.status, snap.players,
                   snap.max_players, snap.current_map
            FROM servers AS s
            JOIN game_sources AS g ON g.id = s.game_source_id
            JOIN server_snapshots AS snap ON snap.server_id = s.id
            JOIN (
                SELECT server_id, MAX(captured_at) AS captured_at
                FROM server_snapshots GROUP BY server_id
            ) AS latest ON latest.server_id = snap.server_id
                       AND latest.captured_at = snap.captured_at
            ORDER BY s.server_name ASC
            """
        ).fetchall()
        return [_attach_server_history(connection, dict(row)) for row in rows]


def persist_server_snapshots(
    snapshots: Iterable[Mapping[str, object]],
    *,
    source_name: str,
    captured_at: str,
    game_source: Mapping[str, str],
) -> dict[str, object]:
    initialize_postgres_display_storage()
    persisted = 0
    with connect_postgres() as connection:
        source = connection.execute(
            """
            INSERT INTO game_sources (slug, display_name, provider_kind, is_active)
            VALUES (%s, %s, %s, TRUE)
            ON CONFLICT(slug) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                provider_kind = EXCLUDED.provider_kind,
                is_active = TRUE,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """,
            (game_source["slug"], game_source["display_name"], game_source["provider_kind"]),
        ).fetchone()
        for snapshot in snapshots:
            external_server_id = str(snapshot.get("external_server_id") or "").strip()
            if not external_server_id:
                external_server_id = _fallback_external_id(snapshot.get("server_name"))
            server = connection.execute(
                """
                INSERT INTO servers (
                    game_source_id, external_server_id, server_name, region,
                    first_seen_at, last_seen_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(game_source_id, external_server_id) DO UPDATE SET
                    server_name = EXCLUDED.server_name,
                    region = EXCLUDED.region,
                    last_seen_at = EXCLUDED.last_seen_at,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                (
                    source["id"],
                    external_server_id,
                    str(snapshot.get("server_name") or "Unknown server"),
                    snapshot.get("region"),
                    captured_at,
                    captured_at,
                ),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO server_snapshots (
                    server_id, captured_at, status, players, max_players, current_map,
                    source_name, snapshot_origin, source_ref, raw_payload_ref
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
                ON CONFLICT(server_id, captured_at, source_name, source_ref) DO UPDATE SET
                    status = EXCLUDED.status,
                    players = EXCLUDED.players,
                    max_players = EXCLUDED.max_players,
                    current_map = EXCLUDED.current_map,
                    snapshot_origin = EXCLUDED.snapshot_origin
                """,
                (
                    server["id"],
                    captured_at,
                    snapshot.get("status") or "unknown",
                    snapshot.get("players"),
                    snapshot.get("max_players"),
                    snapshot.get("current_map"),
                    snapshot.get("source_name") or source_name,
                    snapshot.get("snapshot_origin"),
                    snapshot.get("source_ref") or snapshot.get("source_name") or source_name,
                ),
            )
            persisted += 1
    return {
        "db_path": "postgresql",
        "captured_at": captured_at,
        "persisted_snapshots": persisted,
        "game_source_slug": game_source["slug"],
    }


def upsert_player_event_rows(events: Iterable[object]) -> dict[str, int]:
    initialize_postgres_display_storage()
    inserted = 0
    duplicates = 0
    with connect_postgres() as connection:
        for event in events:
            row = connection.execute(
                """
                INSERT INTO player_event_raw_ledger (
                    event_id, event_type, occurred_at, server_slug, external_match_id,
                    source_kind, source_ref, raw_event_ref, killer_player_key,
                    killer_display_name, victim_player_key, victim_display_name,
                    weapon_name, weapon_category, kill_category, is_teamkill, event_value
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(event_id) DO NOTHING
                RETURNING id
                """,
                (
                    event.event_id,
                    event.event_type,
                    event.occurred_at,
                    event.server_slug,
                    event.external_match_id,
                    event.source_kind,
                    event.source_ref,
                    event.raw_event_ref,
                    event.killer_player_key,
                    event.killer_display_name,
                    event.victim_player_key,
                    event.victim_display_name,
                    event.weapon_name,
                    event.weapon_category,
                    event.kill_category,
                    bool(event.is_teamkill),
                    max(1, int(event.event_value)),
                ),
            ).fetchone()
            inserted += int(bool(row))
            duplicates += int(not row)
    return {"events_inserted": inserted, "duplicate_events": duplicates}


def list_server_snapshot_history(*, server_id: str | None = None, limit: int) -> list[dict[str, object]]:
    initialize_postgres_display_storage()
    where = ""
    params: list[object] = []
    if server_id:
        if server_id.strip().isdigit():
            where = "WHERE s.id = %s"
            params.append(int(server_id))
        else:
            where = "WHERE s.external_server_id = %s"
            params.append(server_id.strip())
    with connect_postgres() as connection:
        rows = connection.execute(
            f"""
            SELECT s.id AS server_id, s.external_server_id, s.server_name, s.region,
                   g.slug AS context, snap.source_name, snap.snapshot_origin,
                   snap.source_ref, snap.captured_at, snap.status, snap.players,
                   snap.max_players, snap.current_map
            FROM server_snapshots AS snap
            JOIN servers AS s ON s.id = snap.server_id
            JOIN game_sources AS g ON g.id = s.game_source_id
            {where}
            ORDER BY snap.captured_at DESC, s.server_name ASC
            LIMIT %s
            """,
            (*params, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def list_recent_scoreboard_matches(*, server_slug: str | None, limit: int) -> list[dict[str, object]]:
    initialize_postgres_display_storage()
    where = ""
    params: list[object] = []
    if server_slug and server_slug != ALL_SERVERS_SLUG:
        where = "WHERE hs.slug = %s"
        params.append(server_slug)
    with connect_postgres() as connection:
        rows = connection.execute(
            f"""
            SELECT hs.slug AS server_slug, hs.display_name AS server_name,
                   hm.external_match_id, hm.started_at, hm.ended_at,
                   hm.map_pretty_name, hm.map_name, hm.allied_score, hm.axis_score,
                   hm.raw_payload_ref, COUNT(stats.id) AS player_count
            FROM historical_matches AS hm
            JOIN historical_servers AS hs ON hs.id = hm.historical_server_id
            LEFT JOIN historical_player_match_stats AS stats ON stats.historical_match_id = hm.id
            {where}
            GROUP BY hm.id, hs.slug, hs.display_name
            ORDER BY COALESCE(hm.ended_at, hm.started_at) DESC
            LIMIT %s
            """,
            (*params, limit),
        ).fetchall()
    return [_recent_match_row(row) for row in rows]


def get_scoreboard_match_detail(*, server_slug: str, match_id: str) -> dict[str, object] | None:
    initialize_postgres_display_storage()
    with connect_postgres() as connection:
        row = connection.execute(
            """
            SELECT hm.id AS match_pk, hs.slug AS server_slug, hs.display_name AS server_name,
                   hm.external_match_id, hm.started_at, hm.ended_at, hm.map_pretty_name,
                   hm.map_name, hm.allied_score, hm.axis_score, hm.raw_payload_ref,
                   COUNT(stats.id) AS player_count,
                   SUM(COALESCE(stats.time_seconds, 0)) AS total_time_seconds
            FROM historical_matches AS hm
            JOIN historical_servers AS hs ON hs.id = hm.historical_server_id
            LEFT JOIN historical_player_match_stats AS stats ON stats.historical_match_id = hm.id
            WHERE hs.slug = %s AND hm.external_match_id = %s
            GROUP BY hm.id, hs.slug, hs.display_name
            LIMIT 1
            """,
            (server_slug, match_id),
        ).fetchone()
        if not row:
            return None
        players = connection.execute(
            """
            SELECT hp.display_name, hp.stable_player_key, hp.steam_id, stats.team_side, stats.level,
                   stats.kills, stats.deaths, stats.teamkills, stats.combat, stats.offense,
                   stats.defense, stats.support, stats.time_seconds
            FROM historical_player_match_stats AS stats
            JOIN historical_players AS hp ON hp.id = stats.historical_player_id
            WHERE stats.historical_match_id = %s
            ORDER BY COALESCE(stats.kills, 0) DESC, hp.display_name ASC
            """,
            (row["match_pk"],),
        ).fetchall()
    started_at = row["started_at"]
    ended_at = row["ended_at"]
    return {
        "server": {"slug": row["server_slug"], "name": row["server_name"]},
        "match_id": row["external_match_id"],
        "started_at": started_at,
        "ended_at": ended_at,
        "closed_at": ended_at or started_at,
        "duration_seconds": _duration_seconds(started_at, ended_at),
        "map": {"name": row["map_name"], "pretty_name": row["map_pretty_name"] or row["map_name"]},
        "result": _match_result(row["allied_score"], row["axis_score"]),
        "player_count": int(row["player_count"] or 0),
        "total_time_seconds": _int(row["total_time_seconds"]),
        "players": [
            {
                "name": player["display_name"],
                "stable_player_key": player["stable_player_key"],
                "team_side": player["team_side"],
                **build_external_player_profile_fields(steam_id=player["steam_id"]),
                **{
                    key: _int(player[key])
                    for key in (
                        "level", "kills", "deaths", "teamkills", "combat",
                        "offense", "defense", "support", "time_seconds",
                    )
                },
            }
            for player in players
        ],
        "capture_basis": "public-scoreboard-match",
        "match_url": resolve_trusted_scoreboard_match_url(row["raw_payload_ref"], row["server_slug"]),
    }


def list_scoreboard_server_summaries(*, server_slug: str | None) -> list[dict[str, object]]:
    initialize_postgres_display_storage()
    if server_slug == ALL_SERVERS_SLUG:
        rows = list_scoreboard_server_summaries(server_slug=None)
        return [_all_server_summary(rows)]
    where = "WHERE hs.slug = %s" if server_slug else ""
    params = (server_slug,) if server_slug else ()
    with connect_postgres() as connection:
        rows = connection.execute(
            f"""
            SELECT hs.slug AS server_slug, hs.display_name AS server_name,
                   COUNT(DISTINCT hm.id) AS matches_count,
                   COUNT(DISTINCT hp.id) AS unique_players,
                   COALESCE(SUM(stats.kills), 0) AS total_kills,
                   COUNT(DISTINCT COALESCE(hm.map_pretty_name, hm.map_name)) AS map_count,
                   MIN(COALESCE(hm.ended_at, hm.started_at, hm.created_at_source)) AS first_match_at,
                   MAX(COALESCE(hm.ended_at, hm.started_at, hm.created_at_source)) AS last_match_at
            FROM historical_servers AS hs
            LEFT JOIN historical_matches AS hm ON hm.historical_server_id = hs.id
            LEFT JOIN historical_player_match_stats AS stats ON stats.historical_match_id = hm.id
            LEFT JOIN historical_players AS hp ON hp.id = stats.historical_player_id
            {where}
            GROUP BY hs.id
            ORDER BY hs.server_number ASC, hs.slug ASC
            """,
            params,
        ).fetchall()
        map_rows = connection.execute(
            f"""
            SELECT hs.slug AS server_slug,
                   COALESCE(hm.map_pretty_name, hm.map_name, 'Mapa no disponible') AS map_name,
                   COUNT(*) AS matches_count
            FROM historical_matches AS hm
            JOIN historical_servers AS hs ON hs.id = hm.historical_server_id
            {where}
            GROUP BY hs.slug, COALESCE(hm.map_pretty_name, hm.map_name, 'Mapa no disponible')
            ORDER BY hs.slug ASC, matches_count DESC, map_name ASC
            """,
            params,
        ).fetchall()
    maps: dict[str, list[dict[str, object]]] = {}
    for row in map_rows:
        maps.setdefault(str(row["server_slug"]), [])
        if len(maps[str(row["server_slug"])]) < 3:
            maps[str(row["server_slug"])].append(
                {"map_name": row["map_name"], "matches_count": int(row["matches_count"] or 0)}
            )
    return [_summary_row(row, maps.get(str(row["server_slug"]), [])) for row in rows]


def list_scoreboard_leaderboard(
    *, timeframe: str, metric: str, server_id: str | None, limit: int
) -> dict[str, object]:
    current = datetime.now(timezone.utc)
    if timeframe == "monthly":
        current_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        previous_start = (current_start - timedelta(days=1)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        label = ("current-month", "Mes actual", "previous-closed-month-fallback", "Mes cerrado anterior")
    else:
        current_midnight = current.replace(hour=0, minute=0, second=0, microsecond=0)
        current_start = current_midnight - timedelta(days=current_midnight.weekday())
        previous_start = current_start - timedelta(days=7)
        label = ("current-week", "Semana actual", "previous-closed-week-fallback", "Semana cerrada anterior")
    current_count = _count_scoreboard_matches(server_id, current_start, current)
    previous_count = _count_scoreboard_matches(server_id, previous_start, current_start)
    fallback = current_count <= 0 and previous_count > 0
    start, end = (previous_start, current_start) if fallback else (current_start, current)
    rows = _leaderboard_rows(server_id=server_id, metric=metric, start=start, end=end, limit=limit)
    window_days = max(1, int(((end - start).total_seconds() + 86399) // 86400))
    result = {
        "metric": metric,
        "window_start": _iso(start),
        "window_end": _iso(end),
        "window_days": window_days,
        "window_kind": label[2] if fallback else label[0],
        "window_label": label[3] if fallback else label[1],
        "uses_fallback": fallback,
        "selection_reason": (
            "no-current-month-matches" if fallback and timeframe == "monthly"
            else "insufficient-current-week-sample" if fallback
            else label[0]
        ),
        "items": rows,
    }
    if timeframe == "monthly":
        result.update(
            {
                "timeframe": "monthly",
                "current_month_start": _iso(current_start),
                "current_month_closed_matches": current_count,
                "previous_month_closed_matches": previous_count,
                "sufficient_sample": {
                    "minimum_closed_matches": 1,
                    "current_month_closed_matches": current_count,
                    "current_month_has_sufficient_sample": current_count > 0,
                    "is_early_month": current.day <= 3,
                },
            }
        )
    else:
        result.update(
            {
                "current_week_start": _iso(current_start),
                "current_week_closed_matches": current_count,
                "previous_week_closed_matches": previous_count,
                "sufficient_sample": {
                    "minimum_closed_matches": 1,
                    "current_week_closed_matches": current_count,
                    "current_week_has_sufficient_sample": current_count > 0,
                    "is_early_week": current.weekday() <= get_historical_weekly_fallback_max_weekday(),
                    "fallback_max_weekday": get_historical_weekly_fallback_max_weekday(),
                },
            }
        )
    return result


def table_counts() -> dict[str, int]:
    initialize_postgres_display_storage()
    tables = (
        "historical_matches",
        "historical_player_match_stats",
        "displayed_historical_snapshots",
        "player_event_raw_ledger",
        "server_snapshots",
    )
    with connect_postgres() as connection:
        return {
            table: int(connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"] or 0)
            for table in tables
        }


def _leaderboard_rows(
    *, server_id: str | None, metric: str, start: datetime, end: datetime, limit: int
) -> list[dict[str, object]]:
    metric_sql = {
        "kills": "COALESCE(SUM(stats.kills), 0)",
        "deaths": "COALESCE(SUM(stats.deaths), 0)",
        "support": "COALESCE(SUM(stats.support), 0)",
        "matches_over_100_kills": (
            "COALESCE(SUM(CASE WHEN COALESCE(stats.kills, 0) >= 100 THEN 1 ELSE 0 END), 0)"
        ),
    }[metric]
    aggregate = server_id == ALL_SERVERS_SLUG
    where, server_params = _server_where(server_id)
    server_slug = f"'{ALL_SERVERS_SLUG}'" if aggregate else "hs.slug"
    server_name = f"'{ALL_SERVERS_DISPLAY_NAME}'" if aggregate else "hs.display_name"
    partition = f"'{ALL_SERVERS_SLUG}'" if aggregate else "hs.slug"
    group_by = "hp.id" if aggregate else "hs.slug, hs.display_name, hp.id"
    with connect_postgres() as connection:
        rows = connection.execute(
            f"""
            WITH ranked AS (
                SELECT {server_slug} AS server_slug, {server_name} AS server_name,
                       hp.stable_player_key, hp.display_name AS player_name, hp.steam_id,
                       COUNT(DISTINCT hm.id) AS matches_count, {metric_sql} AS metric_value,
                       ROW_NUMBER() OVER (
                           PARTITION BY {partition}
                           ORDER BY {metric_sql} DESC, COUNT(DISTINCT hm.id) ASC, hp.display_name ASC
                       ) AS ranking_position
                FROM historical_player_match_stats AS stats
                JOIN historical_matches AS hm ON hm.id = stats.historical_match_id
                JOIN historical_servers AS hs ON hs.id = hm.historical_server_id
                JOIN historical_players AS hp ON hp.id = stats.historical_player_id
                WHERE hm.ended_at IS NOT NULL AND hm.ended_at >= %s AND hm.ended_at < %s {where}
                GROUP BY {group_by}
            )
            SELECT * FROM ranked WHERE ranking_position <= %s
            ORDER BY server_slug ASC, ranking_position ASC
            """,
            (_iso(start), _iso(end), *server_params, limit),
        ).fetchall()
    return [
        {
            "server": {"slug": row["server_slug"], "name": row["server_name"]},
            "time_range": {"start": _iso(start), "end": _iso(end), "window_days": max(1, (end - start).days or 1)},
            "player": {
                "stable_player_key": row["stable_player_key"],
                "name": row["player_name"],
                "steam_id": row["steam_id"],
            },
            "metric": metric,
            "ranking_position": int(row["ranking_position"]),
            "metric_value": int(row["metric_value"] or 0),
            "matches_considered": int(row["matches_count"] or 0),
        }
        for row in rows
    ]


def _count_scoreboard_matches(server_id: str | None, start: datetime, end: datetime) -> int:
    where, server_params = _server_where(server_id)
    with connect_postgres() as connection:
        row = connection.execute(
            f"""
            SELECT COUNT(DISTINCT hm.id) AS count
            FROM historical_matches AS hm
            JOIN historical_servers AS hs ON hs.id = hm.historical_server_id
            JOIN historical_player_match_stats AS stats ON stats.historical_match_id = hm.id
            WHERE hm.ended_at IS NOT NULL AND hm.ended_at >= %s AND hm.ended_at < %s {where}
            """,
            (_iso(start), _iso(end), *server_params),
        ).fetchone()
    return int(row["count"] or 0)


def _server_where(server_id: str | None) -> tuple[str, tuple[object, ...]]:
    if not server_id or server_id == ALL_SERVERS_SLUG:
        return "", ()
    return "AND (hs.slug = %s OR CAST(hs.server_number AS TEXT) = %s)", (server_id, server_id)


def _recent_match_row(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "server": {"slug": row["server_slug"], "name": row["server_name"]},
        "match_id": row["external_match_id"],
        "started_at": row["started_at"],
        "ended_at": row["ended_at"],
        "closed_at": row["ended_at"] or row["started_at"],
        "map": {"name": row["map_name"], "pretty_name": row["map_pretty_name"] or row["map_name"]},
        "result": _match_result(row["allied_score"], row["axis_score"]),
        "player_count": int(row["player_count"] or 0),
        "match_url": resolve_trusted_scoreboard_match_url(row["raw_payload_ref"], row["server_slug"]),
    }


def _summary_row(row: Mapping[str, object], top_maps: list[dict[str, object]]) -> dict[str, object]:
    first = row["first_match_at"]
    last = row["last_match_at"]
    matches = int(row["matches_count"] or 0)
    return {
        "server": {"slug": row["server_slug"], "name": row["server_name"]},
        "matches_count": matches,
        "imported_matches_count": matches,
        "unique_players": int(row["unique_players"] or 0),
        "total_kills": int(row["total_kills"] or 0),
        "map_count": int(row["map_count"] or 0),
        "top_maps": top_maps,
        "coverage": {
            "basis": "postgres-migrated-public-scoreboard",
            "status": "available" if matches else "empty",
            "imported_matches_count": matches,
            "discovered_total_matches": None,
            "first_match_at": first,
            "last_match_at": last,
            "coverage_days": _coverage_days(first, last),
        },
        "backfill": {},
        "time_range": {"start": first, "end": last},
    }


def _all_server_summary(items: list[dict[str, object]]) -> dict[str, object]:
    starts = [item["time_range"]["start"] for item in items if item["time_range"]["start"]]
    ends = [item["time_range"]["end"] for item in items if item["time_range"]["end"]]
    return {
        "server": {"slug": ALL_SERVERS_SLUG, "name": ALL_SERVERS_DISPLAY_NAME},
        "matches_count": sum(int(item["matches_count"]) for item in items),
        "imported_matches_count": sum(int(item["imported_matches_count"]) for item in items),
        "unique_players": None,
        "total_kills": sum(int(item["total_kills"]) for item in items),
        "map_count": None,
        "top_maps": [],
        "coverage": {"basis": "postgres-migrated-public-scoreboard", "status": "available" if items else "empty"},
        "backfill": {},
        "time_range": {"start": min(starts) if starts else None, "end": max(ends) if ends else None},
    }


def _attach_server_history(connection: Any, item: dict[str, object]) -> dict[str, object]:
    rows = connection.execute(
        """
        SELECT captured_at, status, players FROM server_snapshots
        WHERE server_id = %s ORDER BY captured_at DESC LIMIT %s
        """,
        (item["server_id"], SUMMARY_SNAPSHOT_LIMIT),
    ).fetchall()
    players = [int(row["players"]) for row in rows if row["players"] is not None]
    online = [row for row in rows if row["status"] == "online"]
    item["history_summary"] = {
        "window_size": SUMMARY_SNAPSHOT_LIMIT,
        "recent_capture_count": len(rows),
        "recent_online_count": len(online),
        "recent_average_players": round(sum(players) / len(players), 1) if players else None,
        "recent_peak_players": max(players, default=None),
        "last_seen_online_at": online[0]["captured_at"] if online else None,
        "minutes_since_last_capture": _minutes_since(rows[0]["captured_at"]) if rows else None,
    }
    return item


def _match_result(allied: object, axis: object) -> dict[str, object]:
    allied_int, axis_int = _int(allied), _int(axis)
    winner = None
    if allied_int is not None and axis_int is not None:
        winner = "allied" if allied_int > axis_int else "axis" if axis_int > allied_int else "draw"
    return {"allied_score": allied_int, "axis_score": axis_int, "winner": winner}


def _duration_seconds(start: object, end: object) -> int | None:
    start_point, end_point = _parse_datetime(_iso(start)), _parse_datetime(_iso(end))
    return max(0, int((end_point - start_point).total_seconds())) if start_point and end_point else None


def _coverage_days(start: object, end: object) -> int | None:
    seconds = _duration_seconds(start, end)
    return max(1, int((seconds + 86399) // 86400)) if seconds is not None else None


def _minutes_since(value: object) -> int | None:
    point = _parse_datetime(_iso(value))
    return max(0, int((datetime.now(timezone.utc) - point).total_seconds() // 60)) if point else None


def _int(value: object) -> int | None:
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        return None


def _fallback_external_id(value: object) -> str:
    normalized = "".join(
        character.lower() if character.isalnum() else "-"
        for character in str(value or "unknown-server")
    )
    compact = "-".join(part for part in normalized.split("-") if part)
    return compact or "unknown-server"


def _iso(value: object) -> str | None:
    if isinstance(value, datetime):
        point = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return point.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    text = str(value or "").strip()
    return text or None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        point = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return point.astimezone(timezone.utc) if point.tzinfo else point.replace(tzinfo=timezone.utc)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
