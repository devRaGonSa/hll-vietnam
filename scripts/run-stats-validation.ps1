$ErrorActionPreference = "Stop"

Write-Host "Stats regression validation"

function Assert-FileExists {
    param(
        [string] $Path,
        [string] $Message
    )

    if (-not (Test-Path $Path)) {
        throw $Message
    }
}

function Assert-ContainsText {
    param(
        [string] $Content,
        [string] $Text,
        [string] $Message
    )

    if ($Content -notlike "*$Text*") {
        throw $Message
    }
}

function Get-HttpStatusCode {
    param([string] $Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        return [int] $response.StatusCode
    } catch [System.Net.WebException] {
        if ($_.Exception.Response) {
            return [int] $_.Exception.Response.StatusCode
        }
        throw
    }
}

function Assert-LastExitCode {
    param([string] $Message)

    if ($LASTEXITCODE -ne 0) {
        throw $Message
    }
}

Assert-FileExists "frontend/stats.html" "Missing frontend/stats.html"
Assert-FileExists "frontend/assets/js/stats.js" "Missing frontend/assets/js/stats.js"
Assert-FileExists "frontend/ranking.html" "Missing frontend/ranking.html"
Assert-FileExists "frontend/assets/js/ranking.js" "Missing frontend/assets/js/ranking.js"

$statsHtml = Get-Content -Raw "frontend/stats.html"
$statsJs = Get-Content -Raw "frontend/assets/js/stats.js"
$rankingHtml = Get-Content -Raw "frontend/ranking.html"
$rankingJs = Get-Content -Raw "frontend/assets/js/ranking.js"

Assert-ContainsText $statsHtml 'id="stats-search-form"' `
    "Stats page no longer exposes the player search form."
Assert-ContainsText $statsHtml 'id="stats-profile-panel"' `
    "Stats page no longer exposes the player profile panel."
Assert-ContainsText $statsHtml 'id="stats-annual-form"' `
    "Stats page no longer exposes the annual ranking form."
Assert-ContainsText $statsHtml 'id="stats-result-list"' `
    "Stats page no longer exposes player result list container."
Assert-ContainsText $statsHtml 'id="stats-weekly-summary"' `
    "Stats page no longer exposes weekly summary zone."
Assert-ContainsText $statsHtml 'id="stats-monthly-summary"' `
    "Stats page no longer exposes monthly summary zone."
Assert-ContainsText $statsHtml 'id="stats-search-state"' `
    "Stats page no longer exposes search state node."
Assert-ContainsText $statsHtml 'id="stats-annual-state"' `
    "Stats page no longer exposes annual ranking state node."
Assert-ContainsText $statsHtml 'id="stats-backend-state"' `
    "Stats page no longer exposes backend state chip."
Assert-ContainsText $statsHtml 'href="./ranking.html"' `
    "Stats page should keep a direct link to ranking."
Assert-ContainsText $statsJs 'getElementById("stats-search-form")' `
    "Stats JS no longer sets up search form lookup."
Assert-ContainsText $statsJs "loadPlayerProfile(" `
    "Stats JS no longer defines loadPlayerProfile."

Assert-ContainsText $rankingHtml 'id="ranking-form"' `
    "Ranking page no longer exposes the ranking filter form."
Assert-ContainsText $rankingHtml 'value="kills_per_match"' `
    "Ranking page should expose the kills_per_match option."
Assert-ContainsText $rankingHtml 'value="matches_considered"' `
    "Ranking page should expose the matches_considered option."
Assert-ContainsText $rankingHtml 'id="ranking-filter-note"' `
    "Ranking page should expose the ranking filter guidance note."
Assert-ContainsText $rankingHtml 'id="ranking-metric-heading"' `
    "Ranking page should expose the dynamic metric heading."
Assert-ContainsText $rankingJs "applyInitialUrlState" `
    "Ranking JS should restore filter state from the URL."
Assert-ContainsText $rankingJs "history.replaceState" `
    "Ranking JS should sync filter state into the URL."
Assert-ContainsText $rankingJs "El ranking anual sigue limitado a kills" `
    "Ranking JS should explain the annual kills-only constraint."
Assert-ContainsText $rankingJs "El limite solicitado no es valido." `
    "Ranking JS should expose a dedicated invalid-limit message."
Assert-ContainsText $rankingJs "/api/ranking" `
    "Ranking frontend no longer targets the ranking endpoint."

Assert-ContainsText $statsJs "/api/stats/players/search" `
    "Stats frontend no longer targets the player search endpoint."
Assert-ContainsText $statsJs "/api/stats/rankings/annual" `
    "Stats frontend no longer targets the annual ranking endpoint."
Assert-ContainsText $statsJs "/api/stats/players/" `
    "Stats frontend no longer targets the player profile endpoint."
Assert-ContainsText $statsJs "Promise.allSettled" `
    "Stats profile loader should resolve weekly/monthly windows with partial-failure tolerance."

$backendContractCheck = @'
import json
import os
import sqlite3
import sys
from contextlib import contextmanager, redirect_stdout
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path

sys.path.insert(0, "backend")

from app.routes import resolve_get_payload
from app.config import use_postgres_rcon_storage
import app.postgres_rcon_storage as postgres_rcon_storage
import app.historical_runner as historical_runner
import app.rcon_historical_leaderboards as ranking_leaderboards
import app.rcon_historical_player_stats as player_search_stats

initialize_ranking_snapshot_storage = ranking_leaderboards.initialize_ranking_snapshot_storage
generate_ranking_snapshot = ranking_leaderboards.generate_ranking_snapshot
get_latest_ranking_snapshot = ranking_leaderboards.get_latest_ranking_snapshot
refresh_ranking_snapshots = ranking_leaderboards.refresh_ranking_snapshots
initialize_player_search_index_storage = player_search_stats.initialize_player_search_index_storage
refresh_player_search_index = player_search_stats.refresh_player_search_index
initialize_player_period_stats_storage = player_search_stats.initialize_player_period_stats_storage
refresh_player_period_stats = player_search_stats.refresh_player_period_stats
search_rcon_materialized_players = player_search_stats.search_rcon_materialized_players
get_rcon_materialized_player_stats = player_search_stats.get_rcon_materialized_player_stats
MATCH_RESULT_SOURCE = player_search_stats.MATCH_RESULT_SOURCE


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def read_payload(path):
    status, payload = resolve_get_payload(path)
    require(status is not None, f"{path} did not resolve")
    return int(status), payload


def require_int(value, message):
    require(isinstance(value, int), message)


def require_str(value, message):
    require(isinstance(value, str), message)


def require_number(value, message):
    require(isinstance(value, (int, float)), message)


def build_snapshot_fixture():
    db_path = Path("backend/data/hll_vietnam_dev.sqlite3")
    initialize_ranking_snapshot_storage(db_path=db_path)
    weekly_window_start = "2026-06-02T00:00:00Z"
    weekly_window_end = "2026-06-09T00:00:00Z"
    monthly_window_start = "2026-06-01T00:00:00Z"
    monthly_window_end = "2026-06-09T00:00:00Z"
    fixture_generated_at = "2026-06-09T08:00:00Z"
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    with connection:
        connection.execute(
            """
            DELETE FROM ranking_snapshot_items
            WHERE snapshot_id IN (
                SELECT id
                FROM ranking_snapshots
                WHERE source = 'stats-validation-fixture'
            )
            """
        )
        connection.execute(
            "DELETE FROM ranking_snapshots WHERE source = 'stats-validation-fixture'"
        )
        weekly_id = connection.execute(
            """
            INSERT INTO ranking_snapshots (
                timeframe, server_id, metric, window_start, window_end, generated_at,
                source, snapshot_status, item_count, limit_size, source_matches_count,
                freshness, window_kind, window_label
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ready', 1, 20, 4, 'fresh', 'current-week', 'Semana actual')
            RETURNING id
            """,
            (
                "weekly",
                "all-servers",
                "kills",
                weekly_window_start,
                weekly_window_end,
                fixture_generated_at,
                "stats-validation-fixture",
            ),
        ).fetchone()["id"]
        monthly_id = connection.execute(
            """
            INSERT INTO ranking_snapshots (
                timeframe, server_id, metric, window_start, window_end, generated_at,
                source, snapshot_status, item_count, limit_size, source_matches_count,
                freshness, window_kind, window_label
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ready', 1, 20, 5, 'fresh', 'current-month', 'Mes actual')
            RETURNING id
            """,
            (
                "monthly",
                "comunidad-hispana-01",
                "kills_per_match",
                monthly_window_start,
                monthly_window_end,
                fixture_generated_at,
                "stats-validation-fixture",
            ),
        ).fetchone()["id"]
        connection.execute(
            """
            INSERT INTO ranking_snapshot_items (
                snapshot_id, ranking_position, player_id, player_name, metric_value,
                matches_considered, kills, deaths, teamkills, kd_ratio, kills_per_match
            ) VALUES (?, 1, 'fixture-player', 'Fixture Player', 99, 3, 297, 120, 1, 2.48, 99)
            """,
            (weekly_id,),
        )
        connection.execute(
            """
            INSERT INTO ranking_snapshot_items (
                snapshot_id, ranking_position, player_id, player_name, metric_value,
                matches_considered, kills, deaths, teamkills, kd_ratio, kills_per_match
            ) VALUES (?, 1, 'fixture-kpm-player', 'Fixture KPM Player', 42.5, 4, 170, 80, 0, 2.13, 42.5)
            """,
            (monthly_id,),
        )
    connection.close()
    return db_path


def validate_postgres_ranking_snapshot_schema_path():
    require(
        "AUTOINCREMENT" not in postgres_rcon_storage.RCON_SCHEMA_SQL,
        "PostgreSQL schema must not contain AUTOINCREMENT.",
    )
    require(
        "CREATE TABLE IF NOT EXISTS ranking_snapshots" in postgres_rcon_storage.RCON_SCHEMA_SQL,
        "PostgreSQL schema should define ranking_snapshots.",
    )
    require(
        "CREATE TABLE IF NOT EXISTS ranking_snapshot_items" in postgres_rcon_storage.RCON_SCHEMA_SQL,
        "PostgreSQL schema should define ranking_snapshot_items.",
    )
    require(
        "BIGSERIAL PRIMARY KEY" in postgres_rcon_storage.RCON_SCHEMA_SQL,
        "PostgreSQL snapshot schema should use BIGSERIAL primary keys.",
    )

    original_initialize_materialized = ranking_leaderboards.initialize_rcon_materialized_storage
    original_use_postgres_storage = ranking_leaderboards.use_postgres_rcon_storage
    original_initialize_postgres_storage = postgres_rcon_storage.initialize_postgres_rcon_storage
    calls = {"postgres_init": 0}

    ranking_leaderboards.initialize_rcon_materialized_storage = (
        lambda db_path=None: Path("backend/data/hll_vietnam_dev.sqlite3")
    )
    ranking_leaderboards.use_postgres_rcon_storage = lambda explicit_sqlite_path=None: True

    def fake_initialize_postgres_storage():
        calls["postgres_init"] += 1

    postgres_rcon_storage.initialize_postgres_rcon_storage = fake_initialize_postgres_storage

    try:
        initialize_ranking_snapshot_storage()
    finally:
        ranking_leaderboards.initialize_rcon_materialized_storage = original_initialize_materialized
        ranking_leaderboards.use_postgres_rcon_storage = original_use_postgres_storage
        postgres_rcon_storage.initialize_postgres_rcon_storage = original_initialize_postgres_storage

    require(
        calls["postgres_init"] == 1,
        "PostgreSQL ranking snapshot initialization should delegate to initialize_postgres_rcon_storage exactly once.",
    )


