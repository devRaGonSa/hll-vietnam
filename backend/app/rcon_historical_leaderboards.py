"""Leaderboard read model over materialized RCON/AdminLog match stats."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from .config import get_storage_path, use_postgres_rcon_storage
from .historical_storage import ALL_SERVERS_SLUG
from .rcon_admin_log_materialization import (
    MATCH_RESULT_SOURCE,
    initialize_rcon_materialized_storage,
)
from .sqlite_utils import connect_sqlite_readonly

LeaderboardTimeframe = Literal["weekly", "monthly"]
LeaderboardMetric = Literal["kills", "deaths", "matches_over_100_kills", "support"]


def build_rcon_materialized_leaderboard_snapshot_payload(
    *,
    server_id: str | None = None,
    timeframe: str = "weekly",
    metric: str = "kills",
    limit: int = 10,
) -> dict[str, object]:
    """Return an API payload for RCON-backed leaderboard snapshots.

    This is a runtime fast read over the materialized AdminLog tables. It intentionally
    avoids the old public-scoreboard fallback because the UI is running in RCON mode.
    """

    normalized_timeframe = _normalize_timeframe(timeframe)
    normalized_metric = _normalize_metric(metric)
    result = list_rcon_materialized_leaderboard(
        server_key=server_id,
        timeframe=normalized_timeframe,
        metric=normalized_metric,
        limit=limit,
    )
    items = list(result.get("items") or [])[:limit]
    return {
        "status": "ok",
        "data": {
            "title": _build_title(
                metric=normalized_metric,
                timeframe=normalized_timeframe,
                server_id=server_id,
            ),
            "context": f"historical-{normalized_timeframe}-leaderboard-snapshot",
            "source": "rcon-materialized-admin-log-leaderboard",
            "server_slug": server_id,
            "timeframe": normalized_timeframe,
            "metric": normalized_metric,
            "found": True,
            "snapshot_status": "ready",
            "missing_reason": None,
            "request_path_policy": "runtime-rcon-materialized-fast-path",
            "generation_policy": "runtime-materialized-read",
            "generated_at": _to_iso(datetime.now(timezone.utc)),
            "source_range_start": result.get("source_range_start"),
            "source_range_end": result.get("source_range_end"),
            "is_stale": False,
            "freshness": "runtime",
            "window_days": result.get("window_days"),
            "window_start": result.get("window_start"),
            "window_end": result.get("window_end"),
            "window_kind": result.get("window_kind"),
            "window_label": result.get("window_label"),
            "uses_fallback": False,
            "selection_reason": result.get("selection_reason"),
            "current_week_start": result.get("current_week_start"),
            "current_week_closed_matches": result.get("current_week_closed_matches"),
            "previous_week_closed_matches": result.get("previous_week_closed_matches"),
            "current_month_start": result.get("current_month_start"),
            "current_month_closed_matches": result.get("current_month_closed_matches"),
            "previous_month_closed_matches": result.get("previous_month_closed_matches"),
            "sufficient_sample": result.get("sufficient_sample"),
            "snapshot_limit": result.get("limit"),
            "limit": limit,
            "runtime_enrichment": {
                "applied": False,
                "reason": None,
            },
            "primary_source": "rcon",
            "selected_source": "rcon",
            "fallback_used": False,
            "fallback_reason": None,
            "source_attempts": [
                {
                    "source": "rcon",
                    "role": "primary",
                    "status": "success",
                    "reason": "leaderboard-served-by-rcon-materialized-admin-log",
                    "message": None,
                }
            ],
            "items": items,
        },
    }


def list_rcon_materialized_leaderboard(
    *,
    server_key: str | None = None,
    timeframe: str = "weekly",
    metric: str = "kills",
    limit: int = 10,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Return a leaderboard built from materialized RCON/AdminLog player stats.

    RCON/AdminLog materialization currently has reliable kill/death/teamkill counters,
    but not public-scoreboard support points. For support, return an explicitly empty
    supported payload rather than falling back to unrelated public scoreboard storage.
    """

    normalized_timeframe = _normalize_timeframe(timeframe)
    normalized_metric = _normalize_metric(metric)
    normalized_limit = max(1, int(limit or 10))
    window = _build_window(normalized_timeframe)

    if normalized_metric == "support":
        return _empty_payload(
            server_key=server_key,
            timeframe=normalized_timeframe,
            metric=normalized_metric,
            limit=normalized_limit,
            window=window,
            reason="rcon-materialized-stats-do-not-include-support-score",
        )

    resolved_path = initialize_rcon_materialized_storage(db_path=db_path)
    connection_scope = _connect_scope(resolved_path, db_path=db_path)
    with connection_scope as connection:
        rows = _fetch_leaderboard_rows(
            connection,
            server_key=server_key,
            metric=normalized_metric,
            limit=normalized_limit,
            window_start=window["start"],
            window_end=window["end"],
        )
        counts = _fetch_match_counts(
            connection,
            server_key=server_key,
            timeframe=normalized_timeframe,
            window_start=window["start"],
            window_end=window["end"],
        )
        source_range = _fetch_source_range(
            connection,
            server_key=server_key,
            window_start=window["start"],
            window_end=window["end"],
        )

    items = [_build_item(row, index=index + 1) for index, row in enumerate(rows)]
    return {
        "source": "rcon-materialized-admin-log-leaderboard",
        "server_key": server_key,
        "metric": normalized_metric,
        "limit": normalized_limit,
        "window_days": window["days"],
        "window_start": _to_iso(window["start"]),
        "window_end": _to_iso(window["end"]),
        "window_kind": window["kind"],
        "window_label": window["label"],
        "uses_fallback": False,
        "selection_reason": "rcon-materialized-current-window",
        "current_week_start": _to_iso(_week_start(window["end"])),
        "current_week_closed_matches": counts["current_week_closed_matches"],
        "previous_week_closed_matches": counts["previous_week_closed_matches"],
        "current_month_start": _to_iso(_month_start(window["end"])),
        "current_month_closed_matches": counts["current_month_closed_matches"],
        "previous_month_closed_matches": counts["previous_month_closed_matches"],
        "sufficient_sample": {
            "minimum_closed_matches": 1,
            "current_week_closed_matches": counts["current_week_closed_matches"],
            "current_week_has_sufficient_sample": counts["current_week_closed_matches"] >= 1,
            "is_early_week": False,
            "fallback_max_weekday": 2,
        },
        "source_range_start": _to_iso(source_range[0]) if source_range[0] else None,
        "source_range_end": _to_iso(source_range[1]) if source_range[1] else None,
        "items": items,
    }


