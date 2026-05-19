$ErrorActionPreference = "Stop"

Write-Host "HLL Vietnam RCON data pipeline validation"

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Command
    )

    Write-Host ""
    Write-Host "== $Name =="
    & $Command
}

function Test-PythonModule {
    param([Parameter(Mandatory = $true)][string]$ModuleName)

    $check = "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('$ModuleName') else 1)"
    python -c $check *> $null
    return $LASTEXITCODE -eq 0
}

Invoke-Step "Compile backend application modules" {
    python -m compileall backend/app
}

$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ($previousPythonPath) { "backend;$previousPythonPath" } else { "backend" }

try {
    if (Test-PythonModule "pytest") {
        Invoke-Step "Run RCON parser, storage and materialization tests with pytest" {
            python -m pytest `
                backend/tests/test_rcon_admin_log_parser.py `
                backend/tests/test_rcon_admin_log_storage.py `
                backend/tests/test_rcon_materialization_pipeline.py `
                backend/tests/test_scoreboard_match_links.py
        }
    }
    else {
        Write-Host ""
        Write-Host "pytest is not installed; running offline fallback checks for RCON parser/storage and unittest suites."

        Invoke-Step "Run RCON parser and storage fallback checks" {
            $fallbackChecks = @'
from pathlib import Path
import tempfile
from backend.tests import test_rcon_admin_log_parser as parser_tests
from backend.tests import test_rcon_admin_log_storage as storage_tests

parser_tests.test_parse_match_start()
parser_tests.test_parse_match_end()
parser_tests.test_parse_kill()
parser_tests.test_parse_team_switch()
parser_tests.test_parse_connected()
parser_tests.test_parse_disconnected()
parser_tests.test_parse_chat()
parser_tests.test_parse_kick()
parser_tests.test_parse_message_profile()
parser_tests.test_parse_player_profile_snapshot_spanish_sections()
parser_tests.test_non_profile_message_does_not_parse_as_profile_snapshot()

with tempfile.TemporaryDirectory() as tmp:
    storage_tests.test_initialize_rcon_admin_log_storage_creates_event_table(Path(tmp))
with tempfile.TemporaryDirectory() as tmp:
    storage_tests.test_persist_rcon_admin_log_entries_inserts_then_reports_duplicates(Path(tmp))
with tempfile.TemporaryDirectory() as tmp:
    storage_tests.test_profile_message_snapshots_are_materialized_and_deduped(Path(tmp))
with tempfile.TemporaryDirectory() as tmp:
    storage_tests.test_non_profile_messages_do_not_create_profile_snapshots(Path(tmp))
with tempfile.TemporaryDirectory() as tmp:
    storage_tests.test_canonical_message_dedupes_changing_relative_prefixes(Path(tmp))
with tempfile.TemporaryDirectory() as tmp:
    storage_tests.test_list_rcon_admin_log_event_counts_groups_by_target_and_event_type(Path(tmp))

print("RCON parser and storage fallback checks passed.")
'@
            $fallbackChecks | python -
        }

        Invoke-Step "Run RCON materialization unittest suite" {
            python -m unittest backend.tests.test_rcon_materialization_pipeline
        }

        Invoke-Step "Run RCON scoreboard link unittest suite" {
            python -m unittest backend.tests.test_scoreboard_match_links
        }
    }
}
finally {
    $env:PYTHONPATH = $previousPythonPath
}

Invoke-Step "Optional Docker backend smoke check" {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Host "Skipping Docker smoke check: docker command is not available."
        return
    }

    docker compose ps --services --filter "status=running" *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Skipping Docker smoke check: docker compose is not available or no compose project is active."
        return
    }

    $runningServices = docker compose ps --services --filter "status=running"
    if ($runningServices -notcontains "backend") {
        Write-Host "Skipping backend endpoint smoke check: backend service is not running."
        return
    }

    $health = Invoke-WebRequest "http://localhost:8000/health" -UseBasicParsing
    if ($health.StatusCode -lt 200 -or $health.StatusCode -ge 300) {
        throw "Backend health smoke check failed with status $($health.StatusCode)."
    }
    Write-Host "Backend health smoke check passed."
}

Write-Host ""
Write-Host "Skipping real RCON checks: this validation is designed to run without RCON credentials."
Write-Host "RCON data pipeline validation passed."
exit 0
