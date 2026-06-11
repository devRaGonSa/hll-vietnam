"""Search helpers for RCON materialized player statistics."""

from __future__ import annotations

import argparse
import json
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
import unicodedata

from .config import get_kpm_min_active_seconds
from .config import get_storage_path, use_postgres_rcon_storage
from .historical_storage import ALL_SERVERS_SLUG
from .player_external_profiles import build_external_player_profile_fields
from .rcon_admin_log_materialization import MATCH_RESULT_SOURCE, initialize_rcon_materialized_storage
from .rcon_historical_leaderboards import select_leaderboard_window
from .sqlite_utils import connect_sqlite_readonly, connect_sqlite_writer
from .rcon_historical_leaderboards import _to_iso

REAL_KPM_ACTIVE_TIME_SOURCES = (
    "connection_intervals",
    "connection_intervals_carryover",
)

PLAYER_SEARCH_INDEX_SERVER_KEYS = (
    ALL_SERVERS_SLUG,
    "comunidad-hispana-01",
    "comunidad-hispana-02",
)
PLAYER_PERIOD_STATS_PERIOD_TYPES = ("weekly", "monthly", "yearly")

PLAYER_SEARCH_INDEX_SQLITE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS player_search_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    normalized_player_name TEXT NOT NULL,
    first_seen_at TEXT,
    last_seen_at TEXT,
    servers_seen TEXT NOT NULL DEFAULT '[]',
    matches_current_year INTEGER NOT NULL DEFAULT 0,
    kills_current_year INTEGER NOT NULL DEFAULT 0,
    deaths_current_year INTEGER NOT NULL DEFAULT 0,
    teamkills_current_year INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(server_id, player_id)
);

CREATE INDEX IF NOT EXISTS idx_player_search_index_name
ON player_search_index(server_id, normalized_player_name);

