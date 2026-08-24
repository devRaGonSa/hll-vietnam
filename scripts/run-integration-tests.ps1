$ErrorActionPreference = "Stop"

Write-Host "HLL Vietnam integration validation"

function Assert-LastExitCode {
    param([string] $Message)

    if ($LASTEXITCODE -ne 0) {
        throw $Message
    }
}

$gitignore = Get-Content -Raw ".gitignore"
$requiredIgnoreRules = @(
    "backend/runtime/"
)

foreach ($rule in $requiredIgnoreRules) {
    if ($gitignore -notmatch [regex]::Escape($rule)) {
        throw "Missing .gitignore rule: $rule"
    }
}

$backendImportCheck = @'
import sys
sys.path.insert(0, "backend")
import app.main
from app.api.routes import resolve_get_payload

status, payload = resolve_get_payload("/health")
if status is None or payload.get("status") != "ok":
    raise SystemExit("Backend health route did not resolve to an ok payload.")
'@

$backendImportCheck | python -
Assert-LastExitCode "Backend startup import check failed."

powershell -ExecutionPolicy Bypass -File scripts/run-historical-ui-regression-tests.ps1
Assert-LastExitCode "Historical UI regression validation failed."
powershell -ExecutionPolicy Bypass -File scripts/run-home-page-regression-tests.ps1
Assert-LastExitCode "Home page regression validation failed."
powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1
Assert-LastExitCode "Stats regression validation failed."

Write-Host "Backend startup import check passed."
Write-Host "Integration validation passed."
exit 0
