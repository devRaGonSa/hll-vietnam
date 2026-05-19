$ErrorActionPreference = "Stop"

Write-Host "HLL Vietnam platform validation"

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

Write-Host "No product integration tests are configured for this platform-only scope."
Write-Host "Platform validation passed."
exit 0
