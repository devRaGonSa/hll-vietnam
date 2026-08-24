$ErrorActionPreference = "Stop"

Write-Host "Home page regression validation"

function Require-Contains {
    param([string] $Content, [string] $Value, [string] $Message)
    if (-not $Content.Contains($Value)) {
        throw $Message
    }
}

function Require-Absent {
    param([string] $Content, [string] $Value, [string] $Message)
    if ($Content.Contains($Value)) {
        throw $Message
    }
}

$html = Get-Content -Raw "frontend/index.html"
$javascript = Get-Content -Raw "frontend/assets/js/main.js"
$css = Get-Content -Raw "frontend/assets/css/styles.css"
$countdownContracts = @(
    "data-hll-vietnam-countdown",
    "data-countdown-target",
    "data-countdown-days",
    "data-countdown-hours",
    "data-countdown-minutes",
    "data-countdown-seconds",
    "release-countdown",
    "initializeReleaseCountdown",
    "setCountdownUnit"
)

foreach ($contract in $countdownContracts) {
    Require-Absent "$html`n$javascript`n$css" $contract `
        "Obsolete countdown contract remains: $contract"
}

if ($html -notmatch '</header>\s*<main class="content">\s*<section class="panel panel--servers"') {
    throw "Server status is not directly after the hero in the main content flow."
}

$serversIndex = $html.IndexOf('class="panel panel--servers"')
$trailerIndex = $html.IndexOf('class="panel panel--video"')
$clansIndex = $html.IndexOf('class="panel panel--clans"')
if (-not (0 -le $serversIndex -and $serversIndex -lt $trailerIndex -and $trailerIndex -lt $clansIndex)) {
    throw "Home sections are not ordered servers, trailer, clans."
}

Require-Absent $html 'class="panel panel--vip"' "VIP content must not remain on the home page."
Require-Contains $html 'href="./vip.html"' "VIP navigation link is missing."
Require-Absent $html "CDO" "Unverified CDO reward was published."
Require-Absent $html "CDE" "Unverified CDE reward was published."
Require-Contains $html 'id="trailer-frame"' "Trailer was removed."
Require-Contains $html 'id="community-clans-list"' "Clans section was removed."
Require-Contains $javascript '/api/servers' "Server API contract changed."
Require-Contains $javascript 'Hist\u00f3rico' "Historical server link changed."
Require-Contains $javascript 'Partida actual' "Current-match server link changed."

Write-Host "Home page regression validation passed."
