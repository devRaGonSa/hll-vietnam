"""Search helpers for RCON materialized player statistics."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .config import use_postgres_rcon_storage
from .historical_storage import ALL_SERVERS_SLUG
from .rcon_admin_log_materialization import MATCH_RESULT_SOURCE, initialize_rcon_materialized_storage
from .rcon_historical_leaderboards import select_leaderboard_window
from .sqlite_utils import connect_sqlite_readonly
from .rcon_historical_leaderboards import _to_iso


def search_rcon_materialized_players(
    *,
    query: str,
    server_id: str | None = None,
    limit: int = 10,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Search players in materialized RCON/AdminLog statistics."""
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("Query cannot be empty.")

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
        "weekly_ranking": weekly_ranking,
        "monthly_ranking": monthly_ranking,
        "source": {
            "primary_source": "rcon",
            "read_model": "rcon-materialized-admin-log-player-stats",
            "generated_at": _to_iso(now),
            "source_range_start": _to_iso(source_range[0]) if source_range[0] else None,
            "source_range_end": _to_iso(source_range[1]) if source_range[1] else None,
            "freshness": "runtime",
        },
    }


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
            COALESCE(MAX(stats.player_name), stats.player_id) AS player_name,
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
