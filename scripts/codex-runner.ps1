param(
    [int]$PollIntervalSeconds = 30
)

$configPath = "ai-platform.json"

function Get-PlatformConfig {
    param(
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        return $null
    }

    try {
        return Get-Content -Raw $Path | ConvertFrom-Json
    }
    catch {
        Write-Host "Unable to read $Path. Falling back to default worker paths."
        return $null
    }
}

$platformConfig = Get-PlatformConfig -Path $configPath
$projectName = if ($platformConfig.project.name) { $platformConfig.project.name } else { "HLL Vietnam" }
$taskPaths = $platformConfig.workflow.task_paths
$runnerConfig = $platformConfig.runner

$pendingTasksPath = if ($taskPaths.pending) { $taskPaths.pending } else { "ai/tasks/pending" }
$lockFile = if ($runnerConfig.lock_file) { $runnerConfig.lock_file } else { "ai/worker.lock" }
$metricsFile = if ($runnerConfig.metrics_file) { $runnerConfig.metrics_file } else { "ai/system-metrics.md" }
$integrationTestsScript = if ($runnerConfig.integration_tests_script) { $runnerConfig.integration_tests_script } else { "scripts/run-integration-tests.ps1" }
$codexPrompt = if ($runnerConfig.codex_prompt) { $runnerConfig.codex_prompt } else { "Follow AGENTS.md, read the platform context in ai/, and process the pending tasks without acting outside task scope." }

Write-Host "$projectName Codex worker started..."

function Test-WorkerProcessActive {
    param(
        [string]$LockFilePath
    )

    if (-not (Test-Path $LockFilePath)) {
        return $false
    }

    $lockContent = Get-Content $LockFilePath -ErrorAction SilentlyContinue | Select-Object -First 1
    $workerPid = 0

    if ([int]::TryParse(($lockContent -as [string]), [ref]$workerPid) -and $workerPid -gt 0) {
        try {
            Get-Process -Id $workerPid -ErrorAction Stop | Out-Null
            return $true
        }
        catch {
            return $false
        }
    }

    return $false
}

while ($true) {
    if (Test-Path $lockFile) {
        if (Test-WorkerProcessActive -LockFilePath $lockFile) {
            Write-Host "Worker already running. Waiting..."
            Start-Sleep -Seconds $PollIntervalSeconds
            continue
        }

        Write-Host "Stale worker lock detected. Removing it."
        Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
    }

    $pendingTasks = Get-ChildItem $pendingTasksPath -Filter *.md -ErrorAction SilentlyContinue

    if (-not $pendingTasks) {
        Write-Host "No pending tasks found."
        Start-Sleep -Seconds $PollIntervalSeconds
        continue
    }

    if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
        Write-Host "Codex CLI not found. Install and authenticate Codex before running the worker."
        exit 1
    }

    Set-Content -Path $lockFile -Value "$PID" -NoNewline

    try {
        $startTime = Get-Date
        codex $codexPrompt
        $codexExitCode = $LASTEXITCODE
        $duration = [math]::Round(((Get-Date) - $startTime).TotalSeconds, 2)

        if ($codexExitCode -eq 0) {
            Add-Content $metricsFile "$(Get-Date -Format s) | worker-cycle | $duration sec | success | codex-runner"

            if (Test-Path $integrationTestsScript) {
                powershell -ExecutionPolicy Bypass -File $integrationTestsScript
            }
        }
        else {
            Add-Content $metricsFile "$(Get-Date -Format s) | worker-cycle | $duration sec | failed($codexExitCode) | codex-runner"
        }
    }
    finally {
        Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
    }

    Start-Sleep -Seconds $PollIntervalSeconds
}
