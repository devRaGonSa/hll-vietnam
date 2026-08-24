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
$vipIndex = $html.IndexOf('class="panel panel--vip"')
$trailerIndex = $html.IndexOf('class="panel panel--video"')
$clansIndex = $html.IndexOf('class="panel panel--clans"')
if (-not (0 -le $serversIndex -and $serversIndex -lt $vipIndex -and $vipIndex -lt $trailerIndex -and $trailerIndex -lt $clansIndex)) {
    throw "Home sections are not ordered servers, VIP, trailer, clans."
}

Require-Contains $html 'id="vip-title">Premios VIP' "Premios VIP section is missing."
Require-Contains $html "Solicita tu VIP anual abriendo un ticket" "Annual Discord-ticket policy is missing."
Require-Contains $html "aportación o pago anual" "Annual contribution policy is missing."
Require-Contains $html "Abrir ticket en Discord" "Annual VIP CTA is missing."
Require-Contains $html 'rel="noopener noreferrer"' "External Discord protection is missing."
Require-Contains $html 'target="_blank"' "External Discord target is missing."
Require-Contains $html "1.000 bajas" "Verified weekly kills reward is missing."
Require-Contains $html "15.000 puntos de soporte" "Verified weekly support reward is missing."
Require-Contains $html "10.000 puntos de ataque" "Verified weekly offense reward is missing."
Require-Contains $html "12.000 puntos de defensa" "Verified weekly defense reward is missing."
Require-Contains $html "50 vehículos destruidos" "Verified weekly vehicle reward is missing."
Require-Contains $html "10 bajas cuerpo a cuerpo con cuchillo o pala" "Verified weekly melee reward is missing."
Require-Contains $html "Mayor tiempo jugado de la semana" "Verified weekly playtime reward is missing."
Require-Contains $html "HLL #1 y HLL #2</span><strong>+24 h VIP" "Verified HLL seeding reward is missing."
Require-Contains $html "HLL Vietnam</span><strong>+12 h VIP" "Verified HLLV seeding reward is missing."
Require-Absent $html "CDO" "Unverified CDO reward was published."
Require-Absent $html "CDE" "Unverified CDE reward was published."
Require-Contains $html 'id="trailer-frame"' "Trailer was removed."
Require-Contains $html 'id="community-clans-list"' "Clans section was removed."
Require-Contains $javascript '/api/servers' "Server API contract changed."
Require-Contains $javascript 'Hist\u00f3rico' "Historical server link changed."
Require-Contains $javascript 'Partida actual' "Current-match server link changed."

Write-Host "Home page regression validation passed."