CREATE INDEX IF NOT EXISTS idx_player_search_index_last_seen
ON player_search_index(server_id, last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_player_search_index_player
ON player_search_index(server_id, player_id);
"""

PLAYER_PERIOD_STATS_SQLITE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS player_period_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_type TEXT NOT NULL,
    window_kind TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    server_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    matches_considered INTEGER NOT NULL DEFAULT 0,
    kills INTEGER NOT NULL DEFAULT 0,
    deaths INTEGER NOT NULL DEFAULT 0,
    teamkills INTEGER NOT NULL DEFAULT 0,
    ranking_position INTEGER,
    kd_ratio REAL NOT NULL DEFAULT 0.0,
    kills_per_match REAL NOT NULL DEFAULT 0.0,
    first_seen_at TEXT,
    last_seen_at TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(period_type, server_id, player_id)
);

CREATE INDEX IF NOT EXISTS idx_player_period_stats_player_period_server
ON player_period_stats(player_id, period_type, server_id);

CREATE INDEX IF NOT EXISTS idx_player_period_stats_server_period
ON player_period_stats(server_id, period_type);

CREATE INDEX IF NOT EXISTS idx_player_period_stats_last_seen
ON player_period_stats(last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_player_period_stats_updated
ON player_period_stats(updated_at DESC);
"""


def initialize_player_search_index_storage(*, db_path: Path | None = None) -> Path:
    """Create the player search read model storage if it does not exist."""
    resolved_path = initialize_rcon_materialized_storage(db_path=db_path)
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import initialize_postgres_rcon_storage

        initialize_postgres_rcon_storage()
        return resolved_path

    with closing(connect_sqlite_writer(resolved_path)) as connection:
        with connection:
            connection.executescript(PLAYER_SEARCH_INDEX_SQLITE_SCHEMA_SQL)
    return resolved_path


def initialize_player_period_stats_storage(*, db_path: Path | None = None) -> Path:
    """Create the player period stats read model storage if it does not exist."""
    resolved_path = initialize_rcon_materialized_storage(db_path=db_path)
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import initialize_postgres_rcon_storage

        initialize_postgres_rcon_storage()
        return resolved_path

    with closing(connect_sqlite_writer(resolved_path)) as connection:
        with connection:
            connection.executescript(PLAYER_PERIOD_STATS_SQLITE_SCHEMA_SQL)
    return resolved_path


def refresh_player_search_index(
    *,
    db_path: Path | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    """Rebuild the player search read model from current-year materialized matches."""
    anchor = _as_utc(now or datetime.now(timezone.utc))
    year_start = anchor.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    next_year_start = year_start.replace(year=year_start.year + 1)
    resolved_path = initialize_player_search_index_storage(db_path=db_path)

    results: list[dict[str, object]] = []
    total_rows = 0
    with _connect_write_scope(resolved_path, db_path=db_path) as connection:
        for server_id in PLAYER_SEARCH_INDEX_SERVER_KEYS:
            rows = _build_player_search_index_rows(
                connection=connection,
                server_id=server_id,
                year_start=year_start,
                next_year_start=next_year_start,
            )
            _replace_player_search_index_scope(
                connection=connection,
                server_id=server_id,
                rows=rows,
                updated_at=_to_iso(anchor),
            )
            results.append(
                {
                    "server_id": server_id,
                    "row_count": len(rows),
                }
            )
            total_rows += len(rows)

    return {
        "status": "ok",
        "generated_at": _to_iso(anchor),
        "year": year_start.year,
        "source": "rcon-materialized-admin-log",
        "server_ids": list(PLAYER_SEARCH_INDEX_SERVER_KEYS),
        "total_rows": total_rows,
        "results": results,
    }


def refresh_player_period_stats(
    *,
    db_path: Path | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    """Rebuild the personal player stats read model for supported periods and scopes."""
    anchor = _as_utc(now or datetime.now(timezone.utc))
    resolved_path = initialize_player_period_stats_storage(db_path=db_path)

    results: list[dict[str, object]] = []
    total_rows = 0
    with _connect_write_scope(resolved_path, db_path=db_path) as connection:
        for server_id in PLAYER_SEARCH_INDEX_SERVER_KEYS:
            for period_type in PLAYER_PERIOD_STATS_PERIOD_TYPES:
                window = _select_player_period_window(
                    connection=connection,
                    server_id=server_id,
                    period_type=period_type,
                    now=anchor,
                )
                rows = _build_player_period_stats_rows(
                    connection=connection,
                    server_id=server_id,
                    period_type=period_type,
                    window=window,
                )
                _replace_player_period_stats_scope(
                    connection=connection,
                    server_id=server_id,
                    period_type=period_type,
                    rows=rows,
                    updated_at=_to_iso(anchor),
                )
                results.append(
                    {
                        "server_id": server_id,
                        "period_type": period_type,
                        "window_kind": window["kind"],
                        "period_start": _to_iso(window["start"]),
                        "period_end": _to_iso(window["end"]),
                        "row_count": len(rows),
                    }
                )
                total_rows += len(rows)

    return {
        "status": "ok",
        "generated_at": _to_iso(anchor),
        "source": "rcon-materialized-admin-log",
        "server_ids": list(PLAYER_SEARCH_INDEX_SERVER_KEYS),
        "period_types": list(PLAYER_PERIOD_STATS_PERIOD_TYPES),
        "total_rows": total_rows,
        "results": results,
    }


def search_rcon_materialized_players(
    *,
    query: str,
    server_id: str | None = None,
    limit: int = 10,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Search players from the public read model without runtime fallback."""
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("Query cannot be empty.")

    read_model_result, fallback_reason = _search_player_search_index(
        query=normalized_query,
        server_id=server_id,
        limit=limit,
        db_path=db_path,
    )
    if read_model_result is not None:
        return read_model_result

    resolved_server_id = _normalize_server_id(server_id)
    return {
        "server_id": resolved_server_id,
        "query": normalized_query,
        "items": [],
        "source": {
            "read_model": "player-search-index",
            "status": "unavailable",
            "fallback_used": False,
            "fallback_reason": None,
            "missing_reason": fallback_reason or "player-search-index-unavailable",
        },
    }


def _search_rcon_materialized_players_runtime(
    *,
    query: str,
    server_id: str | None = None,
    limit: int = 10,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Search players directly in materialized RCON/AdminLog statistics."""
    normalized_query = query.strip()
    resolved_path = initialize_rcon_materialized_storage(db_path=db_path)
    resolved_server_id = _normalize_server_id(server_id)
    normalized_pattern = _escape_like_pattern(normalized_query)
    like_pattern = f"%{normalized_pattern.lower()}%"

    connection_scope = _connect_scope(resolved_path, db_path=db_path)
    with connection_scope as connection:
        scope_sql, scope_params = _build_scope_sql(resolved_server_id)
        rows = connection.execute(
            f"""
            SELECT
                stats.player_id,
                COUNT(DISTINCT stats.match_key) AS matches_considered,
                MAX(COALESCE(matches.ended_at, matches.started_at)) AS last_seen_at
            FROM rcon_match_player_stats AS stats
            INNER JOIN rcon_materialized_matches AS matches
                ON matches.target_key = stats.target_key
               AND matches.match_key = stats.match_key
            WHERE matches.source_basis = ?
              AND (
                  LOWER(COALESCE(stats.player_name, '')) LIKE LOWER(?) ESCAPE '\\'
                  OR LOWER(stats.player_id) LIKE LOWER(?)
              )
              {scope_sql}
            GROUP BY stats.player_id
            ORDER BY matches_considered DESC, MAX(COALESCE(matches.ended_at, matches.started_at)) DESC
            LIMIT ?
            """,
            [MATCH_RESULT_SOURCE, like_pattern, like_pattern, *scope_params, limit],
        ).fetchall()

    player_rows = [_normalize_player_row(row) for row in rows]
    player_ids = [row["player_id"] for row in player_rows if isinstance(row["player_id"], str)]
    if not player_ids:
        return {
            "server_id": resolved_server_id,
            "query": normalized_query,
            "items": [],
        }

    latest_names = _lookup_latest_player_names(
        db_path=resolved_path,
        player_ids=player_ids,
        server_id=resolved_server_id,
        pattern_like=like_pattern,
    )
    servers_seen = _lookup_servers_seen(
        db_path=resolved_path,
        player_ids=player_ids,
        server_id=resolved_server_id,
    )

    items: list[dict[str, object]] = []
    for row in player_rows:
        player_id = str(row["player_id"] or "").strip()
        if not player_id:
            continue

        item: dict[str, object] = {
            "player_id": player_id,
            "player_name": latest_names.get(player_id) or row["player_name"],
            "matches_considered": int(row["matches_considered"] or 0),
            "last_seen_at": row["last_seen_at"],
        }
        if player_ids:
            item["servers_seen"] = servers_seen.get(player_id, [])
        items.append(item)

    return {
        "server_id": resolved_server_id,
        "query": normalized_query,
        "items": items,
        "source": {
            "read_model": "rcon-materialized-admin-log-player-stats",
            "fallback_used": False,
            "fallback_reason": None,
        },
    }


def get_rcon_materialized_player_stats(
    *,
    player_id: str,
    server_id: str | None = None,
    timeframe: str = "weekly",
    db_path: Path | None = None,
) -> dict[str, object]:
    """Return personal stats and weekly/monthly ranking context for one player."""
    normalized_player_id = player_id.strip()
    if not normalized_player_id:
        raise ValueError("player_id is required")

    resolved_timeframe = timeframe.strip().lower() if isinstance(timeframe, str) else "weekly"
    if resolved_timeframe not in {"weekly", "monthly", "all"}:
        raise ValueError("Invalid timeframe parameter")

    if resolved_timeframe != "all":
        read_model_result, fallback_reason = _get_player_period_stats_read_model(
            player_id=normalized_player_id,
            server_id=server_id,
            timeframe=resolved_timeframe,
            db_path=db_path,
        )
        if read_model_result is not None:
            return read_model_result

        runtime_result = _get_rcon_materialized_player_stats_runtime(
            player_id=normalized_player_id,
            server_id=server_id,
            timeframe=resolved_timeframe,
            db_path=db_path,
        )
        runtime_result.setdefault("source", {})
        runtime_result["source"]["fallback_used"] = True
        runtime_result["source"]["fallback_reason"] = fallback_reason or "player-period-stats-unavailable"
        runtime_result["source"]["read_model"] = "player-period-stats"
        runtime_result["source"]["freshness"] = "runtime-fallback"
        return runtime_result

    return _get_rcon_materialized_player_stats_runtime(
        player_id=normalized_player_id,
        server_id=server_id,
        timeframe=resolved_timeframe,
        db_path=db_path,
    )


def _get_rcon_materialized_player_stats_runtime(
    *,
    player_id: str,
    server_id: str | None = None,
    timeframe: str = "weekly",
    db_path: Path | None = None,
) -> dict[str, object]:
    """Return runtime player stats directly from materialized matches and player rows."""
    normalized_player_id = player_id.strip()
    resolved_timeframe = timeframe.strip().lower() if isinstance(timeframe, str) else "weekly"

    resolved_path = initialize_rcon_materialized_storage(db_path=db_path)
    resolved_server_id = _normalize_server_id(server_id)
    now = datetime.now(timezone.utc)

    with _connect_scope(resolved_path, db_path=db_path) as connection:
        selected_window = _build_player_timeframe_window(
            connection=connection,
            server_id=resolved_server_id,
            timeframe=resolved_timeframe,
            now=now,
        )

        player_stats = _fetch_player_stats(
            connection=connection,
            player_id=normalized_player_id,
            server_id=resolved_server_id,
            window=selected_window if resolved_timeframe != "all" else None,
        )
        active_time = _fetch_player_active_time_summary(
            connection=connection,
            player_id=normalized_player_id,
            server_id=resolved_server_id,
            window=selected_window if resolved_timeframe != "all" else None,
            total_matches_considered=int(player_stats.get("matches_considered", 0) or 0),
        )

        source_range = _fetch_source_range(
            connection=connection,
            server_id=resolved_server_id,
            window=selected_window if resolved_timeframe != "all" else None,
        )

        weekly_window = select_leaderboard_window(
            connection=connection,
            server_key=resolved_server_id,
            timeframe="weekly",
            now=now,
        )
        monthly_window = select_leaderboard_window(
            connection=connection,
            server_key=resolved_server_id,
            timeframe="monthly",
            now=now,
        )

        weekly_ranking = _fetch_player_ranking(
            connection=connection,
            player_id=normalized_player_id,
            server_id=resolved_server_id,
            window=weekly_window,
        )
        monthly_ranking = _fetch_player_ranking(
            connection=connection,
            player_id=normalized_player_id,
            server_id=resolved_server_id,
            window=monthly_window,
        )

    return {
        "player_id": normalized_player_id,
        "server_id": resolved_server_id,
        "timeframe": resolved_timeframe,
        "player_name": player_stats.get("player_name"),
        "window_start": selected_window["start"] if selected_window else None,
        "window_end": selected_window["end"] if selected_window else None,
        "window_kind": selected_window["kind"] if selected_window else "all-time",
        "matches_considered": player_stats.get("matches_considered", 0),
        "kills": player_stats.get("kills", 0),
        "deaths": player_stats.get("deaths", 0),
        "teamkills": player_stats.get("teamkills", 0),
        **active_time,
        **build_external_player_profile_fields(player_id=normalized_player_id),
        "weekly_ranking": weekly_ranking,
        "monthly_ranking": monthly_ranking,
        "source": {
            "primary_source": "rcon",
            "generated_at": _to_iso(now),
            "source_range_start": _to_iso(source_range[0]) if source_range[0] else None,
            "source_range_end": _to_iso(source_range[1]) if source_range[1] else None,
            "freshness": "runtime",
        },
    }


def _get_player_period_stats_read_model(
    *,
    player_id: str,
    server_id: str | None,
    timeframe: str,
    db_path: Path | None = None,
) -> tuple[dict[str, object] | None, str | None]:
    resolved_path = _resolve_rcon_read_model_path(db_path=db_path)
    resolved_server_id = _normalize_server_id(server_id)
    required_periods = sorted({timeframe, "weekly", "monthly"})
    placeholders = ", ".join(["?"] * len(required_periods))

    try:
        with _connect_read_scope(resolved_path, db_path=db_path) as connection:
            scope_rows = connection.execute(
                f"""
                SELECT period_type, COUNT(*) AS row_count
                FROM player_period_stats
                WHERE server_id = ?
                  AND period_type IN ({placeholders})
                GROUP BY period_type
                """,
                [resolved_server_id, *required_periods],
            ).fetchall()
            counts_by_period = {
                str(row["period_type"] or "").strip(): int(row["row_count"] or 0)
                for row in scope_rows
            }
            if not counts_by_period:
                return None, "player-period-stats-empty"
            if any(counts_by_period.get(period_type, 0) <= 0 for period_type in required_periods):
                return None, "player-period-stats-empty"

            rows = connection.execute(
                f"""
                SELECT *
                FROM player_period_stats
                WHERE server_id = ?
                  AND player_id = ?
                  AND period_type IN ({placeholders})
                """,
                [resolved_server_id, player_id, *required_periods],
            ).fetchall()
    except Exception:
        return None, "player-period-stats-unavailable"

    rows_by_period = {
        str(row["period_type"] or "").strip(): dict(row)
        for row in rows
    }
    if any(period_type not in rows_by_period for period_type in required_periods):
        return None, "player-period-stats-player-missing"

    selected_row = rows_by_period[timeframe]
    weekly_row = rows_by_period["weekly"]
    monthly_row = rows_by_period["monthly"]
    with _connect_read_scope(resolved_path, db_path=db_path) as connection:
        active_time = _fetch_player_active_time_summary(
            connection=connection,
            player_id=player_id,
            server_id=resolved_server_id,
            window={
                "start": _to_datetime_or_none(selected_row.get("period_start")),
                "end": _to_datetime_or_none(selected_row.get("period_end")),
            },
            total_matches_considered=int(selected_row.get("matches_considered") or 0),
        )
    return (
        {
            "player_id": player_id,
            "server_id": resolved_server_id,
            "timeframe": timeframe,
            "player_name": selected_row.get("player_name"),
            "window_start": _to_datetime_or_none(selected_row.get("period_start")),
            "window_end": _to_datetime_or_none(selected_row.get("period_end")),
            "window_kind": selected_row.get("window_kind"),
            "matches_considered": int(selected_row.get("matches_considered") or 0),
            "kills": int(selected_row.get("kills") or 0),
            "deaths": int(selected_row.get("deaths") or 0),
            "teamkills": int(selected_row.get("teamkills") or 0),
            **active_time,
            **build_external_player_profile_fields(player_id=player_id),
            "weekly_ranking": _build_player_period_ranking_payload(weekly_row),
            "monthly_ranking": _build_player_period_ranking_payload(monthly_row),
            "source": {
                "primary_source": "rcon",
                "read_model": "player-period-stats",
                "fallback_used": False,
                "fallback_reason": None,
                "generated_at": selected_row.get("updated_at"),
                "source_range_start": selected_row.get("first_seen_at"),
                "source_range_end": selected_row.get("last_seen_at"),
                "freshness": "read-model",
            },
        },
        None,
    )


def _build_player_period_ranking_payload(row: dict[str, object]) -> dict[str, object]:
    ranking_position = row.get("ranking_position")
    return {
        "metric": "kills",
        "ranking_position": int(ranking_position) if ranking_position is not None else None,
        "window_kind": row.get("window_kind"),
        "window_start": row.get("period_start"),
        "window_end": row.get("period_end"),
    }


def _select_player_period_window(
    *,
    connection: object,
    server_id: str,
    period_type: str,
    now: datetime,
) -> dict[str, object]:
    if period_type == "yearly":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return {
            "start": start,
            "end": now,
            "kind": "current-year",
            "label": "Ano actual",
        }
    return select_leaderboard_window(
        connection=connection,
        server_key=server_id,
        timeframe=period_type,
        now=now,
    )


def _build_player_period_stats_rows(
    *,
    connection: object,
    server_id: str,
    period_type: str,
    window: dict[str, object],
) -> list[dict[str, object]]:
    scope_sql, scope_params = _build_scope_sql(server_id)
    rows = connection.execute(
        f"""
        SELECT
            stats.player_id,
            MIN(COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT))) AS first_seen_at,
            MAX(COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT))) AS last_seen_at,
            COUNT(DISTINCT stats.match_key) AS matches_considered,
            SUM(COALESCE(stats.kills, 0)) AS kills,
            SUM(COALESCE(stats.deaths, 0)) AS deaths,
            SUM(COALESCE(stats.teamkills, 0)) AS teamkills
        FROM rcon_match_player_stats AS stats
        INNER JOIN rcon_materialized_matches AS matches
            ON matches.target_key = stats.target_key
           AND matches.match_key = stats.match_key
        WHERE matches.source_basis = ?
          AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) >= ?
          AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) <= ?
          {scope_sql}
        GROUP BY stats.player_id
        HAVING COUNT(DISTINCT stats.match_key) > 0
        """,
        [
            MATCH_RESULT_SOURCE,
            _to_iso(window["start"]),
            _to_iso(window["end"]),
            *scope_params,
        ],
    ).fetchall()
    if not rows:
        return []

    player_ids = [
        str(row["player_id"]).strip()
        for row in rows
        if str(row["player_id"] or "").strip()
    ]
    latest_names = _lookup_latest_player_names_with_connection(
        connection=connection,
        player_ids=player_ids,
        server_id=server_id,
        start=window["start"],
        end=window["end"],
    )

    period_rows: list[dict[str, object]] = []
    for row in rows:
        player_id = str(row["player_id"] or "").strip()
        if not player_id:
            continue
        matches_considered = int(row["matches_considered"] or 0)
        kills = int(row["kills"] or 0)
        deaths = int(row["deaths"] or 0)
        teamkills = int(row["teamkills"] or 0)
        player_name = latest_names.get(player_id) or player_id
        period_rows.append(
            {
                "period_type": period_type,
                "window_kind": str(window["kind"]),
                "period_start": _to_iso(window["start"]),
                "period_end": _to_iso(window["end"]),
                "server_id": server_id,
                "player_id": player_id,
                "player_name": player_name,
                "matches_considered": matches_considered,
                "kills": kills,
                "deaths": deaths,
                "teamkills": teamkills,
                "kd_ratio": round(kills / deaths, 2) if deaths else float(kills),
                "kills_per_match": round(kills / matches_considered, 2) if matches_considered else 0.0,
                "first_seen_at": row["first_seen_at"],
                "last_seen_at": row["last_seen_at"],
            }
        )

    period_rows.sort(
        key=lambda item: (
            -int(item["kills"]),
            -int(item["matches_considered"]),
            str(item["player_name"]).casefold(),
        )
    )
    for position, row in enumerate(period_rows, start=1):
        row["ranking_position"] = position
    return period_rows


def _replace_player_period_stats_scope(
    *,
    connection: object,
    server_id: str,
    period_type: str,
    rows: list[dict[str, object]],
    updated_at: str,
) -> None:
    connection.execute(
        """
        DELETE FROM player_period_stats
        WHERE server_id = ? AND period_type = ?
        """,
        [server_id, period_type],
    )
    for row in rows:
        connection.execute(
            """
            INSERT INTO player_period_stats (
                period_type,
                window_kind,
                period_start,
                period_end,
                server_id,
                player_id,
                player_name,
                matches_considered,
                kills,
                deaths,
                teamkills,
                ranking_position,
                kd_ratio,
                kills_per_match,
                first_seen_at,
                last_seen_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row["period_type"],
                row["window_kind"],
                row["period_start"],
                row["period_end"],
                row["server_id"],
                row["player_id"],
                row["player_name"],
                row["matches_considered"],
                row["kills"],
                row["deaths"],
                row["teamkills"],
                row["ranking_position"],
                row["kd_ratio"],
                row["kills_per_match"],
                row["first_seen_at"],
                row["last_seen_at"],
                updated_at,
            ],
        )


def _build_player_timeframe_window(
    *,
    connection: object,
    server_id: str | None,
    timeframe: str,
    now: datetime,
) -> dict[str, object] | None:
    if timeframe == "all":
        return None
    window = select_leaderboard_window(
        connection=connection,
        server_key=server_id,
        timeframe=timeframe,
        now=now,
    )
    return {
        "start": window["start"],
        "end": window["end"],
        "kind": window["kind"],
    }


def _fetch_player_stats(
    *,
    connection: object,
    player_id: str,
    server_id: str | None,
    window: dict[str, object] | None,
) -> dict[str, object]:
    scope_sql, scope_params = _build_scope_sql(server_id)
    base_where = [
        "matches.source_basis = ?",
        "stats.player_id = ?",
    ]
    params: list[object] = [MATCH_RESULT_SOURCE, player_id]
    if window is not None:
        base_where.append(
            "COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) >= ?"
        )
        base_where.append(
            "COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) <= ?"
        )
        params.extend([_to_iso(window["start"]), _to_iso(window["end"])])
    # Scope filter is applied directly in SQL via ``scope_sql`` placeholders.
    where_sql = " AND ".join(base_where)
    row = connection.execute(
        f"""
        SELECT
            MAX(stats.player_name) AS player_name,
            COUNT(DISTINCT stats.match_key) AS matches_considered,
            SUM(COALESCE(stats.kills, 0)) AS kills,
            SUM(COALESCE(stats.deaths, 0)) AS deaths,
            SUM(COALESCE(stats.teamkills, 0)) AS teamkills
        FROM rcon_match_player_stats AS stats
        INNER JOIN rcon_materialized_matches AS matches
            ON matches.target_key = stats.target_key
           AND matches.match_key = stats.match_key
        WHERE {where_sql} {scope_sql}
        """,
        [*params, *scope_params],
    ).fetchone()
    if not row:
        return {
            "player_name": None,
            "matches_considered": 0,
            "kills": 0,
            "deaths": 0,
            "teamkills": 0,
        }

    return {
        "player_name": str(row["player_name"] or player_id),
        "matches_considered": int(row["matches_considered"] or 0),
        "kills": int(row["kills"] or 0),
        "deaths": int(row["deaths"] or 0),
        "teamkills": int(row["teamkills"] or 0),
    }


def _fetch_player_active_time_summary(
    *,
    connection: object,
    player_id: str,
    server_id: str | None,
    window: dict[str, object] | None,
    total_matches_considered: int,
) -> dict[str, object]:
    scope_sql, scope_params = _build_scope_sql(server_id)
    min_active_seconds = get_kpm_min_active_seconds()
    base_where = [
        "matches.source_basis = ?",
        "stats.player_id = ?",
    ]
    params: list[object] = [MATCH_RESULT_SOURCE, player_id]
    if window is not None:
        base_where.append(
            "COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) >= ?"
        )
        base_where.append(
            "COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) <= ?"
        )
        params.extend([_to_iso(window["start"]), _to_iso(window["end"])])
    where_sql = " AND ".join(base_where)
    eligible_sources_placeholders = ", ".join(["?"] * len(REAL_KPM_ACTIVE_TIME_SOURCES))
    row = connection.execute(
        f"""
        SELECT
            COUNT(DISTINCT CASE
                WHEN stats.player_active_seconds IS NOT NULL
                THEN stats.match_key
                ELSE NULL
            END) AS observed_matches,
            COUNT(DISTINCT CASE
                WHEN stats.active_time_source IN ({eligible_sources_placeholders})
                THEN stats.match_key
                ELSE NULL
            END) AS real_source_matches,
            COUNT(DISTINCT CASE
                WHEN stats.active_time_source IN ({eligible_sources_placeholders})
                 AND COALESCE(stats.player_active_seconds, 0) >= ?
                THEN stats.match_key
                ELSE NULL
            END) AS eligible_matches,
            SUM(CASE
                WHEN stats.active_time_source IN ({eligible_sources_placeholders})
                 AND COALESCE(stats.player_active_seconds, 0) >= ?
                THEN COALESCE(stats.player_active_seconds, 0)
                ELSE 0
            END) AS player_active_seconds,
            SUM(CASE
                WHEN stats.active_time_source IN ({eligible_sources_placeholders})
                 AND COALESCE(stats.player_active_seconds, 0) >= ?
                THEN COALESCE(stats.kills, 0)
                ELSE 0
            END) AS eligible_kills,
            GROUP_CONCAT(DISTINCT CASE
                WHEN stats.active_time_source IN ({eligible_sources_placeholders})
                THEN stats.active_time_source
                ELSE NULL
            END) AS eligible_sources,
            GROUP_CONCAT(DISTINCT COALESCE(stats.active_time_source, 'unavailable')) AS observed_sources
        FROM rcon_match_player_stats AS stats
        INNER JOIN rcon_materialized_matches AS matches
            ON matches.target_key = stats.target_key
           AND matches.match_key = stats.match_key
        WHERE {where_sql} {scope_sql}
        """,
        [
            *REAL_KPM_ACTIVE_TIME_SOURCES,
            *REAL_KPM_ACTIVE_TIME_SOURCES,
            min_active_seconds,
            *REAL_KPM_ACTIVE_TIME_SOURCES,
            min_active_seconds,
            *REAL_KPM_ACTIVE_TIME_SOURCES,
            min_active_seconds,
            *REAL_KPM_ACTIVE_TIME_SOURCES,
            *params,
            *scope_params,
        ],
    ).fetchone()
    return _build_profile_active_time_payload(
        row=dict(row) if row is not None else {},
        total_matches_considered=total_matches_considered,
        min_active_seconds=min_active_seconds,
    )


def _build_profile_active_time_payload(
    *,
    row: dict[str, object],
    total_matches_considered: int,
    min_active_seconds: int,
) -> dict[str, object]:
    observed_matches = int(row.get("observed_matches") or 0)
    real_source_matches = int(row.get("real_source_matches") or 0)
    eligible_matches = int(row.get("eligible_matches") or 0)
    player_active_seconds = int(row.get("player_active_seconds") or 0)
    eligible_kills = int(row.get("eligible_kills") or 0)
    eligible_sources = _split_sources(row.get("eligible_sources"))
    observed_sources = _split_sources(row.get("observed_sources"))

    if eligible_matches > 0 and player_active_seconds >= min_active_seconds:
        player_active_minutes = round(player_active_seconds / 60, 3)
        return {
            "player_active_seconds": player_active_seconds,
            "player_active_minutes": player_active_minutes,
            "kpm": round(eligible_kills / (player_active_seconds / 60), 2),
            "kpm_status": "ready",
            "active_time_source": _summarize_real_active_time_sources(eligible_sources),
            "active_time_coverage": {
                "eligible_matches": eligible_matches,
                "real_source_matches": real_source_matches,
                "observed_matches": observed_matches,
                "total_matches_considered": total_matches_considered,
                "eligible_kills": eligible_kills,
                "minimum_active_seconds": min_active_seconds,
                "sources": eligible_sources,
            },
        }

    if real_source_matches > 0:
        return {
            "player_active_seconds": None,
            "player_active_minutes": None,
            "kpm": None,
            "kpm_status": "insufficient_active_time",
            "active_time_source": _summarize_real_active_time_sources(eligible_sources or observed_sources),
            "active_time_coverage": {
                "eligible_matches": eligible_matches,
                "real_source_matches": real_source_matches,
                "observed_matches": observed_matches,
                "total_matches_considered": total_matches_considered,
                "eligible_kills": eligible_kills,
                "minimum_active_seconds": min_active_seconds,
                "sources": observed_sources,
            },
        }

    if observed_matches > 0 or "event_span_fallback" in observed_sources:
        return {
            "player_active_seconds": None,
            "player_active_minutes": None,
            "kpm": None,
            "kpm_status": "missing_connection_intervals",
            "active_time_source": "event_span_fallback" if observed_sources else "unavailable",
            "active_time_coverage": {
                "eligible_matches": 0,
                "real_source_matches": real_source_matches,
                "observed_matches": observed_matches,
                "total_matches_considered": total_matches_considered,
                "eligible_kills": 0,
                "minimum_active_seconds": min_active_seconds,
                "sources": observed_sources,
            },
        }

    return {
        "player_active_seconds": None,
        "player_active_minutes": None,
        "kpm": None,
        "kpm_status": "missing_active_time",
        "active_time_source": "unavailable",
        "active_time_coverage": {
            "eligible_matches": 0,
            "real_source_matches": 0,
            "observed_matches": 0,
            "total_matches_considered": total_matches_considered,
            "eligible_kills": 0,
            "minimum_active_seconds": min_active_seconds,
            "sources": [],
        },
    }


def _split_sources(value: object) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []
    return [item for item in {part.strip() for part in value.split(",")} if item]


def _summarize_real_active_time_sources(sources: list[str]) -> str:
    normalized = [source for source in sources if source in REAL_KPM_ACTIVE_TIME_SOURCES]
    if not normalized:
        return "unavailable"
    if len(normalized) == 1:
        return normalized[0]
    return "connection_intervals_mixed"


def _fetch_player_ranking(
    *,
    connection: object,
    player_id: str,
    server_id: str | None,
    window: dict[str, object],
) -> dict[str, object]:
    scope_sql, scope_params = _build_scope_sql(server_id)
    row = connection.execute(
        f"""
        SELECT ranking_position
        FROM (
            SELECT
                ranked.player_id,
                ROW_NUMBER() OVER (
                    ORDER BY ranked.kills DESC, ranked.matches_considered DESC, ranked.player_name ASC
                ) AS ranking_position
            FROM (
                SELECT
                    stats.player_id,
                    COALESCE(MAX(stats.player_name), '') AS player_name,
                    SUM(COALESCE(stats.kills, 0)) AS kills,
                    COUNT(DISTINCT stats.match_key) AS matches_considered
                FROM rcon_match_player_stats AS stats
                INNER JOIN rcon_materialized_matches AS matches
                    ON matches.target_key = stats.target_key
                   AND matches.match_key = stats.match_key
                WHERE matches.source_basis = ?
                  AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) >= ?
                  AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) <= ?
                  {scope_sql}
                GROUP BY stats.player_id
            ) AS ranked
            WHERE ranked.kills > 0
        ) AS ranking
        WHERE ranking.player_id = ?
        """,
        [
            MATCH_RESULT_SOURCE,
            _to_iso(window["start"]),
            _to_iso(window["end"]),
            *scope_params,
            player_id,
        ],
    ).fetchone()

    ranking_position: int | None = None
    if row and row["ranking_position"] is not None:
        ranking_position = int(row["ranking_position"])

    return {
        "metric": "kills",
        "ranking_position": ranking_position,
        "window_kind": window["kind"],
        "window_start": _to_iso(window["start"]),
        "window_end": _to_iso(window["end"]),
    }


def _fetch_source_range(
    *,
    connection: object,
    server_id: str | None,
    window: dict[str, object] | None,
) -> tuple[datetime | None, datetime | None]:
    scope_sql, scope_params = _build_scope_sql(server_id, table_alias="matches")
    if window is None:
        row = connection.execute(
            f"""
            SELECT
                MIN(COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT))) AS source_range_start,
                MAX(COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT))) AS source_range_end
            FROM rcon_materialized_matches AS matches
            WHERE matches.source_basis = ?
              {scope_sql}
            """,
            [MATCH_RESULT_SOURCE, *scope_params],
        ).fetchone()
    else:
        row = connection.execute(
            f"""
            SELECT
                MIN(COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT))) AS source_range_start,
                MAX(COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT))) AS source_range_end
            FROM rcon_materialized_matches AS matches
            WHERE matches.source_basis = ?
              AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) >= ?
              AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) <= ?
              {scope_sql}
            """,
            [MATCH_RESULT_SOURCE, _to_iso(window["start"]), _to_iso(window["end"]), *scope_params],
        ).fetchone()
    if not row:
        return None, None
    return _to_datetime_or_none(row["source_range_start"]), _to_datetime_or_none(row["source_range_end"])


def _to_datetime_or_none(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _build_player_search_index_rows(
    *,
    connection: object,
    server_id: str,
    year_start: datetime,
    next_year_start: datetime,
) -> list[dict[str, object]]:
    scope_sql, scope_params = _build_scope_sql(server_id)
    rows = connection.execute(
        f"""
        SELECT
            stats.player_id,
            MIN(COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT))) AS first_seen_at,
            MAX(COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT))) AS last_seen_at,
            COUNT(DISTINCT stats.match_key) AS matches_current_year,
            SUM(COALESCE(stats.kills, 0)) AS kills_current_year,
            SUM(COALESCE(stats.deaths, 0)) AS deaths_current_year,
            SUM(COALESCE(stats.teamkills, 0)) AS teamkills_current_year
        FROM rcon_match_player_stats AS stats
        INNER JOIN rcon_materialized_matches AS matches
            ON matches.target_key = stats.target_key
           AND matches.match_key = stats.match_key
        WHERE matches.source_basis = ?
          AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) >= ?
          AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) < ?
          {scope_sql}
        GROUP BY stats.player_id
        HAVING COUNT(DISTINCT stats.match_key) > 0
        ORDER BY MAX(COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT))) DESC,
                 COUNT(DISTINCT stats.match_key) DESC,
                 stats.player_id ASC
        """,
        [MATCH_RESULT_SOURCE, _to_iso(year_start), _to_iso(next_year_start), *scope_params],
    ).fetchall()
    if not rows:
        return []

    player_ids = [
        str(row["player_id"]).strip()
        for row in rows
        if str(row["player_id"] or "").strip()
    ]
    latest_names = _lookup_latest_player_names_with_connection(
        connection=connection,
        player_ids=player_ids,
        server_id=server_id,
        start=year_start,
        end=next_year_start,
    )
    servers_seen = _lookup_servers_seen_with_connection(
        connection=connection,
        player_ids=player_ids,
        server_id=server_id,
        start=year_start,
        end=next_year_start,
    )

    index_rows: list[dict[str, object]] = []
    for row in rows:
        player_id = str(row["player_id"] or "").strip()
        if not player_id:
            continue
        player_name = latest_names.get(player_id) or player_id
        normalized_player_name = _normalize_player_search_text(player_name) or player_id.casefold()
        index_rows.append(
            {
                "player_id": player_id,
                "player_name": player_name,
                "normalized_player_name": normalized_player_name,
                "first_seen_at": row["first_seen_at"],
                "last_seen_at": row["last_seen_at"],
                "servers_seen": servers_seen.get(player_id, []),
                "matches_current_year": int(row["matches_current_year"] or 0),
                "kills_current_year": int(row["kills_current_year"] or 0),
                "deaths_current_year": int(row["deaths_current_year"] or 0),
                "teamkills_current_year": int(row["teamkills_current_year"] or 0),
            }
        )
    return index_rows


def _replace_player_search_index_scope(
    *,
    connection: object,
    server_id: str,
    rows: list[dict[str, object]],
    updated_at: str,
) -> None:
    connection.execute(
        """
        DELETE FROM player_search_index
        WHERE server_id = ?
        """,
        [server_id],
    )
    for row in rows:
        connection.execute(
            """
            INSERT INTO player_search_index (
                server_id,
                player_id,
                player_name,
                normalized_player_name,
                first_seen_at,
                last_seen_at,
                servers_seen,
                matches_current_year,
                kills_current_year,
                deaths_current_year,
                teamkills_current_year,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                server_id,
                row["player_id"],
                row["player_name"],
                row["normalized_player_name"],
                row["first_seen_at"],
                row["last_seen_at"],
                json.dumps(row["servers_seen"], ensure_ascii=True, separators=(",", ":")),
                row["matches_current_year"],
                row["kills_current_year"],
                row["deaths_current_year"],
                row["teamkills_current_year"],
                updated_at,
            ],
        )


