$ErrorActionPreference = "Stop"

Write-Host "Historical UI regression validation"

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

function Assert-NotContains {
    param(
        [string] $Content,
        [string] $Pattern,
        [string] $Message
    )

    if ($Content -match [regex]::Escape($Pattern)) {
        throw $Message
    }
}

function Get-VisibleText {
    param([string] $Html)

    return ($Html -replace "<script[\s\S]*?</script>", " " `
        -replace "<style[\s\S]*?</style>", " " `
        -replace "<[^>]+>", " ")
}

$historicoHtml = Get-Content -Raw "frontend/historico.html"
$historicoPartidaHtml = Get-Content -Raw "frontend/historico-partida.html"
$historicoJs = Get-Content -Raw "frontend/assets/js/historico.js"
$historicoPartidaJs = Get-Content -Raw "frontend/assets/js/historico-partida.js"
$visibleHistoricalText = "$(Get-VisibleText $historicoHtml) $(Get-VisibleText $historicoPartidaHtml)"

Assert-NotContains $historicoHtml 'data-server-slug="comunidad-hispana-03"' `
    "Comunidad Hispana #03 selector was reintroduced."
Assert-NotContains $historicoHtml "MVP mensual V1" `
    "MVP mensual V1 block was reintroduced in visible historical HTML."
Assert-NotContains $historicoHtml "MVP mensual V2" `
    "MVP mensual V2 block was reintroduced in visible historical HTML."
Assert-NotContains $historicoHtml "Comparativa V1 vs V2" `
    "Comparativa V1 vs V2 block was reintroduced in visible historical HTML."
Assert-NotContains $historicoHtml "Elo/MMR" `
    "Elo/MMR public block was reintroduced in visible historical HTML."
Assert-NotContains $visibleHistoricalText "snapshot" `
    "Public snapshot wording was reintroduced in visible historical text."

Assert-Contains $historicoJs "Ver partida" `
    "Recent match cards no longer include the external match action label."
Assert-Contains $historicoJs "Ver detalles" `
    "Recent match cards no longer include the internal detail fallback label."
Assert-NotContains $historicoJs "item.match_url || item.source_url" `
    "Recent match cards must not trust legacy source_url fallback."
Assert-Contains $historicoPartidaJs "Ver en Scoreboard" `
    "Match detail page no longer includes the external scoreboard action label."
Assert-Contains $historicoPartidaJs 'rel="noopener noreferrer"' `
    "External scoreboard links must keep rel noopener noreferrer."
Assert-Contains $historicoPartidaJs 'target="_blank"' `
    "External scoreboard links must open in a new tab."

$backendCheck = @'
import sys
sys.path.insert(0, "backend")

from app.config import get_historical_data_source_kind
from app.routes import resolve_get_payload

status, payload = resolve_get_payload("/health")
if status is None or payload.get("status") != "ok":
    raise SystemExit("/health did not resolve to an ok payload.")
if payload.get("historical_data_source") != "rcon":
    raise SystemExit("/health no longer reports RCON-first historical source.")
if get_historical_data_source_kind() != "rcon":
    raise SystemExit("Configured historical source is no longer rcon.")

detail_status, detail_payload = resolve_get_payload(
    "/api/historical/matches/detail?server=comunidad-hispana-01&match=regression-check"
)
if detail_status is None or detail_payload.get("status") != "ok":
    raise SystemExit("Match detail endpoint did not resolve successfully.")
if detail_payload.get("data", {}).get("context") != "historical-match-detail":
    raise SystemExit("Match detail endpoint context changed unexpectedly.")
'@

$backendCheck | python -

Write-Host "Historical UI regression validation passed."
