"""Report active PostgreSQL/displayed storage backend and migration parity counts."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing

from .config import get_database_url, get_storage_path, use_postgres_rcon_storage
from .rcon_admin_log_materialization import summarize_rcon_materialization_status
from .rcon_admin_log_storage import initialize_rcon_admin_log_storage
from .sqlite_utils import connect_sqlite_readonly


MIGRATED_RCON_TABLES = (
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
        from .postgres_display_storage import table_counts

        rcon_counts = count_migrated_tables()
        displayed_counts = table_counts()
        backend = "postgresql"
    else:
        rcon_counts = _count_sqlite_tables()
        displayed_counts = {}
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
            "public-scoreboard-historical-matches-and-player-stats",
            "weekly-rankings",
            "monthly-rankings",
            "displayed-historical-snapshots",
            "server-summary-and-live-server-cache",
            "player-event-ledger",
        ],
        "table_counts": {
            **rcon_counts,
            **displayed_counts,
            "admin_log_events": rcon_counts.get("rcon_admin_log_events", 0),
            "materialized_matches": rcon_counts.get("rcon_materialized_matches", 0),
            "player_stats": rcon_counts.get("rcon_match_player_stats", 0),
            "public_scoreboard_historical_matches": displayed_counts.get(
                "historical_matches", 0
            ),
            "weekly_rankings_source_stats": displayed_counts.get(
                "historical_player_match_stats", 0
            ),
            "monthly_rankings_source_stats": displayed_counts.get(
                "historical_player_match_stats", 0
            ),
            "server_summary_cache": displayed_counts.get("displayed_historical_snapshots", 0),
            "player_event_ledger": displayed_counts.get("player_event_raw_ledger", 0),
            "scoreboard_candidates": rcon_counts.get("rcon_scoreboard_match_candidates", 0),
        },
        "latest_materialized_matches": materialization["latest_materialized_matches"],
        "latest_admin_log_match_end_events": materialization[
            "latest_admin_log_match_end_events"
        ],
        "match_end_status": materialization["match_end_status"],
        "remaining_sqlite_or_file_backed_domains": [
            {
                "domain": "public-scoreboard ingestion run and backfill checkpoints",
                "displayed_in_frontend": False,
                "reason": "operational import bookkeeping is not read by visible pages",
                "planned_phase": "phase-3-or-when-scoreboard-import-runs-on-postgresql",
            },
            {
                "domain": "Elo/MMR tables",
                "displayed_in_frontend": False,
                "reason": "Elo/MMR remains paused and hidden from visible pages",
                "planned_phase": "phase-3",
            },
        ],
        "sqlite_remaining": [
            "public-scoreboard ingestion run and backfill checkpoints",
            "paused Elo/MMR tables",
        ],
        "scoreboard_correlation": "PostgreSQL safe candidates and migrated trusted historical match URLs are used.",
        "migration_parity_summary": {
            "available": backend == "postgresql",
            "source_command": "python -m app.sqlite_to_postgres_migration",
            "displayed_historical_storage": (
                "postgresql" if backend == "postgresql" else "sqlite-or-file-fallback"
            ),
        },
    }


def _count_sqlite_tables() -> dict[str, int]:
    resolved_path = initialize_rcon_admin_log_storage()
    counts: dict[str, int] = {}
    with closing(connect_sqlite_readonly(resolved_path)) as connection:
        for table_name in MIGRATED_RCON_TABLES:
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
    print(json.dumps(build_storage_diagnostics(), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
