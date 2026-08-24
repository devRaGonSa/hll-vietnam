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
Require-Contains $html 'data-public-nav' "Shared public navigation is missing."
Require-Contains $html 'Servidores <span class="public-nav__chevron"' "Servers dropdown is missing."
Require-Contains $html 'Comunidad <span class="public-nav__chevron"' "Community dropdown is missing."
Require-Contains $html 'href="./vip.html"' "VIP community navigation link is missing."
Require-Contains $html 'href="./normativa.html"' "Normative community navigation link is missing."
Require-Contains $html 'href="./bots.html"' "Bots community navigation link is missing."
Require-Contains $html 'public-nav.js?v=321' "Shared navigation behavior is missing."
Require-Contains $html 'map-image-resolver.js?v=323' "Home map image resolver is missing."
Require-Absent $html "CDO" "Unverified CDO reward was published."
Require-Absent $html "CDE" "Unverified CDE reward was published."
Require-Contains $html 'id="trailer-frame"' "Trailer was removed."
Require-Contains $html 'id="community-clans-list"' "Clans section was removed."
Require-Contains $javascript '/api/servers' "Server API contract changed."
Require-Contains $javascript 'normalizeServerGame(server.game)' `
    "Server cards no longer derive their game variant from the semantic game field."
Require-Contains $javascript 'server-card--game-hllv' `
    "HLL Vietnam server-card variant is missing."
Require-Contains $javascript 'data-game=' `
    "Server cards no longer expose their normalized game metadata."
Require-Contains $javascript 'SERVER_CARD_PRESENTATION' `
    "Compact server labels are not mapped from stable targets."
Require-Contains $javascript '"comunidad-hispana-01": Object.freeze({ label: "Servidor 1" })' `
    "Server 1 compact label is missing."
Require-Contains $javascript '"comunidad-hispana-02": Object.freeze({ label: "Servidor 2" })' `
    "Server 2 compact label is missing."
Require-Contains $javascript '"comunidad-hll-vietnam-01": Object.freeze({ label: "Servidor 3" })' `
    "Server 3 compact label is missing."
Require-Contains $javascript 'server.allied_score' "Live allied score is missing from cards."
Require-Contains $javascript 'server.axis_score' "Live axis score is missing from cards."
Require-Contains $javascript 'server.remaining_match_time_seconds' `
    "Canonical remaining time is missing from cards."
Require-Contains $javascript 'data-remaining-seconds' "Client countdown hook is missing."
Require-Contains $javascript 'loading="lazy"' "Map thumbnails are not lazy loaded."
Require-Contains $javascript 'unknown-day.webp' "Local map fallback is missing."
Require-Absent $javascript 'label: "Mapa"' "Obsolete MAPA label remains in server cards."
Require-Contains $css '.server-card--game-hllv' `
    "HLL Vietnam server-card styling is missing."
Require-Contains $css '.server-card__map-image' "Map thumbnail styling is missing."
Require-Contains $css '.server-card__live-metrics' "Live score/time layout is missing."
Require-Contains $javascript 'Hist\u00f3rico' "Historical server link changed."
Require-Contains $javascript 'Partida actual' "Current-match server link changed."

Write-Host "Home page regression validation passed."