def validate_ranking_snapshot_cli_defaults():
    original_generate_ranking_snapshot = ranking_leaderboards.generate_ranking_snapshot
    original_refresh_ranking_snapshots = ranking_leaderboards.refresh_ranking_snapshots
    captured = {}

    def fake_generate_ranking_snapshot(**kwargs):
        captured.update(kwargs)
        return {
            "status": "ok",
            "snapshot": {
                "generated_at": datetime(2026, 6, 9, 8, 0, 0, tzinfo=timezone.utc),
                "window_start": date(2026, 6, 2),
            },
            "items": [],
        }

    ranking_leaderboards.generate_ranking_snapshot = fake_generate_ranking_snapshot

    try:
        stdout_buffer = StringIO()
        with redirect_stdout(stdout_buffer):
            exit_code = ranking_leaderboards._main([
                "generate-ranking-snapshot",
                "--timeframe", "weekly",
                "--server-key", "all",
                "--metric", "kills",
                "--limit", "20",
            ])
        require(exit_code == 0, "Ranking snapshot CLI should exit 0 for a valid command.")
        require(
            captured.get("db_path") is None,
            "Ranking snapshot CLI should use PostgreSQL-compatible db_path=None by default.",
        )
        serialized_default_payload = json.loads(stdout_buffer.getvalue())
        require(
            serialized_default_payload.get("data", {}).get("snapshot", {}).get("generated_at") == "2026-06-09T08:00:00Z",
            "Ranking snapshot CLI should serialize datetime values as ISO strings.",
        )
        require(
            serialized_default_payload.get("data", {}).get("snapshot", {}).get("window_start") == "2026-06-02",
            "Ranking snapshot CLI should serialize date values as ISO strings.",
        )

        captured.clear()
        stdout_buffer = StringIO()
        with redirect_stdout(stdout_buffer):
            exit_code = ranking_leaderboards._main([
                "generate-ranking-snapshot",
                "--timeframe", "weekly",
                "--server-key", "all",
                "--metric", "kills",
                "--limit", "20",
                "--sqlite-path", "backend/data/hll_vietnam_dev.sqlite3",
            ])
        require(exit_code == 0, "Ranking snapshot CLI with --sqlite-path should exit 0.")
        require(
            captured.get("db_path") == Path("backend/data/hll_vietnam_dev.sqlite3"),
            "Ranking snapshot CLI should pass the explicit --sqlite-path override through to generate_ranking_snapshot.",
        )

        captured.clear()

        def fake_refresh_ranking_snapshots(**kwargs):
            captured.update(kwargs)
            return {
                "status": "ok",
                "generated_at": datetime(2026, 6, 9, 8, 0, 0, tzinfo=timezone.utc),
                "combinations_expected": 36,
                "totals": {"combinations_expected": 36, "succeeded": 36, "failed": 0, "skipped_regeneration": 0},
                "results": [],
            }

        ranking_leaderboards.refresh_ranking_snapshots = fake_refresh_ranking_snapshots

        stdout_buffer = StringIO()
        with redirect_stdout(stdout_buffer):
            exit_code = ranking_leaderboards._main([
                "refresh-ranking-snapshots",
                "--limit", "30",
            ])
        require(exit_code == 0, "Ranking snapshot bulk CLI should exit 0 for a valid command.")
        require(
            captured.get("db_path") is None,
            "Ranking snapshot bulk CLI should use PostgreSQL-compatible db_path=None by default.",
        )
        require(
            captured.get("limit") == 30,
            "Ranking snapshot bulk CLI should preserve the requested limit.",
        )

        captured.clear()
        stdout_buffer = StringIO()
        with redirect_stdout(stdout_buffer):
            exit_code = ranking_leaderboards._main([
                "refresh-ranking-snapshots",
                "--limit", "30",
                "--sqlite-path", "backend/data/hll_vietnam_dev.sqlite3",
            ])
        require(exit_code == 0, "Ranking snapshot bulk CLI with --sqlite-path should exit 0.")
        require(
            captured.get("db_path") == Path("backend/data/hll_vietnam_dev.sqlite3"),
            "Ranking snapshot bulk CLI should pass the explicit --sqlite-path override through to refresh_ranking_snapshots.",
        )
    finally:
        ranking_leaderboards.generate_ranking_snapshot = original_generate_ranking_snapshot
        ranking_leaderboards.refresh_ranking_snapshots = original_refresh_ranking_snapshots


def validate_ranking_snapshot_bulk_refresh():
    original_generate_ranking_snapshot = ranking_leaderboards.generate_ranking_snapshot
    calls = []

    def fake_generate_ranking_snapshot(**kwargs):
        calls.append(kwargs)
        return {
            "status": "ok",
            "snapshot": {
                "id": len(calls),
                "snapshot_status": "ready",
                "window_start": "2026-06-01T00:00:00Z",
                "window_end": "2026-06-09T00:00:00Z",
                "generated_at": "2026-06-09T08:00:00Z",
            },
            "source_matches_count": 4,
            "ranked_players": 3,
            "skipped_regeneration": False,
        }

    ranking_leaderboards.generate_ranking_snapshot = fake_generate_ranking_snapshot

    try:
        payload = refresh_ranking_snapshots(limit=30)
    finally:
        ranking_leaderboards.generate_ranking_snapshot = original_generate_ranking_snapshot

    require(payload.get("status") == "ok", "Ranking snapshot bulk refresh should return ok when all combinations succeed.")
    require(payload.get("combinations_expected") == 36, "Ranking snapshot bulk refresh should expect 36 combinations.")
    totals = payload.get("totals") or {}
    require(totals.get("succeeded") == 36, "Ranking snapshot bulk refresh should report 36 successful combinations.")
    require(totals.get("failed") == 0, "Ranking snapshot bulk refresh should report zero failed combinations when all succeed.")
    require(len(payload.get("results") or []) == 36, "Ranking snapshot bulk refresh should report 36 result entries.")
    require(len(calls) == 36, "Ranking snapshot bulk refresh should invoke generate_ranking_snapshot 36 times.")

    seen = {
        (call.get("timeframe"), call.get("server_key"), call.get("metric"), call.get("limit"))
        for call in calls
    }
    require(len(seen) == 36, "Ranking snapshot bulk refresh should cover 36 unique timeframe/server/metric combinations.")
    require(
        ("weekly", "all-servers", "kills", 30) in seen,
        "Ranking snapshot bulk refresh should include weekly/all/kills with limit 30.",
    )
    require(
        ("monthly", "comunidad-hispana-02", "kills_per_match", 30) in seen,
        "Ranking snapshot bulk refresh should include monthly/comunidad-hispana-02/kills_per_match with limit 30.",
    )


def validate_ranking_snapshot_bulk_partial_failure():
    original_generate_ranking_snapshot = ranking_leaderboards.generate_ranking_snapshot

    def fake_generate_ranking_snapshot(**kwargs):
        if (
            kwargs.get("timeframe") == "monthly"
            and kwargs.get("server_key") == "comunidad-hispana-02"
            and kwargs.get("metric") == "kd_ratio"
        ):
            raise RuntimeError("forced bulk refresh validation failure")
        return {
            "status": "ok",
            "snapshot": {
                "id": 1,
                "snapshot_status": "ready",
                "window_start": "2026-06-01T00:00:00Z",
                "window_end": "2026-06-09T00:00:00Z",
                "generated_at": "2026-06-09T08:00:00Z",
            },
            "source_matches_count": 4,
            "ranked_players": 3,
            "skipped_regeneration": False,
        }

    ranking_leaderboards.generate_ranking_snapshot = fake_generate_ranking_snapshot

    try:
        payload = refresh_ranking_snapshots(limit=30)
    finally:
        ranking_leaderboards.generate_ranking_snapshot = original_generate_ranking_snapshot

    require(payload.get("status") == "partial", "Ranking snapshot bulk refresh should return partial when one combination fails.")
    totals = payload.get("totals") or {}
    require(totals.get("succeeded") == 35, "Ranking snapshot bulk refresh should continue after one failure and still report the remaining 35 successes.")
    require(totals.get("failed") == 1, "Ranking snapshot bulk refresh should report exactly one failed combination in the forced partial-failure test.")
    error_results = [
        result
        for result in (payload.get("results") or [])
        if isinstance(result, dict) and result.get("status") == "error"
    ]
    require(len(error_results) == 1, "Ranking snapshot bulk refresh should surface one explicit error result in the forced partial-failure test.")
    forced_error = error_results[0]
    require(
        forced_error.get("timeframe") == "monthly"
        and forced_error.get("server_key") == "comunidad-hispana-02"
        and forced_error.get("metric") == "kd_ratio",
        "Ranking snapshot bulk refresh should preserve the failing combination coordinates in error reporting.",
    )
    require(
        forced_error.get("error_type") == "RuntimeError",
        "Ranking snapshot bulk refresh should expose the failing error type.",
    )


def validate_ranking_snapshot_postgres_selection():
    original_database_url = os.environ.get("HLL_BACKEND_DATABASE_URL")
    original_connect_postgres_compat = postgres_rcon_storage.connect_postgres_compat
    calls = {"postgres_connect": 0}

    @contextmanager
    def fake_connect_postgres_compat():
        calls["postgres_connect"] += 1
        yield object()

    os.environ["HLL_BACKEND_DATABASE_URL"] = "postgresql://validation-user:validation-pass@127.0.0.1:5432/hll_validation"
    postgres_rcon_storage.connect_postgres_compat = fake_connect_postgres_compat

    try:
        require(
            use_postgres_rcon_storage(explicit_sqlite_path=None) is True,
            "PostgreSQL storage should be selected when DATABASE_URL is configured and no explicit SQLite path is provided.",
        )
        require(
            use_postgres_rcon_storage(explicit_sqlite_path=Path("backend/data/hll_vietnam_dev.sqlite3")) is False,
            "Explicit SQLite paths should still disable PostgreSQL storage selection.",
        )
        with ranking_leaderboards._connect_write_scope(
            Path("backend/data/hll_vietnam_dev.sqlite3"),
            db_path=None,
        ) as _connection:
            pass
        require(
            calls["postgres_connect"] == 1,
            "Ranking snapshot write scope should use PostgreSQL when db_path=None and DATABASE_URL is configured.",
        )
    finally:
        if original_database_url is None:
            os.environ.pop("HLL_BACKEND_DATABASE_URL", None)
        else:
            os.environ["HLL_BACKEND_DATABASE_URL"] = original_database_url
        postgres_rcon_storage.connect_postgres_compat = original_connect_postgres_compat


