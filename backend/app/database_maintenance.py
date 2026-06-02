"""Application-level database maintenance for bounded historical storage."""

from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from .config import (
    get_admin_log_critical_retention_days,
    get_admin_log_noncritical_retention_days,
    get_database_url,
    get_db_maintenance_batch_size,
    get_historical_weekly_fallback_min_matches,
    get_recent_matches_keep,
    get_server_snapshot_retention_days,
)
from .rcon_admin_log_materialization import MATCH_RESULT_SOURCE
from .sqlite_utils import connect_sqlite_writer
from .writer_lock import backend_writer_lock, build_writer_lock_holder

CRITICAL_ADMIN_LOG_EVENT_TYPES = frozenset({"kill", "match_start", "match_end"})


@dataclass(frozen=True, slots=True)
class MaintenanceOptions:
    apply: bool
    recent_matches_keep: int
    admin_log_noncritical_retention_days: int
    admin_log_critical_retention_days: int
    server_snapshot_retention_days: int
    batch_size: int
    vacuum_analyze: bool
    now: datetime


def run_database_maintenance_cleanup(
    *,
    apply: bool = False,
    recent_matches_keep: int | None = None,
    admin_log_noncritical_retention_days: int | None = None,
    admin_log_critical_retention_days: int | None = None,
    server_snapshot_retention_days: int | None = None,
    batch_size: int | None = None,
    vacuum_analyze: bool = False,
    now: str | datetime | None = None,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Plan or apply safe bounded cleanup for supported storage tables."""
    options = MaintenanceOptions(
        apply=apply,
        recent_matches_keep=recent_matches_keep or get_recent_matches_keep(),
        admin_log_noncritical_retention_days=(
            admin_log_noncritical_retention_days or get_admin_log_noncritical_retention_days()
        ),
        admin_log_critical_retention_days=(
            admin_log_critical_retention_days or get_admin_log_critical_retention_days()
        ),
        server_snapshot_retention_days=(
            server_snapshot_retention_days or get_server_snapshot_retention_days()
        ),
        batch_size=batch_size or get_db_maintenance_batch_size(),
        vacuum_analyze=vacuum_analyze,
        now=_resolve_now(now),
    )
    _emit_json_log(
        {
            "event": "database-maintenance-started",
            "mode": "apply" if options.apply else "dry-run",
            "database_backend": _database_backend_name(db_path=db_path),
            "database_url_configured": bool(get_database_url()) and db_path is None,
            "db_path": str(db_path) if db_path is not None else None,
            "recent_matches_keep": options.recent_matches_keep,
            "admin_log_noncritical_retention_days": options.admin_log_noncritical_retention_days,
            "admin_log_critical_retention_days": options.admin_log_critical_retention_days,
            "server_snapshot_retention_days": options.server_snapshot_retention_days,
            "batch_size": options.batch_size,
            "vacuum_analyze": options.vacuum_analyze,
            "now": _to_iso(options.now),
        }
    )

    try:
        if options.apply:
            with backend_writer_lock(
                holder=build_writer_lock_holder("app.database_maintenance cleanup"),
                storage_path=db_path,
            ):
                payload = _run_cleanup(options=options, db_path=db_path)
        else:
            payload = _run_cleanup(options=options, db_path=db_path)
        _emit_json_log(
            {
                "event": "database-maintenance-completed",
                **payload,
            }
        )
        return payload
    except Exception as exc:  # noqa: BLE001 - CLI reports structured diagnostics
        error_payload = {
            "status": "error",
            "mode": "apply" if options.apply else "dry-run",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        _emit_json_log({"event": "database-maintenance-error", **error_payload})
        return error_payload


def _run_cleanup(*, options: MaintenanceOptions, db_path: Path | None) -> dict[str, object]:
    with _connect_maintenance(db_path=db_path) as connection:
        existing_tables = _existing_table_names(connection)
        plan = _build_cleanup_plan(connection, existing_tables=existing_tables, options=options)
        _emit_json_log(
            {
                "event": "database-maintenance-plan",
                **plan["summary"],
            }
        )

        deleted_counts = {
            "rcon_match_player_stats": 0,
            "rcon_materialized_matches": 0,
            "rcon_admin_log_events": 0,
            "server_snapshots": 0,
        }
        if options.apply:
            deleted_counts["rcon_match_player_stats"] = _delete_match_player_stats(
                connection,
                matches=plan["candidate_matches"],
                batch_size=options.batch_size,
            )
            deleted_counts["rcon_materialized_matches"] = _delete_ids_in_batches(
                connection,
                table_name="rcon_materialized_matches",
                ids=[int(row["id"]) for row in plan["candidate_matches"]],
                batch_size=options.batch_size,
            )
            deleted_counts["rcon_admin_log_events"] = _delete_ids_in_batches(
                connection,
                table_name="rcon_admin_log_events",
                ids=plan["candidate_admin_log_ids"],
                batch_size=options.batch_size,
            )
            deleted_counts["server_snapshots"] = _delete_ids_in_batches(
                connection,
                table_name="server_snapshots",
                ids=plan["candidate_server_snapshot_ids"],
                batch_size=options.batch_size,
            )
            if options.vacuum_analyze:
                _run_vacuum_analyze(connection)

    return {
        "status": "ok",
        "mode": "apply" if options.apply else "dry-run",
        "deleted_counts": deleted_counts,
        "plan": plan["summary"],
    }


def _build_cleanup_plan(
    connection: sqlite3.Connection | Any,
    *,
    existing_tables: set[str],
    options: MaintenanceOptions,
) -> dict[str, object]:
    candidate_server_snapshot_ids: list[int] = []
    candidate_admin_log_ids: list[int] = []
    candidate_matches: list[dict[str, object]] = []
    protected_match_keys: list[str] = []
    skipped_tables: list[str] = []

    if "server_snapshots" not in existing_tables:
        skipped_tables.append("server_snapshots")
        _emit_skip("server_snapshots", "table-missing")
    else:
        cutoff = options.now - timedelta(days=options.server_snapshot_retention_days)
        for row in connection.execute(
            "SELECT id, captured_at FROM server_snapshots ORDER BY id ASC"
        ).fetchall():
            captured_at = _parse_datetime(row["captured_at"])
            if captured_at is None:
                continue
            if captured_at < cutoff:
                candidate_server_snapshot_ids.append(int(row["id"]))

    protected_ranges: dict[str, list[tuple[int, int]]] = {}
    if "rcon_materialized_matches" not in existing_tables:
        skipped_tables.append("rcon_materialized_matches")
        _emit_skip("rcon_materialized_matches", "table-missing")
    else:
        (
            candidate_matches,
            protected_matches,
            protected_ranges,
            protection_summary,
        ) = _plan_materialized_match_cleanup(connection, options=options)
        protected_match_keys = [str(row["match_key"]) for row in protected_matches]
    if "rcon_match_player_stats" not in existing_tables:
        skipped_tables.append("rcon_match_player_stats")
        _emit_skip("rcon_match_player_stats", "table-missing")

    if "rcon_admin_log_events" not in existing_tables:
        skipped_tables.append("rcon_admin_log_events")
        _emit_skip("rcon_admin_log_events", "table-missing")
    else:
        candidate_admin_log_ids = _plan_admin_log_cleanup(
            connection,
            options=options,
            protected_ranges=protected_ranges,
        )

    candidate_player_stat_rows = 0
    if candidate_matches and "rcon_match_player_stats" in existing_tables:
        candidate_player_stat_rows = _count_candidate_player_stats(connection, candidate_matches)

    summary = {
        "status": "ok",
        "protected_match_count": len(protected_match_keys),
        "candidate_match_count": len(candidate_matches),
        "candidate_match_player_stat_count": candidate_player_stat_rows,
        "candidate_admin_log_event_count": len(candidate_admin_log_ids),
        "candidate_server_snapshot_count": len(candidate_server_snapshot_ids),
        "skipped_tables": skipped_tables,
        "protected_match_keys_preview": protected_match_keys[:10],
    }
    if "protection_summary" in locals():
        summary["protection_summary"] = protection_summary

    return {
        "candidate_server_snapshot_ids": candidate_server_snapshot_ids,
        "candidate_admin_log_ids": candidate_admin_log_ids,
        "candidate_matches": candidate_matches,
        "summary": summary,
    }


def _plan_materialized_match_cleanup(
    connection: sqlite3.Connection | Any,
    *,
    options: MaintenanceOptions,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, list[tuple[int, int]]], dict[str, object]]:
    rows = [
        dict(row)
        for row in connection.execute(
            """
            SELECT id, target_key, match_key, started_at, ended_at,
                   started_server_time, ended_server_time, source_basis
            FROM rcon_materialized_matches
            WHERE source_basis = ?
            """,
            (MATCH_RESULT_SOURCE,),
        ).fetchall()
    ]
    closed_rows: list[dict[str, object]] = []
    protected_rows: list[dict[str, object]] = []
    current_month_start = options.now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    current_week_start = (options.now - timedelta(days=options.now.weekday())).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    previous_week_start = current_week_start - timedelta(days=7)

    for row in rows:
        closed_at = _parse_datetime(row.get("ended_at") or row.get("started_at"))
        if closed_at is None:
            row["_protect_reason"] = "unparseable-closed-at"
            protected_rows.append(row)
            continue
        row["_closed_at"] = closed_at
        closed_rows.append(row)

    closed_rows.sort(
        key=lambda row: (
            row["_closed_at"],
            _coerce_int(row.get("ended_server_time")) or _coerce_int(row.get("started_server_time")) or 0,
            _coerce_int(row.get("id")) or 0,
        ),
        reverse=True,
    )
    latest_ids = {int(row["id"]) for row in closed_rows[: options.recent_matches_keep]}
    current_week_count = sum(
        1 for row in closed_rows if current_week_start <= row["_closed_at"] < options.now
    )
    previous_week_count = sum(
        1 for row in closed_rows if previous_week_start <= row["_closed_at"] < current_week_start
    )
    protect_previous_week = (
        current_week_count < get_historical_weekly_fallback_min_matches()
        and previous_week_count > 0
    )
    protect_previous_month = options.now.day <= 7

    candidate_rows: list[dict[str, object]] = []
    protected_ranges: dict[str, list[tuple[int, int]]] = {}
    for row in closed_rows:
        closed_at = row["_closed_at"]
        should_protect = False
        if int(row["id"]) in latest_ids:
            should_protect = True
        elif closed_at >= current_month_start:
            should_protect = True
        elif protect_previous_month and previous_month_start <= closed_at < current_month_start:
            should_protect = True
        elif closed_at >= current_week_start:
            should_protect = True
        elif protect_previous_week and previous_week_start <= closed_at < current_week_start:
            should_protect = True

        if should_protect:
            protected_rows.append(row)
            lower = _coerce_int(row.get("started_server_time"))
            upper = _coerce_int(row.get("ended_server_time"))
            if lower is not None and upper is not None:
                protected_ranges.setdefault(str(row["target_key"]), []).append((lower, upper))
        else:
            candidate_rows.append(row)

    return (
        candidate_rows,
        protected_rows,
        protected_ranges,
        {
            "recent_matches_keep": options.recent_matches_keep,
            "current_week_closed_matches": current_week_count,
            "previous_week_closed_matches": previous_week_count,
            "protect_previous_week": protect_previous_week,
            "protect_previous_month": protect_previous_month,
            "current_week_start": _to_iso(current_week_start),
            "previous_week_start": _to_iso(previous_week_start),
            "current_month_start": _to_iso(current_month_start),
            "previous_month_start": _to_iso(previous_month_start),
        },
    )


def _plan_admin_log_cleanup(
    connection: sqlite3.Connection | Any,
    *,
    options: MaintenanceOptions,
    protected_ranges: dict[str, list[tuple[int, int]]],
) -> list[int]:
    noncritical_cutoff = options.now - timedelta(days=options.admin_log_noncritical_retention_days)
    critical_cutoff = options.now - timedelta(days=options.admin_log_critical_retention_days)
    candidate_ids: list[int] = []
    rows = connection.execute(
        """
        SELECT id, target_key, event_type, event_timestamp, server_time
        FROM rcon_admin_log_events
        ORDER BY id ASC
        """
    ).fetchall()
    for row in rows:
        event_type = str(row["event_type"] or "").strip()
        event_time = _parse_datetime(row["event_timestamp"])
        if event_time is None:
            continue
        if event_type in CRITICAL_ADMIN_LOG_EVENT_TYPES:
            if event_time >= critical_cutoff:
                continue
            server_time = _coerce_int(row["server_time"])
            if server_time is None:
                continue
            if _server_time_is_protected(
                target_key=str(row["target_key"] or ""),
                server_time=server_time,
                protected_ranges=protected_ranges,
            ):
                continue
            candidate_ids.append(int(row["id"]))
            continue
        if event_time < noncritical_cutoff:
            candidate_ids.append(int(row["id"]))
    return candidate_ids


def _count_candidate_player_stats(
    connection: sqlite3.Connection | Any,
    matches: Sequence[dict[str, object]],
) -> int:
    count = 0
    for batch in _chunked(list(matches), 250):
        clause, params = _match_pair_clause(batch)
        row = connection.execute(
            f"SELECT COUNT(*) AS count FROM rcon_match_player_stats WHERE {clause}",
            params,
        ).fetchone()
        count += int(row["count"] or 0)
    return count


def _delete_match_player_stats(
    connection: sqlite3.Connection | Any,
    *,
    matches: Sequence[dict[str, object]],
    batch_size: int,
) -> int:
    deleted = 0
    for batch in _chunked(list(matches), max(1, min(batch_size, 250))):
        clause, params = _match_pair_clause(batch)
        deleted_in_batch = int(
            connection.execute(
                f"DELETE FROM rcon_match_player_stats WHERE {clause}",
                params,
            ).rowcount
            or 0
        )
        _commit(connection)
        deleted += deleted_in_batch
        _emit_json_log(
            {
                "event": "database-maintenance-delete-batch",
                "table": "rcon_match_player_stats",
                "deleted_rows": deleted_in_batch,
                "batch_size": len(batch),
            }
        )
    return deleted


def _delete_ids_in_batches(
    connection: sqlite3.Connection | Any,
    *,
    table_name: str,
    ids: Sequence[int],
    batch_size: int,
) -> int:
    deleted = 0
    for batch in _chunked(list(ids), batch_size):
        placeholders = ",".join("?" for _ in batch)
        deleted_in_batch = int(
            connection.execute(
                f"DELETE FROM {table_name} WHERE id IN ({placeholders})",
                batch,
            ).rowcount
            or 0
        )
        _commit(connection)
        deleted += deleted_in_batch
        _emit_json_log(
            {
                "event": "database-maintenance-delete-batch",
                "table": table_name,
                "deleted_rows": deleted_in_batch,
                "batch_size": len(batch),
            }
        )
    return deleted


def _run_vacuum_analyze(connection: sqlite3.Connection | Any) -> None:
    raw_connection = _raw_connection(connection)
    if isinstance(raw_connection, sqlite3.Connection):
        raw_connection.execute("VACUUM")
        raw_connection.execute("ANALYZE")
        raw_connection.commit()
        return
    raw_connection.commit()
    raw_connection.autocommit = True
    try:
        raw_connection.execute("VACUUM ANALYZE")
    finally:
        raw_connection.autocommit = False


def _match_pair_clause(matches: Sequence[dict[str, object]]) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []
    for row in matches:
        clauses.append("(target_key = ? AND match_key = ?)")
        params.extend([row["target_key"], row["match_key"]])
    return " OR ".join(clauses), params


def _existing_table_names(connection: sqlite3.Connection | Any) -> set[str]:
    raw_connection = _raw_connection(connection)
    if isinstance(raw_connection, sqlite3.Connection):
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        return {str(row["name"]) for row in rows}
    rows = raw_connection.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """
    ).fetchall()
    return {str(row["table_name"]) for row in rows}


