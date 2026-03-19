param(
    [int]$PollIntervalSeconds = 30
)

Write-Host "HLL Vietnam Codex worker started..."

$lockFile = "ai/worker.lock"

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

    $pendingTasks = Get-ChildItem "ai/tasks/pending" -Filter *.md -ErrorAction SilentlyContinue

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
        codex "Follow AGENTS.md, read the platform context in ai/, and process the pending tasks without acting outside task scope."
        $codexExitCode = $LASTEXITCODE
        $duration = [math]::Round(((Get-Date) - $startTime).TotalSeconds, 2)

        if ($codexExitCode -eq 0) {
            Add-Content "ai/system-metrics.md" "$(Get-Date -Format s) | worker-cycle | $duration sec | success | codex-runner"

            if (Test-Path "scripts/run-integration-tests.ps1") {
                powershell -ExecutionPolicy Bypass -File "scripts/run-integration-tests.ps1"
            }
        }
        else {
            Add-Content "ai/system-metrics.md" "$(Get-Date -Format s) | worker-cycle | $duration sec | failed($codexExitCode) | codex-runner"
        }
    }
    finally {
        Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
    }

    Start-Sleep -Seconds $PollIntervalSeconds
}