def validate_postgres_player_search_index_schema_path():
    require(
        "CREATE TABLE IF NOT EXISTS player_search_index" in postgres_rcon_storage.RCON_SCHEMA_SQL,
        "PostgreSQL schema should define player_search_index.",
    )
    require(
        "CREATE INDEX IF NOT EXISTS idx_player_search_index_name" in postgres_rcon_storage.RCON_SCHEMA_SQL,
        "PostgreSQL schema should define the player_search_index normalized name index.",
    )

    original_initialize_materialized = player_search_stats.initialize_rcon_materialized_storage
    original_use_postgres_storage = player_search_stats.use_postgres_rcon_storage
    original_initialize_postgres_storage = postgres_rcon_storage.initialize_postgres_rcon_storage
    calls = {"postgres_init": 0}

    player_search_stats.initialize_rcon_materialized_storage = (
        lambda db_path=None: Path("backend/data/hll_vietnam_dev.sqlite3")
    )
    player_search_stats.use_postgres_rcon_storage = lambda explicit_sqlite_path=None: True

    def fake_initialize_postgres_storage():
        calls["postgres_init"] += 1

    postgres_rcon_storage.initialize_postgres_rcon_storage = fake_initialize_postgres_storage

    try:
        initialize_player_search_index_storage()
    finally:
        player_search_stats.initialize_rcon_materialized_storage = original_initialize_materialized
        player_search_stats.use_postgres_rcon_storage = original_use_postgres_storage
        postgres_rcon_storage.initialize_postgres_rcon_storage = original_initialize_postgres_storage

    require(
        calls["postgres_init"] == 1,
        "Player search index initialization should delegate to initialize_postgres_rcon_storage exactly once.",
    )


def validate_player_search_index_cli_defaults():
    original_refresh_player_search_index = player_search_stats.refresh_player_search_index
    captured = {}

    def fake_refresh_player_search_index(**kwargs):
        captured.update(kwargs)
        return {
            "status": "ok",
            "generated_at": datetime(2026, 6, 9, 8, 0, 0, tzinfo=timezone.utc),
            "year": 2026,
            "source": "rcon-materialized-admin-log",
            "server_ids": ["all-servers", "comunidad-hispana-01", "comunidad-hispana-02"],
            "total_rows": 3,
            "results": [{"server_id": "all-servers", "row_count": 3}],
        }

    player_search_stats.refresh_player_search_index = fake_refresh_player_search_index
    try:
        stdout_buffer = StringIO()
        with redirect_stdout(stdout_buffer):
            exit_code = player_search_stats._main(["refresh-player-search-index"])
        require(exit_code == 0, "Player search index CLI should exit 0 for a valid command.")
        require(
            captured.get("db_path") is None,
            "Player search index CLI should use PostgreSQL-compatible db_path=None by default.",
        )
        serialized_default_payload = json.loads(stdout_buffer.getvalue())
        require(
            serialized_default_payload.get("data", {}).get("generated_at") == "2026-06-09T08:00:00Z",
            "Player search index CLI should serialize datetime values as ISO strings.",
        )

        captured.clear()
        stdout_buffer = StringIO()
        with redirect_stdout(stdout_buffer):
            exit_code = player_search_stats._main([
                "refresh-player-search-index",
                "--sqlite-path", "backend/data/hll_vietnam_dev.sqlite3",
            ])
        require(exit_code == 0, "Player search index CLI with --sqlite-path should exit 0.")
        require(
            captured.get("db_path") == Path("backend/data/hll_vietnam_dev.sqlite3"),
            "Player search index CLI should pass the explicit --sqlite-path override through to refresh_player_search_index.",
        )
    finally:
        player_search_stats.refresh_player_search_index = original_refresh_player_search_index