def _search_player_search_index(
    *,
    query: str,
    server_id: str | None = None,
    limit: int = 10,
    db_path: Path | None = None,
) -> tuple[dict[str, object] | None, str | None]:
    resolved_path = _resolve_rcon_read_model_path(db_path=db_path)
    resolved_server_id = _normalize_server_id(server_id)
    normalized_query = query.strip()
    normalized_name_query = _normalize_player_search_text(normalized_query)
    anchor = datetime.now(timezone.utc)
    year_start = anchor.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    escaped_name_contains = f"%{_escape_like_pattern(normalized_name_query)}%"
    escaped_name_prefix = f"{_escape_like_pattern(normalized_name_query)}%"
    escaped_id_contains = f"%{_escape_like_pattern(normalized_query.casefold())}%"
    escaped_id_exact = normalized_query.casefold()

    try:
        with _connect_read_scope(resolved_path, db_path=db_path) as connection:
            has_rows = connection.execute(
                """
                SELECT 1
                FROM player_search_index
                WHERE server_id = ?
                LIMIT 1
                """,
                [resolved_server_id],
            ).fetchone()
            if has_rows is None:
                return None, "player-search-index-empty"

            rows = connection.execute(
                """
                SELECT
                    player_id,
                    player_name,
                    first_seen_at,
                    last_seen_at,
                    servers_seen,
                    matches_current_year,
                    kills_current_year,
                    deaths_current_year,
                    teamkills_current_year,
                    updated_at
                FROM player_search_index
                WHERE server_id = ?
                  AND (
                      normalized_player_name LIKE ? ESCAPE '\\'
                      OR LOWER(player_id) LIKE LOWER(?)
                  )
                ORDER BY
                    CASE
                        WHEN LOWER(player_id) = LOWER(?) THEN 0
                        WHEN normalized_player_name = ? THEN 1
                        WHEN normalized_player_name LIKE ? ESCAPE '\\' THEN 2
                        WHEN normalized_player_name LIKE ? ESCAPE '\\' THEN 3
                        ELSE 4
                    END,
                    matches_current_year DESC,
                    last_seen_at DESC,
                    player_name ASC
                LIMIT ?
                """,
                [
                    resolved_server_id,
                    escaped_name_contains,
                    escaped_id_contains,
                    escaped_id_exact,
                    normalized_name_query,
                    escaped_name_prefix,
                    escaped_name_contains,
                    limit,
                ],
            ).fetchall()
    except Exception:
        return None, "player-search-index-unavailable"

    items: list[dict[str, object]] = []
    generated_at = None
    for row in rows:
        if generated_at is None:
            generated_at = row["updated_at"]
        items.append(
            {
                "player_id": str(row["player_id"] or "").strip(),
                "player_name": str(row["player_name"] or row["player_id"] or "").strip(),
                "matches_considered": int(row["matches_current_year"] or 0),
                "last_seen_at": row["last_seen_at"],
                "servers_seen": _deserialize_string_list(row["servers_seen"]),
            }
        )

    return (
        {
            "server_id": resolved_server_id,
            "query": normalized_query,
            "items": items,
            "source": {
                "read_model": "player-search-index",
                "fallback_used": False,
                "fallback_reason": None,
                "generated_at": generated_at,
                "window_start": _to_iso(year_start),
                "window_end": _to_iso(anchor),
            },
        },
        None,
    )


