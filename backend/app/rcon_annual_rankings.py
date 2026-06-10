"""Annual ranking snapshot generator and reader over materialized RCON match stats."""

from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import closing
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

from .config import get_storage_path, use_postgres_rcon_storage
from .historical_storage import ALL_SERVERS_SLUG
from .rcon_admin_log_materialization import MATCH_RESULT_SOURCE, initialize_rcon_materialized_storage
from .sqlite_utils import connect_sqlite_readonly, connect_sqlite_writer


def generate_annual_ranking_snapshot(
    *,
    year: int,
    server_key: str | None = None,
    metric: str = "kills",
    limit: int = 20,
    replace_existing: bool = True,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Generate and persist an annual top-k ranking snapshot for materialized RCON data."""
    normalized_year = _normalize_year(year)
    normalized_server_key = _normalize_server_key(server_key)
    normalized_metric = _normalize_metric(metric)
    normalized_limit = _normalize_limit(limit)
    window_start, window_end = _annual_window(normalized_year)

    resolved_path = initialize_rcon_materialized_storage(db_path=db_path)
    scope_sql, scope_params = _build_scope_sql(normalized_server_key)
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import connect_postgres_compat

        connection_scope = connect_postgres_compat()
    else:
        connection_scope = connect_sqlite_writer(resolved_path)

    with connection_scope as connection:
        source_matches_count = _count_matches_in_window(
            connection=connection,
            start=window_start,
            end=window_end,
            scope_sql=scope_sql,
            scope_params=scope_params,
        )
        existing_snapshot_id = _find_existing_snapshot(
            connection=connection,
            year=normalized_year,
            server_key=normalized_server_key,
            metric=normalized_metric,
        )
        if existing_snapshot_id is not None and not replace_existing:
            snapshot = _get_snapshot(connection=connection, snapshot_id=existing_snapshot_id)
            items = _list_items(connection=connection, snapshot_id=existing_snapshot_id)
            return {
                "status": "ok",
                "snapshot": snapshot,
                "items": items,
                "source_matches_count": source_matches_count,
                "ranked_players": len(items),
                "skipped_regeneration": True,
            }

        ranking_rows = _fetch_annual_ranking_rows(
            connection=connection,
            start=window_start,
            end=window_end,
            metric=normalized_metric,
            limit=normalized_limit,
            scope_sql=scope_sql,
            scope_params=scope_params,
        )

        _delete_existing_snapshot(
            connection=connection,
            year=normalized_year,
            server_key=normalized_server_key,
            metric=normalized_metric,
        )
        snapshot_id = _insert_snapshot(
            connection=connection,
            year=normalized_year,
            server_key=normalized_server_key,
            metric=normalized_metric,
            limit=normalized_limit,
            source_matches_count=source_matches_count,
            window_start=window_start,
            window_end=window_end,
        )

        _insert_items(
            connection=connection,
            snapshot_id=snapshot_id,
            rows=ranking_rows,
            limit=normalized_limit,
        )

        snapshot = _get_snapshot(connection=connection, snapshot_id=snapshot_id)
        items = _list_items(connection=connection, snapshot_id=snapshot_id)

    return {
        "status": "ok",
        "snapshot": snapshot,
        "items": items,
        "source_matches_count": source_matches_count,
        "ranked_players": len(items),
    }


def get_annual_ranking_snapshot(
    *,
    year: int,
    server_key: str | None = None,
    metric: str = "kills",
    limit: int = 20,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Load one annual ranking snapshot without recalculating the ranking."""
    normalized_year = _normalize_year(year)
    normalized_server_key = _normalize_server_key(server_key)
    normalized_metric = _normalize_metric(metric)
    normalized_limit = _normalize_limit(limit)

    try:
        with _open_annual_snapshot_read_connection(db_path=db_path) as connection:
            snapshot = _find_snapshot(
                connection=connection,
                year=normalized_year,
                server_key=normalized_server_key,
                metric=normalized_metric,
            )
            if snapshot is None:
                return _build_missing_snapshot_result(
                    year=normalized_year,
                    server_key=normalized_server_key,
                    metric=normalized_metric,
                    limit=normalized_limit,
                )

            snapshot_limit = _normalize_limit(snapshot.get("limit_size") or normalized_limit)
            item_count = _count_items(
                connection=connection,
                snapshot_id=int(snapshot["id"]),
            )
            effective_limit = _resolve_effective_limit(
                requested_limit=normalized_limit,
                snapshot_limit=snapshot_limit,
                item_count=item_count,
            )
            items = _list_items(
                connection=connection,
                snapshot_id=int(snapshot["id"]),
                limit=effective_limit if effective_limit > 0 else None,
            )
    except (FileNotFoundError, sqlite3.OperationalError):
        return _build_missing_snapshot_result(
            year=normalized_year,
            server_key=normalized_server_key,
            metric=normalized_metric,
            limit=normalized_limit,
        )

    return {
        "snapshot_status": "ready",
        "year": normalized_year,
        "server_id": normalized_server_key,
        "metric": normalized_metric,
        "limit": effective_limit,
        "requested_limit": normalized_limit,
        "effective_limit": effective_limit,
        "snapshot_limit": snapshot_limit,
        "item_count": item_count,
        "source": "rcon-annual-ranking-snapshot",
        "generated_at": snapshot.get("generated_at"),
        "window_start": snapshot.get("window_start"),
        "window_end": snapshot.get("window_end"),
        "source_matches_count": int(snapshot.get("source_matches_count") or 0),
        "items": items,
    }


@contextmanager
def _open_annual_snapshot_read_connection(*, db_path: Path | None = None):
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import PostgresCompatConnection, connect_postgres

        with connect_postgres() as connection:
            yield PostgresCompatConnection(connection)
        return

    resolved_path = _resolve_annual_snapshot_sqlite_path(db_path=db_path)
    if not resolved_path.exists():
        raise FileNotFoundError(resolved_path)
    with closing(connect_sqlite_readonly(resolved_path)) as connection:
        yield connection


def _resolve_annual_snapshot_sqlite_path(*, db_path: Path | None = None) -> Path:
    return db_path if db_path is not None else get_storage_path()


def _build_missing_snapshot_result(
    *,
    year: int,
    server_key: str,
    metric: str,
    limit: int,
) -> dict[str, object]:
    return {
        "snapshot_status": "missing",
        "year": year,
        "server_id": server_key,
        "metric": metric,
        "limit": limit,
        "requested_limit": limit,
        "effective_limit": 0,
        "snapshot_limit": None,
        "item_count": 0,
        "source": "rcon-annual-ranking-snapshot",
        "generated_at": None,
        "window_start": None,
        "window_end": None,
        "source_matches_count": 0,
        "items": [],
    }


def _normalize_server_key(server_key: str | None) -> str:
    normalized = str(server_key or "").strip()
    normalized_lower = normalized.lower()
    if not normalized or normalized_lower in {ALL_SERVERS_SLUG, "all"}:
        return ALL_SERVERS_SLUG
    return normalized


def _normalize_metric(metric: str) -> str:
    normalized = str(metric or "kills").strip().lower()
    if normalized != "kills":
        raise ValueError(
            f"Metric '{normalized}' is not supported for annual ranking snapshots."
        )
    return normalized


def _normalize_year(year: int) -> int:
    normalized_year = int(year)
    if normalized_year < 1 or normalized_year > 9999:
        raise ValueError("year must be between 1 and 9999")
    return normalized_year


def _normalize_limit(limit: object, *, maximum: int = 100) -> int:
    normalized_limit = int(limit or 1)
    if normalized_limit < 1:
        raise ValueError("limit must be greater than zero")
    return min(normalized_limit, maximum)


def _resolve_effective_limit(
    *,
    requested_limit: int,
    snapshot_limit: int,
    item_count: int,
) -> int:
    return max(0, min(requested_limit, snapshot_limit, item_count))


def _annual_window(year: int) -> tuple[str, str]:
    start = datetime(year, 1, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    end = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    return start, end


def _fetch_annual_ranking_rows(
    *,
    connection: object,
    start: str,
    end: str,
    metric: str,
    limit: int,
    scope_sql: str,
    scope_params: list[object],
) -> list[dict[str, object]]:
    # For now metric support is intentionally narrowed to kills only.
    if metric != "kills":
        return []

    rows = connection.execute(
        f"""
        SELECT
            stats.player_id,
            COALESCE(MAX(stats.player_name), stats.player_id) AS player_name,
            SUM(COALESCE(stats.kills, 0)) AS kills,
            SUM(COALESCE(stats.deaths, 0)) AS deaths,
            SUM(COALESCE(stats.teamkills, 0)) AS teamkills,
            COUNT(DISTINCT stats.match_key) AS matches_considered,
            SUM(COALESCE(stats.kills, 0)) AS metric_value
        FROM rcon_match_player_stats AS stats
        INNER JOIN rcon_materialized_matches AS matches
            ON matches.target_key = stats.target_key
           AND matches.match_key = stats.match_key
        WHERE matches.source_basis = ?
          AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) >= ?
          AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) < ?
          {scope_sql}
          AND TRIM(COALESCE(stats.player_name, '')) != ''
        GROUP BY stats.player_id
        HAVING SUM(COALESCE(stats.kills, 0)) > 0
        ORDER BY metric_value DESC, matches_considered DESC, player_name ASC
        LIMIT ?
        """,
        [MATCH_RESULT_SOURCE, start, end, *scope_params, limit],
    ).fetchall()
    return [dict(row) for row in rows]


def _count_matches_in_window(
    *,
    connection: object,
    start: str,
    end: str,
    scope_sql: str,
    scope_params: list[object],
) -> int:
    row = connection.execute(
        f"""
        SELECT COUNT(*) AS source_matches_count
        FROM (
            SELECT matches.target_key, matches.match_key
            FROM rcon_materialized_matches AS matches
            WHERE matches.source_basis = ?
              AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) >= ?
              AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) < ?
              {scope_sql}
            GROUP BY matches.target_key, matches.match_key
        ) AS source_matches
        """,
        [MATCH_RESULT_SOURCE, start, end, *scope_params],
    ).fetchone()
    return int(row["source_matches_count"] or 0) if row else 0


def _find_snapshot(
    *,
    connection: object,
    year: int,
    server_key: str,
    metric: str,
) -> dict[str, object] | None:
    row = connection.execute(
        """
        SELECT
            id,
            year,
            server_key,
            metric,
            limit_size,
            source_basis,
            window_start,
            window_end,
            status,
            source_matches_count,
            generated_at
        FROM rcon_annual_ranking_snapshots
        WHERE year = ? AND server_key = ? AND metric = ?
        LIMIT 1
        """,
        [year, server_key, metric],
    ).fetchone()
    return dict(row) if row else None


def _find_existing_snapshot(
    *,
    connection: object,
    year: int,
    server_key: str,
    metric: str,
) -> int | None:
    row = connection.execute(
        """
        SELECT id
        FROM rcon_annual_ranking_snapshots
        WHERE year = ? AND server_key = ? AND metric = ?
        LIMIT 1
        """,
        [year, server_key, metric],
    ).fetchone()
    return int(row["id"]) if row else None


def _delete_existing_snapshot(
    *,
    connection: object,
    year: int,
    server_key: str,
    metric: str,
) -> int | None:
    existing_id = _find_existing_snapshot(
        connection=connection,
        year=year,
        server_key=server_key,
        metric=metric,
    )
    if existing_id is None:
        return None
    connection.execute(
        "DELETE FROM rcon_annual_ranking_snapshot_items WHERE snapshot_id = ?",
        (existing_id,),
    )
    connection.execute(
        "DELETE FROM rcon_annual_ranking_snapshots WHERE id = ?",
        (existing_id,),
    )
    return existing_id


def _insert_snapshot(
    *,
    connection: object,
    year: int,
    server_key: str,
    metric: str,
    limit: int,
    source_matches_count: int,
    window_start: str,
    window_end: str,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO rcon_annual_ranking_snapshots (
            year,
            server_key,
            metric,
            limit_size,
            source_basis,
            window_start,
            window_end,
            source_matches_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        [
            year,
            server_key,
            metric,
            limit,
            MATCH_RESULT_SOURCE,
            window_start,
            window_end,
            source_matches_count,
        ],
    )
    row = cursor.fetchone()
    if row is not None and row["id"] is not None:
        return int(row["id"])

    existing = _find_existing_snapshot(
        connection=connection,
        year=year,
        server_key=server_key,
        metric=metric,
    )
    if existing is None:
        raise RuntimeError("Unable to resolve annual snapshot id after insert.")
    return existing


def _insert_items(
    *,
    connection: object,
    snapshot_id: int,
    rows: list[dict[str, object]],
    limit: int,
) -> None:
    for index, row in enumerate(rows[:limit], start=1):
        kills = int(row.get("kills") or 0)
        deaths = int(row.get("deaths") or 0)
        metric_value = int(row.get("metric_value") or 0)
        connection.execute(
            """
            INSERT INTO rcon_annual_ranking_snapshot_items (
                snapshot_id,
                ranking_position,
                player_id,
                player_name,
                metric_value,
                matches_considered,
                kills,
                deaths,
                teamkills,
                kd_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                snapshot_id,
                index,
                str(row.get("player_id")),
                str(row.get("player_name")),
                metric_value,
                int(row.get("matches_considered") or 0),
                kills,
                deaths,
                int(row.get("teamkills") or 0),
                float(kills / deaths) if deaths else float(kills),
            ],
        )


def _get_snapshot(*, connection: object, snapshot_id: int) -> dict[str, object] | None:
    row = connection.execute(
        """
        SELECT
            id,
            year,
            server_key,
            metric,
            limit_size,
            source_basis,
            window_start,
            window_end,
            status,
            source_matches_count,
            generated_at
        FROM rcon_annual_ranking_snapshots
        WHERE id = ?
        LIMIT 1
        """,
        [snapshot_id],
    ).fetchone()
    if not row:
        return None
    return dict(row)


def _list_items(*, connection: object, snapshot_id: int, limit: int | None = None) -> list[dict[str, object]]:
    params: list[object] = [snapshot_id]
    query = """
        SELECT
            ranking_position,
            player_id,
            player_name,
            metric_value,
            matches_considered,
            kills,
            deaths,
            teamkills,
            kd_ratio
        FROM rcon_annual_ranking_snapshot_items
        WHERE snapshot_id = ?
        ORDER BY ranking_position ASC
    """
    if limit is not None:
        query = f"{query}\n        LIMIT ?"
        params.append(limit)
    rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def _count_items(*, connection: object, snapshot_id: int) -> int:
    row = connection.execute(
        """
        SELECT COUNT(*) AS item_count
        FROM rcon_annual_ranking_snapshot_items
        WHERE snapshot_id = ?
        """,
        [snapshot_id],
    ).fetchone()
    return int(row["item_count"] or 0) if row else 0


def _build_scope_sql(server_key: str, *, table_alias: str = "matches") -> tuple[str, list[object]]:
    if server_key == ALL_SERVERS_SLUG:
        return "", []
    return (
        f"AND ({table_alias}.target_key = ? OR {table_alias}.external_server_id = ?)",
        [server_key, server_key],
    )


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate annual ranking snapshots.")
    subparsers = parser.add_subparsers(dest="command")
    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("--year", type=int, required=True)
    generate_parser.add_argument("--server-key", default=None)
    generate_parser.add_argument("--metric", default="kills")
    generate_parser.add_argument("--limit", type=int, default=20)
    generate_parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=None,
        help="explicit local SQLite override; default operational mode uses PostgreSQL when configured",
    )
    generate_parser.add_argument("--replace-existing", action="store_true", default=True)
    parser.set_defaults(command="generate")
    args = parser.parse_args(argv)

    if args.command == "generate":
        payload = generate_annual_ranking_snapshot(
            year=args.year,
            server_key=args.server_key,
            metric=args.metric,
            limit=args.limit,
            replace_existing=args.replace_existing,
            db_path=args.sqlite_path,
        )
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