def build_player_search_fixture():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    db_path = Path(f"backend/data/hll_vietnam_player_search_validation_{stamp}.sqlite3")
    if db_path.exists():
        try:
            db_path.unlink()
        except PermissionError:
            pass
    initialize_player_search_index_storage(db_path=db_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    with connection:
        connection.execute(
            """
            INSERT INTO rcon_materialized_matches (
                target_key, external_server_id, match_key, map_name, map_pretty_name, game_mode,
                started_server_time, ended_server_time, started_at, ended_at,
                allied_score, axis_score, winner, confidence_mode, source_basis
            ) VALUES
                ('comunidad-hispana-01', 'comunidad-hispana-01', 'm1', 'stmarie', 'St. Marie Du Mont', 'warfare', 1, 2, '2026-03-01T18:00:00Z', '2026-03-01T19:00:00Z', 5, 3, 'allied', 'exact', ?),
                ('comunidad-hispana-02', 'comunidad-hispana-02', 'm2', 'foy', 'Foy', 'warfare', 3, 4, '2026-04-01T18:00:00Z', '2026-04-01T19:00:00Z', 2, 5, 'axis', 'exact', ?),
                ('comunidad-hispana-01', 'comunidad-hispana-01', 'm3', 'kursk', 'Kursk', 'warfare', 5, 6, '2025-12-01T18:00:00Z', '2025-12-01T19:00:00Z', 1, 0, 'allied', 'exact', ?)
            """,
            (MATCH_RESULT_SOURCE, MATCH_RESULT_SOURCE, MATCH_RESULT_SOURCE),
        )
        connection.execute(
            """
            INSERT INTO rcon_match_player_stats (
                target_key, match_key, player_id, player_name, team,
                kills, deaths, teamkills, deaths_by_teamkill,
                weapons_json, death_by_weapons_json, most_killed_json, death_by_json,
                first_seen_server_time, last_seen_server_time
            ) VALUES
                ('comunidad-hispana-01', 'm1', 'player-rambo', 'Rámbó', 'allied', 12, 4, 1, 0, '{}', '{}', '{}', '{}', 1, 2),
                ('comunidad-hispana-02', 'm2', 'player-rambo', 'Rambo', 'axis', 8, 6, 0, 0, '{}', '{}', '{}', '{}', 3, 4),
                ('comunidad-hispana-01', 'm3', 'player-rambo', 'Old Rambo', 'allied', 99, 1, 0, 0, '{}', '{}', '{}', '{}', 5, 6),
                ('comunidad-hispana-01', 'm1', 'player-ghost', 'Ghost', 'axis', 3, 9, 0, 0, '{}', '{}', '{}', '{}', 1, 2)
            """
        )
    connection.close()
    return db_path


def validate_player_search_index_refresh_and_search():
    db_path = build_player_search_fixture()
    try:
        payload = refresh_player_search_index(
            db_path=db_path,
            now=datetime(2026, 6, 9, 8, 0, 0, tzinfo=timezone.utc),
        )
        require(payload.get("status") == "ok", "Player search index refresh should return ok.")
        require(payload.get("year") == 2026, "Player search index refresh should use the current UTC year.")
        require_int(payload.get("total_rows"), "Player search index refresh should report numeric total_rows.")

        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT server_id, player_id, player_name, normalized_player_name,
                   matches_current_year, kills_current_year, deaths_current_year,
                   teamkills_current_year, servers_seen
            FROM player_search_index
            ORDER BY server_id ASC, player_id ASC
            """
        ).fetchall()
        connection.close()
        require(len(rows) >= 4, "Player search index refresh should materialize rows for all and per-server scopes.")
        all_scope_row = next(
            (
                dict(row)
                for row in rows
                if row["server_id"] == "all-servers" and row["player_id"] == "player-rambo"
            ),
            None,
        )
        require(all_scope_row is not None, "Player search index should contain an all-servers row for player-rambo.")
        require(
            all_scope_row["player_name"] == "Rambo",
            "Player search index should preserve the latest current-year player display name.",
        )
        require(
            all_scope_row["normalized_player_name"] == "rambo",
            "Player search index should persist an accent-insensitive normalized player name.",
        )
        require(
            int(all_scope_row["matches_current_year"] or 0) == 2,
            "Player search index should only count current-year matches.",
        )
        require(
            int(all_scope_row["kills_current_year"] or 0) == 20,
            "Player search index should aggregate current-year kills.",
        )
        require(
            json.loads(all_scope_row["servers_seen"]) == ["comunidad-hispana-01", "comunidad-hispana-02"],
            "Player search index should preserve the list of servers seen in scope order.",
        )

        read_model_result = search_rcon_materialized_players(
            query="Rambo",
            server_id="all",
            limit=10,
            db_path=db_path,
        )
        require(
            (read_model_result.get("source") or {}).get("read_model") == "player-search-index",
            "Player search should prefer player_search_index when populated.",
        )
        require(
            (read_model_result.get("source") or {}).get("fallback_used") is False,
            "Player search should not report fallback when player_search_index is used.",
        )
        items = read_model_result.get("items") or []
        require(len(items) >= 1, "Player search read model should return at least one item for Rambo.")
        require(
            items[0].get("player_id") == "player-rambo",
            "Player search read model should return player-rambo first for a direct-name query.",
        )
        require(
            items[0].get("matches_considered") == 2,
            "Player search read model should preserve the current-year match count in the public contract.",
        )

        server_scoped_result = search_rcon_materialized_players(
            query="Rambo",
            server_id="comunidad-hispana-01",
            limit=10,
            db_path=db_path,
        )
        server_items = server_scoped_result.get("items") or []
        require(
            len(server_items) >= 1 and server_items[0].get("matches_considered") == 1,
            "Server-scoped player search should use the server-specific index row when available.",
        )
    finally:
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                pass


def validate_player_search_index_fallbacks():
    db_path = build_player_search_fixture()
    try:
        fallback_result = search_rcon_materialized_players(
            query="Rambo",
            server_id="all",
            limit=10,
            db_path=db_path,
        )
        require(
            (fallback_result.get("source") or {}).get("fallback_used") is True,
            "Player search should fall back to runtime when player_search_index is empty.",
        )
        require(
            (fallback_result.get("source") or {}).get("fallback_reason") == "player-search-index-empty",
            "Player search should expose an explicit empty-index fallback reason.",
        )

        original_search_player_search_index = player_search_stats._search_player_search_index

        def fake_search_player_search_index(**kwargs):
            return None, "player-search-index-unavailable"

        player_search_stats._search_player_search_index = fake_search_player_search_index
        try:
            unavailable_result = search_rcon_materialized_players(
                query="Rambo",
                server_id="all",
                limit=10,
                db_path=db_path,
            )
        finally:
            player_search_stats._search_player_search_index = original_search_player_search_index

        require(
            (unavailable_result.get("source") or {}).get("fallback_used") is True,
            "Player search should preserve runtime fallback when the read model is unavailable.",
        )
        require(
            (unavailable_result.get("source") or {}).get("fallback_reason") == "player-search-index-unavailable",
            "Player search should expose an explicit unavailable-index fallback reason.",
        )
    finally:
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                pass


def validate_postgres_player_period_stats_schema_path():
    require(
        "CREATE TABLE IF NOT EXISTS player_period_stats" in postgres_rcon_storage.RCON_SCHEMA_SQL,
        "PostgreSQL schema should define player_period_stats.",
    )
    require(
        "CREATE INDEX IF NOT EXISTS idx_player_period_stats_player_period_server" in postgres_rcon_storage.RCON_SCHEMA_SQL,
        "PostgreSQL schema should define the player_period_stats player/period/server index.",
    )

    original_initialize_materialized = player_search_stats.initialize_rcon_materialized_storage
    original_use_postgres_storage = player_search_stats.use_postgres_rcon_storage
    original_initialize_postgres_storage = postgres_rcon_storage.initialize_postgres_rcon_storage
    calls = {"postgres_init": 0}

    player_search_stats.initialize_rcon_materialized_storage = (
        lambda db_path=None: Path("backend/data/hll_vietnam_dev.sqlite3")
    )
    player_search_stats.use_postgres_rcon_storage = lambda explicit_sqlite_path=None: True

    def fake_initialize_postgres_storage():
        calls["postgres_init"] += 1

    postgres_rcon_storage.initialize_postgres_rcon_storage = fake_initialize_postgres_storage

    try:
        initialize_player_period_stats_storage()
    finally:
        player_search_stats.initialize_rcon_materialized_storage = original_initialize_materialized
        player_search_stats.use_postgres_rcon_storage = original_use_postgres_storage
        postgres_rcon_storage.initialize_postgres_rcon_storage = original_initialize_postgres_storage

    require(
        calls["postgres_init"] == 1,
        "Player period stats initialization should delegate to initialize_postgres_rcon_storage exactly once.",
    )


def validate_player_period_stats_cli_defaults():
    original_refresh_player_period_stats = player_search_stats.refresh_player_period_stats
    captured = {}

    def fake_refresh_player_period_stats(**kwargs):
        captured.update(kwargs)
        return {
            "status": "ok",
            "generated_at": datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc),
            "source": "rcon-materialized-admin-log",
            "server_ids": ["all-servers", "comunidad-hispana-01", "comunidad-hispana-02"],
            "period_types": ["weekly", "monthly", "yearly"],
            "total_rows": 9,
            "results": [{"server_id": "all-servers", "period_type": "weekly", "row_count": 2}],
        }

    player_search_stats.refresh_player_period_stats = fake_refresh_player_period_stats
    try:
        stdout_buffer = StringIO()
        with redirect_stdout(stdout_buffer):
            exit_code = player_search_stats._main(["refresh-player-period-stats"])
        require(exit_code == 0, "Player period stats CLI should exit 0 for a valid command.")
        require(
            captured.get("db_path") is None,
            "Player period stats CLI should use PostgreSQL-compatible db_path=None by default.",
        )
        serialized_default_payload = json.loads(stdout_buffer.getvalue())
        require(
            serialized_default_payload.get("data", {}).get("generated_at") == "2026-06-10T12:00:00Z",
            "Player period stats CLI should serialize datetime values as ISO strings.",
        )

        captured.clear()
        stdout_buffer = StringIO()
        with redirect_stdout(stdout_buffer):
            exit_code = player_search_stats._main([
                "refresh-player-period-stats",
                "--sqlite-path", "backend/data/hll_vietnam_dev.sqlite3",
            ])
        require(exit_code == 0, "Player period stats CLI with --sqlite-path should exit 0.")
        require(
            captured.get("db_path") == Path("backend/data/hll_vietnam_dev.sqlite3"),
            "Player period stats CLI should pass the explicit --sqlite-path override through to refresh_player_period_stats.",
        )
    finally:
        player_search_stats.refresh_player_period_stats = original_refresh_player_period_stats


def build_player_period_stats_fixture():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    db_path = Path(f"backend/data/hll_vietnam_player_period_stats_validation_{stamp}.sqlite3")
    if db_path.exists():
        try:
            db_path.unlink()
        except PermissionError:
            pass
    initialize_player_period_stats_storage(db_path=db_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    with connection:
        connection.execute(
            """
            INSERT INTO rcon_materialized_matches (
                target_key, external_server_id, match_key, map_name, map_pretty_name, game_mode,
                started_server_time, ended_server_time, started_at, ended_at,
                allied_score, axis_score, winner, confidence_mode, source_basis
            ) VALUES
                ('comunidad-hispana-01', 'comunidad-hispana-01', 's1w1', 'stmarie', 'St. Marie Du Mont', 'warfare', 101, 102, '2026-06-08T18:00:00Z', '2026-06-08T19:00:00Z', 5, 3, 'allied', 'exact', ?),
                ('comunidad-hispana-01', 'comunidad-hispana-01', 's1w2', 'foy', 'Foy', 'warfare', 103, 104, '2026-06-09T18:00:00Z', '2026-06-09T19:00:00Z', 2, 5, 'axis', 'exact', ?),
                ('comunidad-hispana-01', 'comunidad-hispana-01', 's1w3', 'kursk', 'Kursk', 'warfare', 105, 106, '2026-06-10T18:00:00Z', '2026-06-10T19:00:00Z', 4, 1, 'allied', 'exact', ?),
                ('comunidad-hispana-02', 'comunidad-hispana-02', 's2w1', 'hurtgen', 'Hurtgen Forest', 'warfare', 201, 202, '2026-06-08T20:00:00Z', '2026-06-08T21:00:00Z', 5, 0, 'allied', 'exact', ?),
                ('comunidad-hispana-02', 'comunidad-hispana-02', 's2w2', 'kharkov', 'Kharkov', 'warfare', 203, 204, '2026-06-09T20:00:00Z', '2026-06-09T21:00:00Z', 3, 2, 'allied', 'exact', ?),
                ('comunidad-hispana-02', 'comunidad-hispana-02', 's2w3', 'driel', 'Driel', 'warfare', 205, 206, '2026-06-10T20:00:00Z', '2026-06-10T21:00:00Z', 2, 1, 'allied', 'exact', ?),
                ('comunidad-hispana-01', 'comunidad-hispana-01', 's1y1', 'utah', 'Utah Beach', 'warfare', 401, 402, '2026-01-15T18:00:00Z', '2026-01-15T19:00:00Z', 5, 1, 'allied', 'exact', ?),
                ('comunidad-hispana-01', 'comunidad-hispana-01', 'old-year', 'omaha', 'Omaha Beach', 'warfare', 301, 302, '2025-12-15T18:00:00Z', '2025-12-15T19:00:00Z', 1, 0, 'allied', 'exact', ?)
            """,
            (
                MATCH_RESULT_SOURCE,
                MATCH_RESULT_SOURCE,
                MATCH_RESULT_SOURCE,
                MATCH_RESULT_SOURCE,
                MATCH_RESULT_SOURCE,
                MATCH_RESULT_SOURCE,
                MATCH_RESULT_SOURCE,
                MATCH_RESULT_SOURCE,
            ),
        )
        connection.execute(
            """
            INSERT INTO rcon_match_player_stats (
                target_key, match_key, player_id, player_name, team,
                kills, deaths, teamkills, deaths_by_teamkill,
                weapons_json, death_by_weapons_json, most_killed_json, death_by_json,
                first_seen_server_time, last_seen_server_time
            ) VALUES
                ('comunidad-hispana-01', 's1w1', 'regression-player', 'Old Regression', 'allied', 10, 4, 1, 0, '{}', '{}', '{}', '{}', 101, 102),
                ('comunidad-hispana-01', 's1w2', 'regression-player', 'Regression Hero', 'axis', 9, 5, 0, 0, '{}', '{}', '{}', '{}', 103, 104),
                ('comunidad-hispana-01', 's1w3', 'regression-player', 'Regression Hero', 'allied', 11, 3, 0, 0, '{}', '{}', '{}', '{}', 105, 106),
                ('comunidad-hispana-02', 's2w1', 'regression-player', 'Regression Hero', 'allied', 4, 2, 0, 0, '{}', '{}', '{}', '{}', 201, 202),
                ('comunidad-hispana-02', 's2w2', 'regression-player', 'Regression Hero', 'allied', 5, 4, 0, 0, '{}', '{}', '{}', '{}', 203, 204),
                ('comunidad-hispana-02', 's2w3', 'regression-player', 'Regression Hero', 'allied', 3, 2, 0, 0, '{}', '{}', '{}', '{}', 205, 206),
                ('comunidad-hispana-01', 's1y1', 'yearly-only-player', 'Yearly Only', 'allied', 8, 3, 0, 0, '{}', '{}', '{}', '{}', 401, 402),
                ('comunidad-hispana-01', 'old-year', 'regression-player', 'Historic Regression', 'allied', 99, 1, 0, 0, '{}', '{}', '{}', '{}', 301, 302),
                ('comunidad-hispana-01', 's1w1', 'other-player', 'Other Player', 'axis', 5, 7, 0, 0, '{}', '{}', '{}', '{}', 101, 102),
                ('comunidad-hispana-01', 's1w2', 'other-player', 'Other Player', 'allied', 3, 6, 0, 0, '{}', '{}', '{}', '{}', 103, 104),
                ('comunidad-hispana-01', 's1w3', 'other-player', 'Other Player', 'axis', 4, 8, 0, 0, '{}', '{}', '{}', '{}', 105, 106),
                ('comunidad-hispana-02', 's2w1', 'other-player', 'Other Player', 'axis', 1, 4, 0, 0, '{}', '{}', '{}', '{}', 201, 202),
                ('comunidad-hispana-02', 's2w2', 'other-player', 'Other Player', 'axis', 2, 3, 0, 0, '{}', '{}', '{}', '{}', 203, 204),
                ('comunidad-hispana-02', 's2w3', 'other-player', 'Other Player', 'axis', 1, 2, 0, 0, '{}', '{}', '{}', '{}', 205, 206)
            """
        )
    connection.close()
    return db_path


def validate_fetch_player_stats_sql_contract():
    captured = {}

    class FakeResult:
        def fetchone(self):
            return {
                "player_name": None,
                "matches_considered": 0,
                "kills": 0,
                "deaths": 0,
                "teamkills": 0,
            }

    class FakeConnection:
        def execute(self, sql, params):
            captured["sql"] = sql
            captured["params"] = list(params)
            return FakeResult()

    result = player_search_stats._fetch_player_stats(
        connection=FakeConnection(),
        player_id="regression-player",
        server_id="comunidad-hispana-01",
        window={
            "start": datetime(2026, 6, 8, 0, 0, 0, tzinfo=timezone.utc),
            "end": datetime(2026, 6, 10, 23, 59, 59, tzinfo=timezone.utc),
            "kind": "current-week",
        },
    )

    sql = captured.get("sql") or ""
    require("COALESCE(MAX(stats.player_name), stats.player_id)" not in sql, "Runtime player stats SQL must not reference non-aggregated stats.player_id inside COALESCE(MAX(...)).")
    require("MAX(stats.player_name) AS player_name" in sql, "Runtime player stats SQL should aggregate player_name directly.")
    require(result.get("player_name") == "regression-player", "Runtime player stats should still fall back to player_id in Python when SQL player_name is null.")


def validate_player_period_stats_refresh_and_read_model():
    db_path = build_player_period_stats_fixture()
    anchor = datetime(2026, 6, 10, 22, 0, 0, tzinfo=timezone.utc)
    try:
        payload = refresh_player_period_stats(
            db_path=db_path,
            now=anchor,
        )
        require(payload.get("status") == "ok", "Player period stats refresh should return ok.")
        require(payload.get("period_types") == ["weekly", "monthly", "yearly"], "Player period stats refresh should report the supported periods.")
        require_int(payload.get("total_rows"), "Player period stats refresh should report numeric total_rows.")

        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        weekly_row = connection.execute(
            """
            SELECT *
            FROM player_period_stats
            WHERE period_type = 'weekly'
              AND server_id = 'all-servers'
              AND player_id = 'regression-player'
            LIMIT 1
            """
        ).fetchone()
        monthly_row = connection.execute(
            """
            SELECT *
            FROM player_period_stats
            WHERE period_type = 'monthly'
              AND server_id = 'all-servers'
              AND player_id = 'regression-player'
            LIMIT 1
            """
        ).fetchone()
        yearly_row = connection.execute(
            """
            SELECT *
            FROM player_period_stats
            WHERE period_type = 'yearly'
              AND server_id = 'all-servers'
              AND player_id = 'regression-player'
            LIMIT 1
            """
        ).fetchone()
        server_row = connection.execute(
            """
            SELECT *
            FROM player_period_stats
            WHERE period_type = 'weekly'
              AND server_id = 'comunidad-hispana-01'
              AND player_id = 'regression-player'
            LIMIT 1
            """
        ).fetchone()
        connection.close()

        require(weekly_row is not None, "Player period stats should materialize a weekly all-servers row.")
        require(monthly_row is not None, "Player period stats should materialize a monthly all-servers row.")
        require(yearly_row is not None, "Player period stats should materialize a yearly all-servers row.")
        require(server_row is not None, "Player period stats should materialize server-scoped rows.")
        require(int(weekly_row["matches_considered"] or 0) == 6, "Weekly all-servers row should aggregate six closed matches.")
        require(int(weekly_row["kills"] or 0) == 42, "Weekly all-servers row should aggregate weekly kills.")
        require(int(weekly_row["deaths"] or 0) == 20, "Weekly all-servers row should aggregate weekly deaths.")
        require(int(weekly_row["teamkills"] or 0) == 1, "Weekly all-servers row should aggregate weekly teamkills.")
        require(int(weekly_row["ranking_position"] or 0) == 1, "Weekly all-servers row should persist ranking_position.")
        require(str(weekly_row["window_kind"]) == "current-week", "Weekly all-servers row should preserve the selected window kind.")
        require(str(monthly_row["window_kind"]) == "current-month", "Monthly all-servers row should preserve the selected window kind.")
        require(int(yearly_row["kills"] or 0) == 42, "Yearly row should exclude prior-year matches.")
        require(int(server_row["matches_considered"] or 0) == 3, "Server-scoped weekly row should aggregate only server-local matches.")

        read_model_result = get_rcon_materialized_player_stats(
            player_id="regression-player",
            server_id="all",
            timeframe="weekly",
            db_path=db_path,
        )
        require(
            (read_model_result.get("source") or {}).get("read_model") == "player-period-stats",
            "Player profile should prefer player_period_stats when populated.",
        )
        require(
            (read_model_result.get("source") or {}).get("fallback_used") is False,
            "Player profile should not report fallback when player_period_stats is used.",
        )
        require(read_model_result.get("matches_considered") == 6, "Player period stats read path should preserve weekly matches_considered.")
        require(read_model_result.get("kills") == 42, "Player period stats read path should preserve weekly kills.")
        require((read_model_result.get("weekly_ranking") or {}).get("ranking_position") == 1, "Player profile weekly ranking should come from the read model.")
        require((read_model_result.get("monthly_ranking") or {}).get("ranking_position") == 1, "Player profile monthly ranking should come from the read model.")
    finally:
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                pass


def validate_player_period_stats_fallbacks():
    db_path = build_player_period_stats_fixture()
    try:
        empty_result = get_rcon_materialized_player_stats(
            player_id="regression-player",
            server_id="all",
            timeframe="weekly",
            db_path=db_path,
        )
        require(
            (empty_result.get("source") or {}).get("fallback_used") is True,
            "Player profile should fall back to runtime when player_period_stats is empty.",
        )
        require(
            (empty_result.get("source") or {}).get("fallback_reason") == "player-period-stats-empty",
            "Player profile should expose an explicit empty read-model fallback reason.",
        )

        refresh_player_period_stats(
            db_path=db_path,
            now=datetime(2026, 6, 10, 22, 0, 0, tzinfo=timezone.utc),
        )
        connection = sqlite3.connect(db_path)
        with connection:
            connection.execute(
                """
                DELETE FROM player_period_stats
                WHERE period_type = 'monthly'
                  AND server_id = 'all-servers'
                  AND player_id = 'regression-player'
                """
            )
        connection.close()

        missing_row_result = get_rcon_materialized_player_stats(
            player_id="regression-player",
            server_id="all",
            timeframe="weekly",
            db_path=db_path,
        )
        require(
            (missing_row_result.get("source") or {}).get("fallback_used") is True,
            "Player profile should fall back when one required player period row is missing.",
        )
        require(
            (missing_row_result.get("source") or {}).get("fallback_reason") in {"player-period-stats-empty", "player-period-stats-player-missing"},
            "Player profile should expose a controlled fallback reason when the player period read model is incomplete.",
        )

        server_specific_missing_read_model_result = get_rcon_materialized_player_stats(
            player_id="yearly-only-player",
            server_id="comunidad-hispana-01",
            timeframe="weekly",
            db_path=db_path,
        )
        require(
            (server_specific_missing_read_model_result.get("source") or {}).get("fallback_used") is True,
            "Player profile should fall back when a server-specific weekly row is missing from player_period_stats.",
        )
        require(
            (server_specific_missing_read_model_result.get("source") or {}).get("fallback_reason") in {"player-period-stats-empty", "player-period-stats-player-missing"},
            "Server-specific missing player-period row should expose a controlled fallback reason.",
        )
        require(
            server_specific_missing_read_model_result.get("matches_considered") == 0,
            "Server-specific fallback without runtime rows in the requested window should return zero matches instead of throwing.",
        )
        require(
            server_specific_missing_read_model_result.get("kills") == 0,
            "Server-specific fallback without runtime rows should return zero kills instead of throwing.",
        )
        require(
            server_specific_missing_read_model_result.get("player_name") == "yearly-only-player",
            "Server-specific fallback without runtime rows should keep the controlled player_name fallback.",
        )

        original_read_model = player_search_stats._get_player_period_stats_read_model

        def fake_get_player_period_stats_read_model(**kwargs):
            return None, "player-period-stats-unavailable"

        player_search_stats._get_player_period_stats_read_model = fake_get_player_period_stats_read_model
        try:
            unavailable_result = get_rcon_materialized_player_stats(
                player_id="regression-player",
                server_id="all",
                timeframe="weekly",
                db_path=db_path,
            )
        finally:
            player_search_stats._get_player_period_stats_read_model = original_read_model

        require(
            (unavailable_result.get("source") or {}).get("fallback_used") is True,
            "Player profile should preserve runtime fallback when the read model is unavailable.",
        )
        require(
            (unavailable_result.get("source") or {}).get("fallback_reason") == "player-period-stats-unavailable",
            "Player profile should expose an explicit unavailable read-model fallback reason.",
        )
    finally:
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                pass


def validate_historical_runner_read_model_refresh_cycle():
    original_backend_writer_lock = historical_runner.backend_writer_lock
    original_build_writer_lock_holder = historical_runner.build_writer_lock_holder
    original_run_primary_rcon_capture = historical_runner._run_primary_rcon_capture
    original_resolve_classic_fallback_policy = historical_runner._resolve_classic_fallback_policy
    original_rcon_capture_has_new_useful_data = historical_runner._rcon_capture_has_new_useful_data
    original_generate_historical_snapshots = historical_runner.generate_historical_snapshots
    original_build_elo_mmr_rebuild_policy = historical_runner._build_elo_mmr_rebuild_policy
    original_rebuild_elo_mmr_models = historical_runner.rebuild_elo_mmr_models
    original_refresh_player_search_index = historical_runner.refresh_player_search_index
    original_refresh_player_period_stats = historical_runner.refresh_player_period_stats
    original_refresh_ranking_snapshots = historical_runner.refresh_ranking_snapshots
    original_maybe_run_database_maintenance = historical_runner._maybe_run_database_maintenance
    original_emit_json_log = historical_runner._emit_json_log

    @contextmanager
    def fake_backend_writer_lock(holder):
        yield

    captured_logs = []
    call_order = []

    historical_runner.backend_writer_lock = fake_backend_writer_lock
    historical_runner.build_writer_lock_holder = lambda label: label
    historical_runner._run_primary_rcon_capture = lambda: {
        "status": "ok",
        "targets": [{"target_key": "comunidad-hispana-01", "sample_inserted": True}],
        "totals": {
            "samples_inserted": 1,
            "admin_log_events_inserted": 0,
            "materialized_matches_inserted": 0,
        },
    }
    historical_runner._resolve_classic_fallback_policy = lambda **kwargs: (
        False,
        "validation-rcon-primary-cycle",
    )
    historical_runner._rcon_capture_has_new_useful_data = lambda payload: True
    historical_runner.generate_historical_snapshots = lambda **kwargs: {
        "status": "ok",
        "generated_at": "2026-06-09T08:00:00Z",
    }
    historical_runner._build_elo_mmr_rebuild_policy = lambda **kwargs: {
        "due": False,
        "policy": "validation-policy",
        "last_generated_at": None,
        "samples_since_last_rebuild": 1,
        "minutes_since_last_rebuild": None,
        "rebuild_interval_minutes": 60,
        "min_new_samples": 10,
    }
    historical_runner.rebuild_elo_mmr_models = lambda: {"status": "ok"}
    historical_runner._maybe_run_database_maintenance = lambda: {
        "status": "skipped",
        "reason": "validation-disabled",
    }
    historical_runner._emit_json_log = lambda payload: captured_logs.append(payload)

    def fake_refresh_player_search_index(**kwargs):
        call_order.append("player-search-index")
        return {"status": "ok", "total_rows": 3}

    def fake_refresh_player_period_stats(**kwargs):
        call_order.append("player-period-stats")
        return {"status": "ok", "total_rows": 9}

    def fake_refresh_ranking_snapshots(**kwargs):
        call_order.append("ranking-snapshots")
        return {
            "status": "ok",
            "totals": {"succeeded": 36, "failed": 0, "skipped_regeneration": 0},
        }

    historical_runner.refresh_player_search_index = fake_refresh_player_search_index
    historical_runner.refresh_player_period_stats = fake_refresh_player_period_stats
    historical_runner.refresh_ranking_snapshots = fake_refresh_ranking_snapshots

    try:
        result = historical_runner._run_refresh_with_retries(
            max_retries=0,
            retry_delay_seconds=0,
            server_slug=None,
            max_pages=None,
            page_size=None,
            run_number=1,
        )
        require(result.get("status") == "ok", "Historical runner should return ok when all periodic refresh steps succeed.")
        require(
            call_order == ["player-search-index", "player-period-stats", "ranking-snapshots"],
            "Historical runner should refresh player_search_index, then player_period_stats, then ranking_snapshots.",
        )
        require(
            (result.get("player_search_index_result") or {}).get("status") == "ok",
            "Historical runner should report player_search_index_result separately.",
        )
        require(
            (result.get("player_period_stats_result") or {}).get("status") == "ok",
            "Historical runner should report player_period_stats_result separately.",
        )
        require(
            (result.get("ranking_snapshot_result") or {}).get("status") == "ok",
            "Historical runner should keep reporting ranking_snapshot_result separately.",
        )
        require(
            any(
                log.get("event") == "player-search-index-refresh-started"
                for log in captured_logs
                if isinstance(log, dict)
            ),
            "Historical runner should log the player_search_index refresh start event.",
        )
        require(
            any(
                log.get("event") == "player-period-stats-refresh-started"
                for log in captured_logs
                if isinstance(log, dict)
            ),
            "Historical runner should log the player_period_stats refresh start event.",
        )

        call_order.clear()
        captured_logs.clear()

        def fake_refresh_player_search_index_failure(**kwargs):
            call_order.append("player-search-index")
            raise RuntimeError("forced player search refresh failure")

        historical_runner.refresh_player_search_index = fake_refresh_player_search_index_failure
        result = historical_runner._run_refresh_with_retries(
            max_retries=0,
            retry_delay_seconds=0,
            server_slug=None,
            max_pages=None,
            page_size=None,
            run_number=1,
        )
        require(
            result.get("status") == "partial",
            "Historical runner should return partial when one read-model refresh fails but the cycle continues.",
        )
        require(
            call_order == ["player-search-index", "player-period-stats", "ranking-snapshots"],
            "Historical runner should still attempt the remaining refresh steps after a player search read-model failure.",
        )
        require(
            (result.get("player_search_index_result") or {}).get("status") == "error",
            "Historical runner should expose the player_search_index refresh failure explicitly.",
        )
        require(
            (result.get("player_period_stats_result") or {}).get("status") == "ok",
            "Historical runner should continue refreshing player_period_stats after a player_search_index failure.",
        )
        require(
            (result.get("ranking_snapshot_result") or {}).get("status") == "ok",
            "Historical runner should continue refreshing ranking snapshots after a player_search_index failure.",
        )
        require(
            any(
                log.get("event") == "player-search-index-refresh-failed"
                for log in captured_logs
                if isinstance(log, dict)
            ),
            "Historical runner should emit a dedicated failure log for player_search_index refresh failures.",
        )
    finally:
        historical_runner.backend_writer_lock = original_backend_writer_lock
        historical_runner.build_writer_lock_holder = original_build_writer_lock_holder
        historical_runner._run_primary_rcon_capture = original_run_primary_rcon_capture
        historical_runner._resolve_classic_fallback_policy = original_resolve_classic_fallback_policy
        historical_runner._rcon_capture_has_new_useful_data = original_rcon_capture_has_new_useful_data
        historical_runner.generate_historical_snapshots = original_generate_historical_snapshots
        historical_runner._build_elo_mmr_rebuild_policy = original_build_elo_mmr_rebuild_policy
        historical_runner.rebuild_elo_mmr_models = original_rebuild_elo_mmr_models
        historical_runner.refresh_player_search_index = original_refresh_player_search_index
        historical_runner.refresh_player_period_stats = original_refresh_player_period_stats
        historical_runner.refresh_ranking_snapshots = original_refresh_ranking_snapshots
        historical_runner._maybe_run_database_maintenance = original_maybe_run_database_maintenance
        historical_runner._emit_json_log = original_emit_json_log


def cleanup_snapshot_fixture(db_path):
    connection = sqlite3.connect(db_path)
    with connection:
        connection.execute(
            """
            DELETE FROM ranking_snapshot_items
            WHERE snapshot_id IN (
                SELECT id
                FROM ranking_snapshots
                WHERE source = 'stats-validation-fixture'
            )
            """
        )
        connection.execute(
            "DELETE FROM ranking_snapshots WHERE source = 'stats-validation-fixture'"
        )
    connection.close()


def cleanup_generated_snapshot(snapshot_id):
    if not snapshot_id:
        return
    db_path = Path("backend/data/hll_vietnam_dev.sqlite3")
    connection = sqlite3.connect(db_path)
    with connection:
        connection.execute(
            "DELETE FROM ranking_snapshot_items WHERE snapshot_id = ?",
            (snapshot_id,),
        )
        connection.execute(
            "DELETE FROM ranking_snapshots WHERE id = ?",
            (snapshot_id,),
        )
    connection.close()


health_status, health_payload = read_payload("/health")
require(health_status == 200, "Route resolver /health should return 200.")
require(health_payload.get("status") == "ok", "/health payload should be ok.")

validate_postgres_ranking_snapshot_schema_path()
validate_ranking_snapshot_cli_defaults()
validate_ranking_snapshot_postgres_selection()
validate_ranking_snapshot_bulk_refresh()
validate_ranking_snapshot_bulk_partial_failure()
validate_postgres_player_search_index_schema_path()
validate_player_search_index_cli_defaults()
validate_player_search_index_refresh_and_search()
validate_player_search_index_fallbacks()
validate_postgres_player_period_stats_schema_path()
validate_player_period_stats_cli_defaults()
validate_fetch_player_stats_sql_contract()
validate_player_period_stats_refresh_and_read_model()
validate_player_period_stats_fallbacks()
validate_historical_runner_read_model_refresh_cycle()

kd_metric_sql, _, _ = ranking_leaderboards._resolve_metric_sql("kd_ratio")
require(
    "AS REAL" not in kd_metric_sql,
    "kd_ratio SQL should not keep SQLite REAL casting in the shared query path.",
)
require(
    "AS NUMERIC" in kd_metric_sql,
    "kd_ratio SQL should cast to NUMERIC for PostgreSQL-compatible rounding.",
)

kpm_metric_sql, _, _ = ranking_leaderboards._resolve_metric_sql("kills_per_match")
require(
    "AS REAL" not in kpm_metric_sql,
    "kills_per_match SQL should not keep SQLite REAL casting in the shared query path.",
)
require(
    "AS NUMERIC" in kpm_metric_sql,
    "kills_per_match SQL should cast to NUMERIC for PostgreSQL-compatible rounding.",
)

search_status, search_payload = read_payload("/api/stats/players/search?q=regression-check&limit=5")
require(search_status == 200, "Stats player search should return 200 for a valid query.")
search_data = search_payload.get("data") or {}
require(search_payload.get("status") == "ok", "Stats player search should return ok status.")
require(search_data.get("query") == "regression-check", "Stats player search should preserve query.")
require(search_data.get("server_id"), "Stats player search should include server_id.")
require(isinstance(search_data.get("source"), dict), "Stats player search should expose source metadata.")
require((search_data.get("source") or {}).get("read_model") in {"player-search-index", "rcon-materialized-admin-log-player-stats"}, "Stats player search should expose a recognized read model.")
require(isinstance(search_data.get("items"), list), "Stats player search items must be a list.")

for item in search_data["items"]:
    if item is None:
        continue
    require_str(item.get("player_id"), "Search result must include player_id.")
    require_str(item.get("player_name"), "Search result should include player_name.")
    require_int(item.get("matches_considered"), "Search result matches_considered should be int.")

missing_query_status, missing_query_payload = read_payload("/api/stats/players/search")
require(missing_query_status == 400, "Stats search without q should return 400.")
require(missing_query_payload is not None, "Search validation must return a payload.")

invalid_search_limit_status, _ = read_payload("/api/stats/players/search?q=regression-check&limit=0")
require(invalid_search_limit_status == 400, "Stats search with limit=0 should return 400.")

profile_status, profile_payload = read_payload("/api/stats/players/regression-player?timeframe=weekly")
require(profile_status == 200, "Stats player profile should return 200 for a valid player lookup.")
profile_data = profile_payload.get("data") or {}
require(profile_payload.get("status") == "ok", "Stats player profile should return ok status.")
require(profile_data.get("player_id") == "regression-player", "Stats player profile should preserve player_id.")
require(profile_data.get("timeframe") == "weekly", "Stats player profile should preserve timeframe.")
require(profile_data.get("server_id"), "Stats player profile should include server_id.")
require_int(profile_data.get("matches_considered"), "Profile matches_considered should be int.")
require(isinstance(profile_data.get("source"), dict), "Profile source metadata should be present.")
require(isinstance(profile_data.get("weekly_ranking"), (dict, type(None))), "Profile weekly_ranking should be dict or null.")
require(isinstance(profile_data.get("monthly_ranking"), (dict, type(None))), "Profile monthly_ranking should be dict or null.")

invalid_timeframe_status, _ = read_payload("/api/stats/players/regression-player?timeframe=seasonal")
require(invalid_timeframe_status == 400, "Invalid player timeframe should return 400.")

current_year = datetime.now(timezone.utc).year
annual_status, annual_payload = read_payload(
    f"/api/stats/rankings/annual?year={current_year}&server_id=all&metric=kills&limit=20"
)
require(annual_status == 200, "Annual ranking should return 200 for metric=kills.")
annual_data = annual_payload.get("data") or {}
require(annual_payload.get("status") == "ok", "Annual ranking should return ok status.")
require_int(annual_data.get("year"), "Annual payload should include numeric year.")
require_int(annual_data.get("limit"), "Annual payload should include limit.")
require_int(annual_data.get("requested_limit"), "Annual payload should include requested_limit.")
require_int(annual_data.get("effective_limit"), "Annual payload should include effective_limit.")
require_int(annual_data.get("snapshot_limit"), "Annual payload should include snapshot_limit.")
require_int(annual_data.get("item_count"), "Annual payload should include item_count.")
require(annual_data.get("snapshot_status") in {"ready", "missing"}, "Annual snapshot_status should be ready or missing.")
require(isinstance(annual_data.get("items"), list), "Annual ranking items should be list.")
require(isinstance(annual_data.get("server_id"), str), "Annual payload should include server_id.")
require(annual_data.get("metric") == "kills", "Annual payload should return kills metric.")

for item in annual_data.get("items", []):
    if item is None:
        continue
    require_int(item.get("ranking_position"), "Annual item ranking_position should be int.")
    require_str(item.get("player_id"), "Annual item should include player_id.")
    require_str(item.get("player_name"), "Annual item should include player_name.")
    require_int(item.get("matches_considered"), "Annual item matches_considered should be int.")

low_limit_status, low_limit_payload = read_payload(
    f"/api/stats/rankings/annual?year={current_year}&server_id=all&metric=kills&limit=3"
)
require(low_limit_status == 200, "Annual ranking low-limit requests should return 200.")
low_limit_value = (low_limit_payload.get("data") or {}).get("limit")
require(isinstance(low_limit_value, int) and 1 <= low_limit_value <= 3, "Annual low-limit normalization changed unexpectedly.")

high_limit_status, _ = read_payload(
    f"/api/stats/rankings/annual?year={current_year}&server_id=all&metric=kills&limit=101"
)
require(high_limit_status == 400, "Annual ranking with limit=101 should return 400.")

unsupported_metric_status, _ = read_payload(
    f"/api/stats/rankings/annual?year={current_year}&server_id=all&metric=deaths&limit=20"
)
require(unsupported_metric_status == 400, "Annual ranking with unsupported metric should return 400.")

missing_year_status, _ = read_payload("/api/stats/rankings/annual?year=2999&server_id=all&metric=kills&limit=20")
require(missing_year_status == 200, "Future year annual ranking should still return 200.")

weekly_ranking_status, weekly_ranking_payload = read_payload(
    "/api/ranking?timeframe=weekly&server_id=all&metric=kills&limit=20"
)
require(weekly_ranking_status == 200, "Global ranking weekly route should return 200.")
weekly_ranking_data = weekly_ranking_payload.get("data") or {}
require(weekly_ranking_payload.get("status") == "ok", "Global ranking weekly payload should return ok status.")
require(weekly_ranking_data.get("page_kind") == "global-ranking", "Global ranking should expose page_kind.")
require(weekly_ranking_data.get("timeframe") == "weekly", "Global ranking weekly timeframe should be preserved.")
require(weekly_ranking_data.get("metric") == "kills", "Global ranking weekly metric should be kills.")
require(weekly_ranking_data.get("snapshot_status") in {"ready", "missing"}, "Global ranking weekly should expose ready/missing snapshot status.")
require(isinstance(weekly_ranking_data.get("items"), list), "Global ranking weekly items must be list.")
require(isinstance(weekly_ranking_data.get("source"), dict), "Global ranking weekly should expose source metadata.")
require("fallback_used" in weekly_ranking_data, "Global ranking weekly should expose fallback_used.")
require("freshness" in weekly_ranking_data, "Global ranking weekly should expose freshness.")
require("generated_at" in weekly_ranking_data, "Global ranking weekly should expose generated_at.")
require("window_start" in weekly_ranking_data, "Global ranking weekly should expose window_start.")
require("window_end" in weekly_ranking_data, "Global ranking weekly should expose window_end.")

weekly_deaths_status, weekly_deaths_payload = read_payload(
    "/api/ranking?timeframe=weekly&server_id=all&metric=deaths&limit=20"
)
require(weekly_deaths_status == 200, "Global ranking weekly deaths route should return 200.")
require((weekly_deaths_payload.get("data") or {}).get("metric") == "deaths", "Global ranking weekly deaths metric should be preserved.")

weekly_teamkills_status, weekly_teamkills_payload = read_payload(
    "/api/ranking?timeframe=weekly&server_id=all&metric=teamkills&limit=20"
)
require(weekly_teamkills_status == 200, "Global ranking weekly teamkills route should return 200.")
require((weekly_teamkills_payload.get("data") or {}).get("metric") == "teamkills", "Global ranking weekly teamkills metric should be preserved.")

weekly_matches_status, weekly_matches_payload = read_payload(
    "/api/ranking?timeframe=weekly&server_id=all&metric=matches_considered&limit=20"
)
require(weekly_matches_status == 200, "Global ranking weekly matches_considered route should return 200.")
require((weekly_matches_payload.get("data") or {}).get("metric") == "matches_considered", "Global ranking weekly matches_considered metric should be preserved.")

weekly_kd_status, weekly_kd_payload = read_payload(
    "/api/ranking?timeframe=weekly&server_id=all&metric=kd_ratio&limit=20"
)
require(weekly_kd_status == 200, "Global ranking weekly kd_ratio route should return 200.")
require((weekly_kd_payload.get("data") or {}).get("metric") == "kd_ratio", "Global ranking weekly kd_ratio metric should be preserved.")

weekly_kpm_status, weekly_kpm_payload = read_payload(
    "/api/ranking?timeframe=weekly&server_id=all&metric=kills_per_match&limit=20"
)
require(weekly_kpm_status == 200, "Global ranking weekly kills_per_match route should return 200.")
require((weekly_kpm_payload.get("data") or {}).get("metric") == "kills_per_match", "Global ranking weekly kills_per_match metric should be preserved.")

monthly_ranking_status, monthly_ranking_payload = read_payload(
    "/api/ranking?timeframe=monthly&server_id=comunidad-hispana-01&metric=kills&limit=20"
)
require(monthly_ranking_status == 200, "Global ranking monthly route should return 200.")
monthly_ranking_data = monthly_ranking_payload.get("data") or {}
require(monthly_ranking_data.get("timeframe") == "monthly", "Global ranking monthly timeframe should be preserved.")
require(monthly_ranking_data.get("server_id") == "comunidad-hispana-01", "Global ranking monthly should preserve server_id.")
require("fallback_used" in monthly_ranking_data, "Global ranking monthly should expose fallback_used.")
require("freshness" in monthly_ranking_data, "Global ranking monthly should expose freshness.")
require("generated_at" in monthly_ranking_data, "Global ranking monthly should expose generated_at.")
require("window_start" in monthly_ranking_data, "Global ranking monthly should expose window_start.")
require("window_end" in monthly_ranking_data, "Global ranking monthly should expose window_end.")

monthly_kd_status, monthly_kd_payload = read_payload(
    "/api/ranking?timeframe=monthly&server_id=comunidad-hispana-01&metric=kd_ratio&limit=20"
)
require(monthly_kd_status == 200, "Global ranking monthly kd_ratio route should return 200.")
require((monthly_kd_payload.get("data") or {}).get("metric") == "kd_ratio", "Global ranking monthly kd_ratio metric should be preserved.")

monthly_kpm_status, monthly_kpm_payload = read_payload(
    "/api/ranking?timeframe=monthly&server_id=comunidad-hispana-01&metric=kills_per_match&limit=20"
)
require(monthly_kpm_status == 200, "Global ranking monthly kills_per_match route should return 200.")
require((monthly_kpm_payload.get("data") or {}).get("metric") == "kills_per_match", "Global ranking monthly kills_per_match metric should be preserved.")

annual_ranking_status, annual_ranking_payload = read_payload(
    f"/api/ranking?timeframe=annual&year={current_year}&server_id=all&metric=kills&limit=20"
)
require(annual_ranking_status == 200, "Global ranking annual route should return 200.")
annual_ranking_data = annual_ranking_payload.get("data") or {}
require(annual_ranking_data.get("timeframe") == "annual", "Global ranking annual timeframe should be preserved.")
require(annual_ranking_data.get("metric") == "kills", "Global ranking annual metric should be kills.")
require(annual_ranking_data.get("snapshot_status") in {"ready", "missing"}, "Global ranking annual snapshot_status should be ready or missing.")
require(isinstance(annual_ranking_data.get("items"), list), "Global ranking annual items must be list.")
require("generated_at" in annual_ranking_data, "Global ranking annual should expose generated_at.")
require("window_start" in annual_ranking_data, "Global ranking annual should expose window_start.")
require("window_end" in annual_ranking_data, "Global ranking annual should expose window_end.")

annual_2026_status, annual_2026_payload = read_payload(
    "/api/ranking?timeframe=annual&year=2026&server_id=all&metric=kills&limit=20"
)
require(annual_2026_status == 200, "Global ranking annual 2026 route should return 200.")
require(
    ((annual_2026_payload.get("data") or {}).get("snapshot_status") in {"ready", "missing"}),
    "Global ranking annual 2026 should expose ready/missing snapshot status.",
)

for ranking_payload in [
    weekly_ranking_payload,
    weekly_deaths_payload,
    weekly_teamkills_payload,
    weekly_matches_payload,
    weekly_kd_payload,
    weekly_kpm_payload,
    monthly_kd_payload,
    monthly_kpm_payload,
    annual_ranking_payload,
]:
    ranking_data = ranking_payload.get("data") or {}
    for item in ranking_data.get("items", []):
        if item is None:
            continue
        require_int(item.get("ranking_position"), "Global ranking item ranking_position should be int.")
        require_str(item.get("player_id"), "Global ranking item should include player_id.")
        require_str(item.get("player_name"), "Global ranking item should include player_name.")
        require_number(item.get("metric_value"), "Global ranking item metric_value should be numeric.")
        require_int(item.get("matches_considered"), "Global ranking item matches_considered should be int.")
        require_number(item.get("kd_ratio"), "Global ranking item kd_ratio should be numeric.")
        require_number(item.get("kills_per_match"), "Global ranking item kills_per_match should be numeric.")

low_limit_ranking_status, low_limit_ranking_payload = read_payload(
    "/api/ranking?timeframe=weekly&server_id=all&metric=kills&limit=3"
)
require(low_limit_ranking_status == 200, "Global ranking with low limit should return 200.")
require((low_limit_ranking_payload.get("data") or {}).get("limit") == 3, "Global ranking low-limit response should preserve limit 3.")

high_limit_ranking_status, _ = read_payload(
    "/api/ranking?timeframe=weekly&server_id=all&metric=kills&limit=101"
)
require(high_limit_ranking_status == 400, "Global ranking with limit=101 should return 400.")

unsupported_metric_ranking_status, _ = read_payload(
    "/api/ranking?timeframe=weekly&server_id=all&metric=assists&limit=20"
)
require(unsupported_metric_ranking_status == 400, "Global ranking with unsupported metric should return 400.")

annual_unsupported_metric_status, annual_unsupported_metric_payload = read_payload(
    f"/api/ranking?timeframe=annual&year={current_year}&server_id=all&metric=deaths&limit=20"
)
require(annual_unsupported_metric_status == 400, "Global ranking annual with unsupported snapshot metric should return 400.")
require(
    "annual" in str(
        annual_unsupported_metric_payload.get("message")
        or annual_unsupported_metric_payload.get("error")
        or ""
    ).lower(),
    "Annual unsupported metric error should mention annual snapshot support.",
)

unsupported_timeframe_ranking_status, _ = read_payload(
    "/api/ranking?timeframe=seasonal&server_id=all&metric=kills&limit=20"
)
require(unsupported_timeframe_ranking_status == 400, "Global ranking with unsupported timeframe should return 400.")

missing_year_ranking_status, _ = read_payload(
    "/api/ranking?timeframe=annual&server_id=all&metric=kills&limit=20"
)
require(missing_year_ranking_status == 400, "Global ranking annual requests without year should return 400.")

generated_snapshot_id = None
try:
    generated_snapshot = generate_ranking_snapshot(
        timeframe="weekly",
        server_key="all",
        metric="kills",
        limit=20,
        now=datetime(2026, 5, 20, 12, 0, 0, tzinfo=timezone.utc),
        db_path=Path("backend/data/hll_vietnam_dev.sqlite3"),
    )
    generated_snapshot_record = generated_snapshot.get("snapshot") or {}
    generated_snapshot_id = generated_snapshot_record.get("id")
    require(generated_snapshot.get("status") == "ok", "Weekly ranking snapshot generation should return ok.")
    require(generated_snapshot_id, "Generated weekly ranking snapshot should expose snapshot id.")
    require(
        generated_snapshot_record.get("timeframe") == "weekly",
        "Generated weekly ranking snapshot should preserve timeframe.",
    )
    require(
        generated_snapshot_record.get("metric") == "kills",
        "Generated weekly ranking snapshot should preserve metric.",
    )
    latest_generated_snapshot = get_latest_ranking_snapshot(
        server_key="all",
        timeframe="weekly",
        metric="kills",
        limit=20,
        db_path=Path("backend/data/hll_vietnam_dev.sqlite3"),
    )
    require(
        latest_generated_snapshot.get("snapshot_status") == "ready",
        "Generated weekly ranking snapshot should be readable as ready.",
    )
    require(
        latest_generated_snapshot.get("generated_at"),
        "Generated weekly ranking snapshot should expose generated_at.",
    )
    generated_route_status, generated_route_payload = read_payload(
        "/api/ranking?timeframe=weekly&server_id=all&metric=kills&limit=20"
    )
    require(generated_route_status == 200, "Generated weekly ranking route should return 200.")
    generated_route_data = generated_route_payload.get("data") or {}
    require(
        generated_route_data.get("snapshot_status") == "ready",
        "Generated weekly ranking route should return snapshot_status=ready.",
    )
    require(
        generated_route_data.get("fallback_used") is False,
        "Generated weekly ranking route should not use runtime fallback.",
    )
    require(
        isinstance(generated_route_data.get("items"), list),
        "Generated weekly ranking route should return items list.",
    )

    generated_fallback_status, generated_fallback_payload = read_payload(
        "/api/ranking?timeframe=weekly&server_id=all&metric=deaths&limit=20"
    )
    require(generated_fallback_status == 200, "Generated validation fallback route should return 200.")
    generated_fallback_data = generated_fallback_payload.get("data") or {}
    require(
        generated_fallback_data.get("fallback_used") is True,
        "Missing weekly deaths snapshot should still use runtime fallback when enabled.",
    )
finally:
    cleanup_generated_snapshot(generated_snapshot_id)

fixture_db_path = build_snapshot_fixture()
try:
    fixture_weekly_status, fixture_weekly_payload = read_payload(
        "/api/ranking?timeframe=weekly&server_id=all&metric=kills&limit=20"
    )
    require(fixture_weekly_status == 200, "Fixture weekly ranking should return 200.")
    fixture_weekly_data = fixture_weekly_payload.get("data") or {}
    require(fixture_weekly_data.get("snapshot_status") == "ready", "Fixture weekly ranking should serve ready snapshot.")
    require(fixture_weekly_data.get("fallback_used") is False, "Fixture weekly ranking should not use fallback.")
    require((fixture_weekly_data.get("source") or {}).get("read_model") == "ranking-snapshot", "Fixture weekly ranking should identify snapshot read model.")
    require(fixture_weekly_data.get("generated_at"), "Fixture weekly ranking should expose generated_at.")

    fixture_monthly_status, fixture_monthly_payload = read_payload(
        "/api/ranking?timeframe=monthly&server_id=comunidad-hispana-01&metric=kills_per_match&limit=20"
    )
    require(fixture_monthly_status == 200, "Fixture monthly ranking should return 200.")
    fixture_monthly_data = fixture_monthly_payload.get("data") or {}
    require(fixture_monthly_data.get("snapshot_status") == "ready", "Fixture monthly ranking should serve ready snapshot.")
    require(fixture_monthly_data.get("fallback_used") is False, "Fixture monthly ranking should not use fallback.")
    require((fixture_monthly_data.get("source") or {}).get("read_model") == "ranking-snapshot", "Fixture monthly ranking should identify snapshot read model.")

    os.environ["HLL_BACKEND_RANKING_RUNTIME_FALLBACK_ENABLED"] = "false"
    missing_snapshot_status, missing_snapshot_payload = read_payload(
        "/api/ranking?timeframe=weekly&server_id=all&metric=deaths&limit=20"
    )
    require(missing_snapshot_status == 200, "Missing snapshot weekly ranking should return 200.")
    missing_snapshot_data = missing_snapshot_payload.get("data") or {}
    require(missing_snapshot_data.get("snapshot_status") == "missing", "Missing snapshot weekly ranking should expose missing snapshot_status.")
    require(missing_snapshot_data.get("fallback_used") is False, "Missing snapshot weekly ranking should not use runtime fallback when disabled.")
    require(isinstance(missing_snapshot_data.get("items"), list) and len(missing_snapshot_data.get("items")) == 0, "Missing snapshot weekly ranking should return empty items when fallback is disabled.")
finally:
    os.environ["HLL_BACKEND_RANKING_RUNTIME_FALLBACK_ENABLED"] = "true"
    cleanup_snapshot_fixture(fixture_db_path)

print(json.dumps({
    "checked": [
        "health",
        "stats-player-search",
        "stats-player-profile",
        "stats-annual-ranking",
        "global-ranking",
        "postgres-ranking-derived-metric-sql",
        "postgres-ranking-schema-path",
        "ranking-snapshot-cli-postgres-default",
        "ranking-snapshot-bulk-cli",
        "ranking-snapshot-postgres-selection",
        "ranking-snapshot-bulk-refresh",
        "ranking-snapshot-bulk-partial-failure",
        "ranking-snapshot-generator",
        "ranking-snapshot-ready",
        "ranking-snapshot-missing",
        "player-search-index",
        "player-period-stats",
        "historical-runner-player-read-model-refresh",
    ],
    "annual_snapshot_status": annual_data.get("snapshot_status"),
    "global_ranking_annual_snapshot_status": annual_ranking_data.get("snapshot_status"),
    "search_items_count": len(search_data.get("items") or []),
    "profile_matches_considered": profile_data.get("matches_considered"),
    "profile_read_model_source": (profile_data.get("source") or {}).get("read_model"),
}))
'@

$backendContractCheck | python -
Assert-LastExitCode "Stats route-contract validation failed."

$backendBaseUrl = "http://127.0.0.1:8000"
$backendAvailable = $false

try {
    $healthPayload = Invoke-RestMethod -Uri "$backendBaseUrl/health" -TimeoutSec 5
    if ($healthPayload.status -ne "ok") {
        throw "Live backend health payload did not return status=ok."
    }
    $backendAvailable = $true
    Write-Host "Live backend available at $backendBaseUrl"
} catch {
    Write-Warning "Live backend unavailable at $backendBaseUrl. Route-contract checks passed via local Python imports."
    Write-Host "Next steps: start the backend, then rerun scripts/run-stats-validation.ps1 to verify live HTTP responses."
}

if ($backendAvailable) {
    $currentYear = (Get-Date).ToUniversalTime().Year
    $searchPayload = Invoke-RestMethod -Uri "$backendBaseUrl/api/stats/players/search?q=regression-check&limit=5" -TimeoutSec 5
    if ($searchPayload.status -ne "ok") {
        throw "Live stats search should return status=ok."
    }
    if (-not ($searchPayload.data -and ($searchPayload.data.items -is [array]))) {
        throw "Live stats search payload must include item list."
    }

    $profilePayload = Invoke-RestMethod -Uri "$backendBaseUrl/api/stats/players/regression-player?timeframe=weekly" -TimeoutSec 5
    if ($profilePayload.status -ne "ok") {
        throw "Live stats profile should return status=ok."
    }

    $annualPayload = Invoke-RestMethod -Uri "$backendBaseUrl/api/stats/rankings/annual?year=$currentYear&server_id=all&metric=kills&limit=20" -TimeoutSec 5
    if ($annualPayload.status -ne "ok") {
        throw "Live annual ranking should return status=ok."
    }
    if (-not ($annualPayload.data.snapshot_status -in @("ready", "missing"))) {
        throw "Live annual ranking should expose ready/missing snapshot status."
    }

    $unsupportedMetricStatus = Get-HttpStatusCode -Url "$backendBaseUrl/api/stats/rankings/annual?year=$currentYear&server_id=all&metric=deaths&limit=20"
    if ($unsupportedMetricStatus -ne 400) {
        throw "Live annual ranking with unsupported metric should return HTTP 400."
    }

    $rankingWeeklyPayload = Invoke-RestMethod -Uri "$backendBaseUrl/api/ranking?timeframe=weekly&server_id=all&metric=kills&limit=20" -TimeoutSec 5
    if ($rankingWeeklyPayload.status -ne "ok") {
        throw "Live global ranking weekly route should return status=ok."
    }

    $rankingWeeklyDeathsPayload = Invoke-RestMethod -Uri "$backendBaseUrl/api/ranking?timeframe=weekly&server_id=all&metric=deaths&limit=20" -TimeoutSec 5
    if ($rankingWeeklyDeathsPayload.status -ne "ok") {
        throw "Live global ranking weekly deaths route should return status=ok."
    }

    $rankingWeeklyKdPayload = Invoke-RestMethod -Uri "$backendBaseUrl/api/ranking?timeframe=weekly&server_id=all&metric=kd_ratio&limit=20" -TimeoutSec 5
    if ($rankingWeeklyKdPayload.status -ne "ok") {
        throw "Live global ranking weekly kd_ratio route should return status=ok."
    }

    $rankingMonthlyKpmPayload = Invoke-RestMethod -Uri "$backendBaseUrl/api/ranking?timeframe=monthly&server_id=all&metric=kills_per_match&limit=20" -TimeoutSec 5
    if ($rankingMonthlyKpmPayload.status -ne "ok") {
        throw "Live global ranking monthly kills_per_match route should return status=ok."
    }

    $rankingAnnualPayload = Invoke-RestMethod -Uri "$backendBaseUrl/api/ranking?timeframe=annual&year=$currentYear&server_id=all&metric=kills&limit=20" -TimeoutSec 5
    if ($rankingAnnualPayload.status -ne "ok") {
        throw "Live global ranking annual route should return status=ok."
    }
    if (-not ($rankingAnnualPayload.data.snapshot_status -in @("ready", "missing"))) {
        throw "Live global ranking annual should expose ready/missing snapshot status."
    }

    $rankingSupportedDeathsStatus = Get-HttpStatusCode -Url "$backendBaseUrl/api/ranking?timeframe=weekly&server_id=all&metric=deaths&limit=20"
    if ($rankingSupportedDeathsStatus -ne 200) {
        throw "Live global ranking weekly deaths should return HTTP 200."
    }

    $rankingInvalidMetricStatus = Get-HttpStatusCode -Url "$backendBaseUrl/api/ranking?timeframe=weekly&server_id=all&metric=assists&limit=20"
    if ($rankingInvalidMetricStatus -ne 400) {
        throw "Live global ranking with invalid metric should return HTTP 400."
    }

    $rankingUnsupportedAnnualMetricStatus = Get-HttpStatusCode -Url "$backendBaseUrl/api/ranking?timeframe=annual&year=$currentYear&server_id=all&metric=deaths&limit=20"
    if ($rankingUnsupportedAnnualMetricStatus -ne 400) {
        throw "Live global ranking annual with unsupported snapshot metric should return HTTP 400."
    }

    $rankingUnsupportedMetricStatus = Get-HttpStatusCode -Url "$backendBaseUrl/api/ranking?timeframe=weekly&server_id=all&metric=assists&limit=20"
    if ($rankingUnsupportedMetricStatus -ne 400) {
        throw "Live global ranking with unsupported metric should return HTTP 400."
    }

    Write-Host "Live HTTP checks passed for Stats endpoints."
}

Write-Host "Stats regression validation passed."