def _fetch_leaderboard_rows(
    connection: object,
    *,
    server_key: str | None,
    metric: str,
    limit: int,
    window_start: datetime,
    window_end: datetime,
) -> list[dict[str, object]]:
    scope_sql, scope_params = _build_scope_sql(server_key)
    metric_sql = {
        "kills": "SUM(COALESCE(stats.kills, 0))",
        "deaths": "SUM(COALESCE(stats.deaths, 0))",
        "matches_over_100_kills": "SUM(CASE WHEN COALESCE(stats.kills, 0) >= 100 THEN 1 ELSE 0 END)",
    }[metric]
    having_sql = f"HAVING {metric_sql} > 0"
    params: list[object] = [
        _to_iso(window_start),
        _to_iso(window_end),
        *scope_params,
        limit,
    ]
    rows = connection.execute(
        f"""
        SELECT
            stats.player_id,
            stats.player_name,
            {metric_sql} AS metric_value,
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
          AND TRIM(COALESCE(stats.player_name, '')) != ''
        GROUP BY stats.player_id, stats.player_name
        {having_sql}
        ORDER BY metric_value DESC, matches_considered DESC, stats.player_name ASC
        LIMIT ?
        """,
        [MATCH_RESULT_SOURCE, *params],
    ).fetchall()
    return [dict(row) for row in rows]


def _fetch_match_counts(
    connection: object,
    *,
    server_key: str | None,
    timeframe: str,
    window_start: datetime,
    window_end: datetime,
) -> dict[str, int]:
    current_week_start = _week_start(window_end)
    previous_week_start = current_week_start - timedelta(days=7)
    current_month_start = _month_start(window_end)
    previous_month_start = _previous_month_start(current_month_start)
    return {
        "current_week_closed_matches": _count_matches(
            connection,
            server_key=server_key,
            start=current_week_start,
            end=window_end,
        ),
        "previous_week_closed_matches": _count_matches(
            connection,
            server_key=server_key,
            start=previous_week_start,
            end=current_week_start,
        ),
        "current_month_closed_matches": _count_matches(
            connection,
            server_key=server_key,
            start=current_month_start,
            end=window_end,
        ),
        "previous_month_closed_matches": _count_matches(
            connection,
            server_key=server_key,
            start=previous_month_start,
            end=current_month_start,
        ),
    }


def _fetch_source_range(
    connection: object,
    *,
    server_key: str | None,
    window_start: datetime,
    window_end: datetime,
) -> tuple[datetime | None, datetime | None]:
    scope_sql, scope_params = _build_scope_sql(server_key, table_alias="matches")
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
        [MATCH_RESULT_SOURCE, _to_iso(window_start), _to_iso(window_end), *scope_params],
    ).fetchone()
    if not row:
        return None, None
    return _parse_datetime(row["source_range_start"]), _parse_datetime(row["source_range_end"])


