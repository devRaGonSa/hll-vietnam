$ErrorActionPreference = "Stop"

Write-Host "HLL Vietnam platform validation"

function Assert-LastExitCode {
    param([string] $Message)

    if ($LASTEXITCODE -ne 0) {
        throw $Message
    }
}

$configPath = "ai-platform.json"
if (-not (Test-Path $configPath)) {
    throw "Missing $configPath"
}

$config = Get-Content -Raw $configPath | ConvertFrom-Json
$taskPaths = $config.workflow.task_paths

$requiredTaskPaths = @(
    $taskPaths.pending,
    $taskPaths.in_progress,
    $taskPaths.review,
    $taskPaths.blocked,
    $taskPaths.obsolete,
    $taskPaths.done
)

foreach ($path in $requiredTaskPaths) {
    if (-not $path -or -not (Test-Path $path)) {
        throw "Missing task lifecycle path: $path"
    }
}

$gitignore = Get-Content -Raw ".gitignore"
$requiredIgnoreRules = @(
    "backend/runtime/",
    "ai/reports/*.md",
    "!ai/reports/.gitkeep"
)

foreach ($rule in $requiredIgnoreRules) {
    if ($gitignore -notmatch [regex]::Escape($rule)) {
        throw "Missing .gitignore rule: $rule"
    }
}

if (-not (Test-Path "ai/reports/.gitkeep")) {
    throw "Missing ai/reports/.gitkeep"
}

$backendImportCheck = @'
import sys
sys.path.insert(0, "backend")
import app.main
from app.routes import resolve_get_payload

status, payload = resolve_get_payload("/health")
if status is None or payload.get("status") != "ok":
    raise SystemExit("Backend health route did not resolve to an ok payload.")
'@

$backendImportCheck | python -
Assert-LastExitCode "Backend startup import check failed."

powershell -ExecutionPolicy Bypass -File scripts/run-historical-ui-regression-tests.ps1
Assert-LastExitCode "Historical UI regression validation failed."
powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1
Assert-LastExitCode "Stats regression validation failed."

Write-Host "No product integration tests are configured for this platform-only scope."
Write-Host "Backend startup import check passed."
Write-Host "Platform validation passed."
exit 0