def _lookup_latest_player_names(
    *,
    db_path: Path,
    player_ids: list[str],
    server_id: str | None,
    pattern_like: str,
) -> dict[str, str]:
    placeholders = ", ".join(["?"] * len(player_ids))
    scope_sql, scope_params = _build_scope_sql(server_id)
    with _connect_scope(db_path, db_path=db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT
                stats.player_id,
                stats.player_name,
                COALESCE(matches.ended_at, matches.started_at) AS last_seen_at
            FROM rcon_match_player_stats AS stats
            INNER JOIN rcon_materialized_matches AS matches
                ON matches.target_key = stats.target_key
               AND matches.match_key = stats.match_key
            WHERE stats.player_id IN ({placeholders})
              AND matches.source_basis = ?
              AND (
                  LOWER(COALESCE(stats.player_name, '')) LIKE LOWER(?) ESCAPE '\\'
                  OR LOWER(stats.player_id) LIKE LOWER(?)
              )
              {scope_sql}
            ORDER BY COALESCE(matches.ended_at, matches.started_at) DESC
            """,
            [*player_ids, MATCH_RESULT_SOURCE, pattern_like, pattern_like, *scope_params],
        ).fetchall()

    latest_names: dict[str, str] = {}
    for row in rows:
        player_id = str(row["player_id"] or "").strip()
        if player_id and player_id not in latest_names:
            latest_names[player_id] = str(row["player_name"] or player_id)
    return latest_names


def _lookup_latest_player_names_with_connection(
    *,
    connection: object,
    player_ids: list[str],
    server_id: str | None,
    start: datetime,
    end: datetime,
) -> dict[str, str]:
    if not player_ids:
        return {}
    placeholders = ", ".join(["?"] * len(player_ids))
    scope_sql, scope_params = _build_scope_sql(server_id)
    rows = connection.execute(
        f"""
        SELECT
            stats.player_id,
            stats.player_name,
            COALESCE(matches.ended_at, matches.started_at) AS last_seen_at
        FROM rcon_match_player_stats AS stats
        INNER JOIN rcon_materialized_matches AS matches
            ON matches.target_key = stats.target_key
           AND matches.match_key = stats.match_key
        WHERE stats.player_id IN ({placeholders})
          AND matches.source_basis = ?
          AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) >= ?
          AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) < ?
          {scope_sql}
        ORDER BY COALESCE(matches.ended_at, matches.started_at) DESC, stats.player_name ASC
        """,
        [*player_ids, MATCH_RESULT_SOURCE, _to_iso(start), _to_iso(end), *scope_params],
    ).fetchall()
    latest_names: dict[str, str] = {}
    for row in rows:
        player_id = str(row["player_id"] or "").strip()
        if player_id and player_id not in latest_names:
            latest_names[player_id] = str(row["player_name"] or player_id)
    return latest_names


def _lookup_servers_seen(
    *,
    db_path: Path,
    player_ids: list[str],
    server_id: str | None,
) -> dict[str, list[str]]:
    placeholders = ", ".join(["?"] * len(player_ids))
    scope_sql, scope_params = _build_scope_sql(server_id)
    with _connect_scope(db_path, db_path=db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT
                stats.player_id,
                COALESCE(matches.external_server_id, matches.target_key) AS server_id
            FROM rcon_match_player_stats AS stats
            INNER JOIN rcon_materialized_matches AS matches
                ON matches.target_key = stats.target_key
               AND matches.match_key = stats.match_key
            WHERE stats.player_id IN ({placeholders})
              AND matches.source_basis = ?
              {scope_sql}
            GROUP BY stats.player_id, COALESCE(matches.external_server_id, matches.target_key)
            ORDER BY stats.player_id, server_id ASC
            """,
            [*player_ids, MATCH_RESULT_SOURCE, *scope_params],
        ).fetchall()

    by_player: dict[str, list[str]] = {}
    for row in rows:
        player_id = str(row["player_id"] or "").strip()
        if not player_id:
            continue
        by_player.setdefault(player_id, [])
        server_name = str(row["server_id"] or "").strip()
        if server_name and server_name not in by_player[player_id]:
            by_player[player_id].append(server_name)
    return by_player