def _emit_skip(table_name: str, reason: str) -> None:
    _emit_json_log(
        {
            "event": "database-maintenance-table-skipped",
            "table": table_name,
            "reason": reason,
        }
    )


def _server_time_is_protected(
    *,
    target_key: str,
    server_time: int,
    protected_ranges: dict[str, list[tuple[int, int]]],
) -> bool:
    for lower, upper in protected_ranges.get(target_key, []):
        if lower <= server_time <= upper:
            return True
    return False


def _connect_maintenance(*, db_path: Path | None):
    if get_database_url() and db_path is None:
        from .postgres_rcon_storage import connect_postgres_compat

        return connect_postgres_compat()
    resolved_path = db_path or Path.cwd() / "backend" / "data" / "hll_vietnam_dev.sqlite3"
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    return closing(connect_sqlite_writer(resolved_path))


def _commit(connection: sqlite3.Connection | Any) -> None:
    _raw_connection(connection).commit()


def _raw_connection(connection: sqlite3.Connection | Any) -> sqlite3.Connection | Any:
    return connection.connection if hasattr(connection, "connection") else connection


def _database_backend_name(*, db_path: Path | None) -> str:
    return "postgres" if get_database_url() and db_path is None else "sqlite"


def _resolve_now(value: str | datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    parsed = _parse_datetime(value)
    if parsed is None:
        raise ValueError("--now must be an ISO 8601 timestamp or date.")
    return parsed


def _parse_datetime(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) == 10:
        text = f"{text}T00:00:00+00:00"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _coerce_int(value: object) -> int | None:
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        return None


def _chunked(values: Sequence[Any], size: int) -> Iterable[list[Any]]:
    for index in range(0, len(values), size):
        yield list(values[index : index + size])


def _emit_json_log(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=True, default=str), flush=True)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Database maintenance for HLL Vietnam.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    cleanup_parser = subparsers.add_parser("cleanup")
    cleanup_parser.add_argument("--dry-run", action="store_true")
    cleanup_parser.add_argument("--apply", action="store_true")
    cleanup_parser.add_argument("--recent-matches-keep", type=int, default=get_recent_matches_keep())
    cleanup_parser.add_argument(
        "--admin-log-noncritical-retention-days",
        type=int,
        default=get_admin_log_noncritical_retention_days(),
    )
    cleanup_parser.add_argument(
        "--admin-log-critical-retention-days",
        type=int,
        default=get_admin_log_critical_retention_days(),
    )
    cleanup_parser.add_argument(
        "--server-snapshot-retention-days",
        type=int,
        default=get_server_snapshot_retention_days(),
    )
    cleanup_parser.add_argument("--batch-size", type=int, default=get_db_maintenance_batch_size())
    cleanup_parser.add_argument("--vacuum-analyze", action="store_true")
    cleanup_parser.add_argument("--now", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command != "cleanup":
        raise ValueError("Unsupported command.")
    if args.apply and args.dry_run:
        raise ValueError("--apply and --dry-run are mutually exclusive.")
    payload = run_database_maintenance_cleanup(
        apply=bool(args.apply),
        recent_matches_keep=args.recent_matches_keep,
        admin_log_noncritical_retention_days=args.admin_log_noncritical_retention_days,
        admin_log_critical_retention_days=args.admin_log_critical_retention_days,
        server_snapshot_retention_days=args.server_snapshot_retention_days,
        batch_size=args.batch_size,
        vacuum_analyze=bool(args.vacuum_analyze),
        now=args.now,
    )
    return 0 if payload.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
