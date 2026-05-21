"""Report active phase-1 RCON storage backend and migrated table counts."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing

from .config import get_database_url, get_storage_path, use_postgres_rcon_storage
from .rcon_admin_log_materialization import summarize_rcon_materialization_status
from .rcon_admin_log_storage import initialize_rcon_admin_log_storage
from .sqlite_utils import connect_sqlite_readonly


MIGRATED_TABLES = (
    "rcon_admin_log_events",
    "rcon_player_profile_snapshots",
    "rcon_materialized_matches",
    "rcon_match_player_stats",
    "rcon_historical_targets",
    "rcon_historical_samples",
    "rcon_historical_competitive_windows",
    "rcon_scoreboard_match_candidates",
)


def build_storage_diagnostics() -> dict[str, object]:
    """Return one JSON-safe diagnostic payload for the migrated domains."""
    if use_postgres_rcon_storage():
        from .postgres_rcon_storage import count_migrated_tables

        counts = count_migrated_tables()
        backend = "postgresql"
    else:
        counts = _count_sqlite_tables()
        backend = "sqlite-fallback"
    materialization = summarize_rcon_materialization_status()
    return {
        "active_storage_backend": backend,
        "database_url_configured": bool(get_database_url()),
        "sqlite_fallback_path": str(get_storage_path()),
        "migrated_domains": [
            "rcon-admin-log-events",
            "rcon-player-profile-snapshots",
            "rcon-historical-capture-samples-and-windows",
            "rcon-materialized-matches",
            "rcon-materialized-player-stats",
            "rcon-safe-scoreboard-candidates",
        ],
        "table_counts": counts,
        "latest_materialized_matches": materialization["latest_materialized_matches"],
        "latest_admin_log_match_end_events": materialization[
            "latest_admin_log_match_end_events"
        ],
        "match_end_status": materialization["match_end_status"],
        "sqlite_remaining": [
            "live server snapshots and /api/servers cache",
            "public-scoreboard historical_* tables and scoreboard fallback data",
            "historical snapshots, player-event ledger and Elo/MMR tables",
        ],
        "scoreboard_correlation": (
            "PostgreSQL safe candidates are preferred when present; phase-1 still falls "
            "back to trusted persisted historical_* scoreboard rows on SQLite."
        ),
    }


def _count_sqlite_tables() -> dict[str, int]:
    resolved_path = initialize_rcon_admin_log_storage()
    counts: dict[str, int] = {}
    with closing(connect_sqlite_readonly(resolved_path)) as connection:
        for table_name in MIGRATED_TABLES:
            try:
                row = connection.execute(
                    f"SELECT COUNT(*) AS count FROM {table_name}"
                ).fetchone()
            except sqlite3.Error:
                counts[table_name] = 0
            else:
                counts[table_name] = int(row["count"] or 0)
    return counts


def main() -> None:
    print(json.dumps(build_storage_diagnostics(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