def _lookup_servers_seen_with_connection(
    *,
    connection: object,
    player_ids: list[str],
    server_id: str | None,
    start: datetime,
    end: datetime,
) -> dict[str, list[str]]:
    if not player_ids:
        return {}
    placeholders = ", ".join(["?"] * len(player_ids))
    scope_sql, scope_params = _build_scope_sql(server_id)
    rows = connection.execute(
        f"""
        SELECT
            stats.player_id,
            COALESCE(matches.external_server_id, matches.target_key) AS server_id
        FROM rcon_match_player_stats AS stats
        INNER JOIN rcon_materialized_matches AS matches
            ON matches.target_key = stats.target_key
           AND matches.match_key = stats.match_key
        WHERE stats.player_id IN ({placeholders})
          AND matches.source_basis = ?
          AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) >= ?
          AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) < ?
          {scope_sql}
        GROUP BY stats.player_id, COALESCE(matches.external_server_id, matches.target_key)
        ORDER BY stats.player_id, server_id ASC
        """,
        [*player_ids, MATCH_RESULT_SOURCE, _to_iso(start), _to_iso(end), *scope_params],
    ).fetchall()

    by_player: dict[str, list[str]] = {}
    for row in rows:
        player_id = str(row["player_id"] or "").strip()
        if not player_id:
            continue
        by_player.setdefault(player_id, [])
        candidate_server_id = str(row["server_id"] or "").strip()
        if candidate_server_id and candidate_server_id not in by_player[player_id]:
            by_player[player_id].append(candidate_server_id)
    return by_player


