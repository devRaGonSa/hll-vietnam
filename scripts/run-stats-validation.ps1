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

function Assert-Contains {
    param(
        [string] $Content,
        [string] $Pattern,
        [string] $Message
    )

    if ($Content -notmatch [regex]::Escape($Pattern)) {
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

$statsHtml = Get-Content -Raw "frontend/stats.html"
$statsJs = Get-Content -Raw "frontend/assets/js/stats.js"

Assert-Contains $statsHtml 'id="stats-search-form"' `
    "Stats page no longer exposes the player search form."
Assert-Contains $statsHtml 'id="stats-profile-panel"' `
    "Stats page no longer exposes the player profile panel."
Assert-Contains $statsHtml 'id="stats-annual-form"' `
    "Stats page no longer exposes the annual ranking form."
Assert-Contains $statsHtml './assets/js/stats.js' `
    "Stats page no longer loads the Stats JavaScript asset."
Assert-Contains $statsJs "/api/stats/players/search" `
    "Stats frontend no longer targets the player search endpoint."
Assert-Contains $statsJs "/api/stats/rankings/annual" `
    "Stats frontend no longer targets the annual ranking endpoint."
Assert-Contains $statsJs "/api/stats/players/" `
    "Stats frontend no longer targets the player profile endpoint."
Assert-Contains $statsJs "Backend no disponible" `
    "Stats frontend no longer exposes the controlled backend-unavailable messaging."

$backendContractCheck = @'
import json
import sys
from datetime import datetime, timezone

sys.path.insert(0, "backend")

from app.routes import resolve_get_payload


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def read_payload(path):
    status, payload = resolve_get_payload(path)
    require(status is not None, f"{path} did not resolve")
    return int(status), payload


health_status, health_payload = read_payload("/health")
require(health_status == 200, "Route resolver /health no longer returns 200.")
require(health_payload.get("status") == "ok", "Route resolver /health no longer returns ok status.")

search_status, search_payload = read_payload("/api/stats/players/search?q=regression-check&limit=5")
require(search_status == 200, "Stats player search should return 200 for a valid query.")
search_data = search_payload.get("data") or {}
require(search_payload.get("status") == "ok", "Stats player search payload no longer returns ok status.")
require(search_data.get("query") == "regression-check", "Stats player search no longer echoes query.")
require(search_data.get("server_id") == "all-servers", "Stats player search no longer defaults server scope to all-servers.")
require(isinstance(search_data.get("items"), list), "Stats player search items must remain a list.")

missing_query_status, missing_query_payload = read_payload("/api/stats/players/search")
require(missing_query_status == 400, "Stats player search without q must return 400.")
require("required" in str(missing_query_payload.get("message", "")).lower(), "Missing-q error message changed unexpectedly.")

invalid_search_limit_status, _ = read_payload("/api/stats/players/search?q=regression-check&limit=0")
require(invalid_search_limit_status == 400, "Stats player search with limit=0 must return 400.")

profile_status, profile_payload = read_payload("/api/stats/players/regression-player?timeframe=weekly")
require(profile_status == 200, "Stats player profile should return 200 for a valid player lookup.")
profile_data = profile_payload.get("data") or {}
require(profile_payload.get("status") == "ok", "Stats player profile payload no longer returns ok status.")
require(profile_data.get("player_id") == "regression-player", "Stats player profile no longer preserves player id.")
require(profile_data.get("timeframe") == "weekly", "Stats player profile no longer preserves timeframe.")
require(profile_data.get("server_id") == "all-servers", "Stats player profile no longer defaults server scope to all-servers.")
require(isinstance(profile_data.get("matches_considered"), int), "Stats player profile matches_considered must remain an int.")
require(isinstance(profile_data.get("source"), dict), "Stats player profile source metadata must remain present.")
require(isinstance(profile_data.get("weekly_ranking"), (dict, type(None))), "Stats player profile weekly ranking shape changed unexpectedly.")
require(isinstance(profile_data.get("monthly_ranking"), (dict, type(None))), "Stats player profile monthly ranking shape changed unexpectedly.")

invalid_timeframe_status, _ = read_payload("/api/stats/players/regression-player?timeframe=seasonal")
require(invalid_timeframe_status == 400, "Stats player profile with invalid timeframe must return 400.")

current_year = datetime.now(timezone.utc).year
annual_status, annual_payload = read_payload(
    f"/api/stats/rankings/annual?year={current_year}&server_id=all&metric=kills&limit=20"
)
require(annual_status == 200, "Annual ranking should return 200 for metric=kills.")
annual_data = annual_payload.get("data") or {}
require(annual_payload.get("status") == "ok", "Annual ranking payload no longer returns ok status.")
require(annual_data.get("year") == current_year, "Annual ranking no longer preserves requested year.")
require(annual_data.get("server_id") == "all-servers", "Annual ranking no longer preserves the normalized all-servers scope.")
require(annual_data.get("metric") == "kills", "Annual ranking metric changed unexpectedly.")
require(
    isinstance(annual_data.get("limit"), int) and 1 <= annual_data.get("limit") <= 20,
    "Annual ranking limit must remain a positive int capped by the requested value.",
)
require(annual_data.get("snapshot_status") in {"ready", "missing"}, "Annual ranking snapshot status must remain ready or missing.")
require(isinstance(annual_data.get("items"), list), "Annual ranking items must remain a list.")

low_limit_status, low_limit_payload = read_payload(
    f"/api/stats/rankings/annual?year={current_year}&server_id=all&metric=kills&limit=3"
)
require(low_limit_status == 200, "Annual ranking with low limit must return 200.")
low_limit_value = (low_limit_payload.get("data") or {}).get("limit")
require(
    isinstance(low_limit_value, int) and 1 <= low_limit_value <= 3,
    "Annual ranking limit normalization for low limits changed unexpectedly.",
)

high_limit_status, _ = read_payload(
    f"/api/stats/rankings/annual?year={current_year}&server_id=all&metric=kills&limit=101"
)
require(high_limit_status == 400, "Annual ranking with limit=101 must return 400.")

unsupported_metric_status, unsupported_metric_payload = read_payload(
    f"/api/stats/rankings/annual?year={current_year}&server_id=all&metric=deaths&limit=20"
)
require(unsupported_metric_status == 400, "Annual ranking with unsupported metric must return 400.")
require("metric" in str(unsupported_metric_payload.get("message", "")).lower(), "Unsupported metric error message changed unexpectedly.")

missing_year_status, _ = read_payload("/api/stats/rankings/annual?year=2999&server_id=all&metric=kills&limit=20")
require(missing_year_status == 200, "Annual ranking future-year missing snapshot must still return 200.")

print(json.dumps({
    "checked": [
        "health",
        "stats-player-search",
        "stats-player-profile",
        "stats-annual-ranking",
    ],
    "annual_snapshot_status": annual_data.get("snapshot_status"),
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
    Write-Host "Expected limited behavior while offline: stats.html should show backend-unavailable states for search, profile, and annual ranking."
}

if ($backendAvailable) {
    $currentYear = (Get-Date).ToUniversalTime().Year
    $searchPayload = Invoke-RestMethod -Uri "$backendBaseUrl/api/stats/players/search?q=regression-check&limit=5" -TimeoutSec 5
    if ($searchPayload.status -ne "ok") {
        throw "Live stats search no longer returns status=ok."
    }

    $profilePayload = Invoke-RestMethod -Uri "$backendBaseUrl/api/stats/players/regression-player?timeframe=weekly" -TimeoutSec 5
    if ($profilePayload.status -ne "ok") {
        throw "Live stats profile no longer returns status=ok."
    }

    $annualPayload = Invoke-RestMethod -Uri "$backendBaseUrl/api/stats/rankings/annual?year=$currentYear&server_id=all&metric=kills&limit=20" -TimeoutSec 5
    if ($annualPayload.status -ne "ok") {
        throw "Live annual ranking no longer returns status=ok."
    }

    $unsupportedMetricStatus = Get-HttpStatusCode -Url "$backendBaseUrl/api/stats/rankings/annual?year=$currentYear&server_id=all&metric=deaths&limit=20"
    if ($unsupportedMetricStatus -ne 400) {
        throw "Live annual ranking with unsupported metric must return HTTP 400."
    }

    Write-Host "Live HTTP checks passed for Stats endpoints."
}

Write-Host "Stats regression validation passed."