def _count_matches(
    connection: object,
    *,
    server_key: str | None,
    start: datetime,
    end: datetime,
) -> int:
    scope_sql, scope_params = _build_scope_sql(server_key, table_alias="matches")
    row = connection.execute(
        f"""
        SELECT COUNT(*) AS count
        FROM rcon_materialized_matches AS matches
        WHERE matches.source_basis = ?
          AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) >= ?
          AND COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) < ?
          {scope_sql}
        """,
        [MATCH_RESULT_SOURCE, _to_iso(start), _to_iso(end), *scope_params],
    ).fetchone()
    return int(row["count"] or 0) if row else 0


def _build_item(row: dict[str, object], *, index: int) -> dict[str, object]:
    kills = _coerce_int(row.get("kills"))
    deaths = _coerce_int(row.get("deaths"))
    return {
        "ranking_position": index,
        "player": {
            "id": row.get("player_id"),
            "name": row.get("player_name"),
        },
        "player_id": row.get("player_id"),
        "player_name": row.get("player_name"),
        "metric_value": _coerce_int(row.get("metric_value")),
        "matches_considered": _coerce_int(row.get("matches_considered")),
        "kills": kills,
        "deaths": deaths,
        "teamkills": _coerce_int(row.get("teamkills")),
        "kd_ratio": round(kills / deaths, 2) if deaths else float(kills),
    }


def _build_scope_sql(
    server_key: str | None,
    *,
    table_alias: str = "matches",
) -> tuple[str, list[object]]:
    if not server_key or server_key == ALL_SERVERS_SLUG:
        return "", []
    return f"AND ({table_alias}.target_key = ? OR {table_alias}.external_server_id = ?)", [
        server_key,
        server_key,
    ]


def _connect_scope(resolved_path: Path, *, db_path: Path | None):
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import connect_postgres_compat

        return connect_postgres_compat()
    return closing(connect_sqlite_readonly(resolved_path))


def _empty_payload(
    *,
    server_key: str | None,
    timeframe: str,
    metric: str,
    limit: int,
    window: dict[str, object],
    reason: str,
) -> dict[str, object]:
    return {
        "source": "rcon-materialized-admin-log-leaderboard",
        "server_key": server_key,
        "metric": metric,
        "limit": limit,
        "window_days": window["days"],
        "window_start": _to_iso(window["start"]),
        "window_end": _to_iso(window["end"]),
        "window_kind": window["kind"],
        "window_label": window["label"],
        "uses_fallback": False,
        "selection_reason": reason,
        "current_week_start": _to_iso(_week_start(window["end"])),
        "current_week_closed_matches": 0,
        "previous_week_closed_matches": 0,
        "current_month_start": _to_iso(_month_start(window["end"])),
        "current_month_closed_matches": 0,
        "previous_month_closed_matches": 0,
        "sufficient_sample": {
            "minimum_closed_matches": 1,
            "current_week_closed_matches": 0,
            "current_week_has_sufficient_sample": False,
            "is_early_week": False,
            "fallback_max_weekday": 2,
        },
        "source_range_start": None,
        "source_range_end": None,
        "items": [],
    }


def _build_window(timeframe: str) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    if timeframe == "monthly":
        start = _month_start(now)
        return {
            "start": start,
            "end": now,
            "days": max(1, (now.date() - start.date()).days + 1),
            "kind": "current-month",
            "label": "Mes actual",
        }
    start = _week_start(now)
    return {
        "start": start,
        "end": now,
        "days": max(1, (now.date() - start.date()).days + 1),
        "kind": "current-week",
        "label": "Semana actual",
    }


def _week_start(value: datetime) -> datetime:
    point = value.astimezone(timezone.utc)
    start = point - timedelta(days=point.weekday())
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def _month_start(value: datetime) -> datetime:
    point = value.astimezone(timezone.utc)
    return point.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _previous_month_start(current_month_start: datetime) -> datetime:
    previous_month_end = current_month_start - timedelta(days=1)
    return _month_start(previous_month_end)


def _normalize_timeframe(value: str) -> LeaderboardTimeframe:
    return "monthly" if str(value or "").strip().lower() == "monthly" else "weekly"


def _normalize_metric(value: str) -> LeaderboardMetric:
    normalized = str(value or "kills").strip().lower()
    if normalized in {"kills", "deaths", "matches_over_100_kills", "support"}:
        return normalized  # type: ignore[return-value]
    return "kills"


def _build_title(*, metric: str, timeframe: str, server_id: str | None) -> str:
    timeframe_label = "mensual" if timeframe == "monthly" else "semanal"
    scope = "totales" if server_id == ALL_SERVERS_SLUG else "por servidor"
    metric_label = {
        "kills": "Top kills",
        "deaths": "Top muertes",
        "matches_over_100_kills": "Partidas 100+ kills",
        "support": "Top soporte",
    }.get(metric, "Top kills")
    return f"Snapshot {metric_label} {timeframe_label} {scope}"


def _coerce_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _parse_datetime(value: object) -> datetime | None:
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


def _to_iso(value: object) -> str:
    parsed = _parse_datetime(value)
    if parsed is None:
        parsed = datetime.now(timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