def _build_scope_sql(
    server_id: str | None,
    *,
    table_alias: str = "matches",
) -> tuple[str, list[object]]:
    if not server_id or server_id == ALL_SERVERS_SLUG:
        return "", []
    return (
        f"AND ({table_alias}.target_key = ? OR {table_alias}.external_server_id = ?)",
        [server_id, server_id],
    )


def _normalize_server_id(server_id: str | None) -> str:
    normalized = str(server_id or "").strip()
    if not normalized or normalized.lower() == "all":
        return ALL_SERVERS_SLUG
    return normalized


def _escape_like_pattern(raw_value: str) -> str:
    return (
        raw_value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
        .strip()
    )


def _normalize_player_row(row: object) -> dict[str, object]:
    if isinstance(row, dict):
        return dict(row)
    return {
        "player_id": row[0] if row else None,
        "matches_considered": row[1] if row else 0,
        "last_seen_at": row[2] if row else None,
        "player_name": None,
    }


def _connect_scope(resolved_path: Path, *, db_path: Path | None = None):
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import connect_postgres_compat

        return connect_postgres_compat()
    return closing(connect_sqlite_readonly(resolved_path))


def _connect_read_scope(resolved_path: Path, *, db_path: Path | None = None):
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import connect_postgres_compat

        return connect_postgres_compat(initialize=False)
    return closing(connect_sqlite_readonly(resolved_path))


