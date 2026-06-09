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
import app.rcon_historical_leaderboards as ranking_leaderboards

initialize_ranking_snapshot_storage = ranking_leaderboards.initialize_ranking_snapshot_storage
generate_ranking_snapshot = ranking_leaderboards.generate_ranking_snapshot
get_latest_ranking_snapshot = ranking_leaderboards.get_latest_ranking_snapshot
refresh_ranking_snapshots = ranking_leaderboards.refresh_ranking_snapshots


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
],
    "annual_snapshot_status": annual_data.get("snapshot_status"),
    "global_ranking_annual_snapshot_status": annual_ranking_data.get("snapshot_status"),
    "search_items_count": len(search_data.get("items") or []),
    "profile_matches_considered": profile_data.get("matches_considered"),
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
