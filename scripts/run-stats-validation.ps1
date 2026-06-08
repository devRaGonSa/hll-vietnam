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

$statsHtml = Get-Content -Raw "frontend/stats.html"
$statsJs = Get-Content -Raw "frontend/assets/js/stats.js"

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
Assert-ContainsText $statsJs 'getElementById("stats-search-form")' `
    "Stats JS no longer sets up search form lookup."
Assert-ContainsText $statsJs "loadPlayerProfile(" `
    "Stats JS no longer defines loadPlayerProfile."

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


def require_int(value, message):
    require(isinstance(value, int), message)


def require_str(value, message):
    require(isinstance(value, str), message)


health_status, health_payload = read_payload("/health")
require(health_status == 200, "Route resolver /health should return 200.")
require(health_payload.get("status") == "ok", "/health payload should be ok.")

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
require(weekly_ranking_data.get("snapshot_status") == "ready", "Global ranking weekly should expose ready snapshot status.")
require(isinstance(weekly_ranking_data.get("items"), list), "Global ranking weekly items must be list.")
require(isinstance(weekly_ranking_data.get("source"), dict), "Global ranking weekly should expose source metadata.")

monthly_ranking_status, monthly_ranking_payload = read_payload(
    "/api/ranking?timeframe=monthly&server_id=comunidad-hispana-01&metric=kills&limit=20"
)
require(monthly_ranking_status == 200, "Global ranking monthly route should return 200.")
monthly_ranking_data = monthly_ranking_payload.get("data") or {}
require(monthly_ranking_data.get("timeframe") == "monthly", "Global ranking monthly timeframe should be preserved.")
require(monthly_ranking_data.get("server_id") == "comunidad-hispana-01", "Global ranking monthly should preserve server_id.")

annual_ranking_status, annual_ranking_payload = read_payload(
    f"/api/ranking?timeframe=annual&year={current_year}&server_id=all&metric=kills&limit=20"
)
require(annual_ranking_status == 200, "Global ranking annual route should return 200.")
annual_ranking_data = annual_ranking_payload.get("data") or {}
require(annual_ranking_data.get("timeframe") == "annual", "Global ranking annual timeframe should be preserved.")
require(annual_ranking_data.get("metric") == "kills", "Global ranking annual metric should be kills.")
require(annual_ranking_data.get("snapshot_status") in {"ready", "missing"}, "Global ranking annual snapshot_status should be ready or missing.")
require(isinstance(annual_ranking_data.get("items"), list), "Global ranking annual items must be list.")

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
    "/api/ranking?timeframe=weekly&server_id=all&metric=deaths&limit=20"
)
require(unsupported_metric_ranking_status == 400, "Global ranking with unsupported metric should return 400.")

unsupported_timeframe_ranking_status, _ = read_payload(
    "/api/ranking?timeframe=seasonal&server_id=all&metric=kills&limit=20"
)
require(unsupported_timeframe_ranking_status == 400, "Global ranking with unsupported timeframe should return 400.")

missing_year_ranking_status, _ = read_payload(
    "/api/ranking?timeframe=annual&server_id=all&metric=kills&limit=20"
)
require(missing_year_ranking_status == 400, "Global ranking annual requests without year should return 400.")

print(json.dumps({
    "checked": [
        "health",
        "stats-player-search",
        "stats-player-profile",
        "stats-annual-ranking",
        "global-ranking",
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

    $rankingAnnualPayload = Invoke-RestMethod -Uri "$backendBaseUrl/api/ranking?timeframe=annual&year=$currentYear&server_id=all&metric=kills&limit=20" -TimeoutSec 5
    if ($rankingAnnualPayload.status -ne "ok") {
        throw "Live global ranking annual route should return status=ok."
    }
    if (-not ($rankingAnnualPayload.data.snapshot_status -in @("ready", "missing"))) {
        throw "Live global ranking annual should expose ready/missing snapshot status."
    }

    $rankingUnsupportedMetricStatus = Get-HttpStatusCode -Url "$backendBaseUrl/api/ranking?timeframe=weekly&server_id=all&metric=deaths&limit=20"
    if ($rankingUnsupportedMetricStatus -ne 400) {
        throw "Live global ranking with unsupported metric should return HTTP 400."
    }

    Write-Host "Live HTTP checks passed for Stats endpoints."
}

Write-Host "Stats regression validation passed."