def _connect_write_scope(resolved_path: Path, *, db_path: Path | None = None):
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import connect_postgres_compat

        return connect_postgres_compat()
    return connect_sqlite_writer(resolved_path)


def _resolve_rcon_read_model_path(*, db_path: Path | None = None) -> Path:
    return db_path or get_storage_path()


def _build_missing_player_period_stats_result(
    *,
    player_id: str,
    server_id: str | None,
    timeframe: str,
    missing_reason: str,
) -> dict[str, object]:
    resolved_server_id = _normalize_server_id(server_id)
    return {
        "player_id": player_id,
        "server_id": resolved_server_id,
        "timeframe": timeframe,
        "player_name": None,
        "window_start": None,
        "window_end": None,
        "window_kind": timeframe,
        "matches_considered": 0,
        "kills": 0,
        "deaths": 0,
        "teamkills": 0,
        "weekly_ranking": None,
        "monthly_ranking": None,
        "source": {
            "read_model": "player-period-stats",
            "status": "unavailable",
            "fallback_used": False,
            "fallback_reason": None,
            "missing_reason": missing_reason,
        },
    }


def _normalize_player_search_text(value: object) -> str:
    text = str(value or "").strip().casefold()
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(character for character in decomposed if not unicodedata.combining(character))
    compact = " ".join(without_accents.split())
    return compact


def _deserialize_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return _to_iso(value)
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Search and refresh player-search read models over materialized RCON stats.",
    )
    subparsers = parser.add_subparsers(dest="command")

    refresh_parser = subparsers.add_parser("refresh-player-search-index")
    refresh_parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=None,
        help="explicit local SQLite override; default operational mode uses PostgreSQL when configured",
    )
    refresh_period_stats_parser = subparsers.add_parser("refresh-player-period-stats")
    refresh_period_stats_parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=None,
        help="explicit local SQLite override; default operational mode uses PostgreSQL when configured",
    )

    args = parser.parse_args(argv)
    if args.command == "refresh-player-search-index":
        payload = refresh_player_search_index(db_path=args.sqlite_path)
        print(
            json.dumps(
                {"status": "ok", "data": payload},
                ensure_ascii=True,
                indent=2,
                default=_json_default,
            )
        )
        return 0
    if args.command == "refresh-player-period-stats":
        payload = refresh_player_period_stats(db_path=args.sqlite_path)
        print(
            json.dumps(
                {"status": "ok", "data": payload},
                ensure_ascii=True,
                indent=2,
                default=_json_default,
            )
        )
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
