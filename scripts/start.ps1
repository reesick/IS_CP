param([int]$Port = 8000, [switch]$Open)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (!(Test-Path $python)) { throw 'Run scripts/bootstrap.ps1 first.' }
New-Item -ItemType Directory -Force data\logs | Out-Null
$env:HF_HOME = Join-Path $projectRoot '.cache\huggingface'
$env:IMAGESHIELD_ML_PYTHON = Join-Path $projectRoot '.venv-ml\Scripts\python.exe'
if (Test-Path data\processes.json) {
    $saved = Get-Content data\processes.json -Raw | ConvertFrom-Json
    $existing = Get-CimInstance Win32_Process -Filter "ProcessId=$($saved.api)" -ErrorAction SilentlyContinue
    if ($existing -and $existing.ExecutablePath -and $existing.ExecutablePath.StartsWith($projectRoot, [StringComparison]::OrdinalIgnoreCase) -and $existing.CommandLine.Contains('backend.app.main:app')) {
        try {
            $existingHealth = Invoke-RestMethod -Uri "http://127.0.0.1:$($saved.port)/api/v1/health" -TimeoutSec 3
            if ($existingHealth.status -eq 'ok' -and $existingHealth.worker_alive) {
                Write-Output "ImageShield already running at http://127.0.0.1:$($saved.port)"
                exit 0
            }
        } catch { }
    }
    & (Join-Path $PSScriptRoot 'stop.ps1')
}
$api = Start-Process -FilePath $python -ArgumentList @('-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',"$Port") -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput data\logs\api.log -RedirectStandardError data\logs\api-error.log
$worker = Start-Process -FilePath $python -ArgumentList @('-m','backend.app.worker') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput data\logs\worker.log -RedirectStandardError data\logs\worker-error.log
@{api=$api.Id;worker=$worker.Id;port=$Port;started=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content data\processes.json
$healthy = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    if ($api.HasExited -or $worker.HasExited) { break }
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/v1/health" -TimeoutSec 2
        if ($health.status -eq 'ok' -and $health.worker_alive) { $healthy = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
}
if (!$healthy) {
    & (Join-Path $PSScriptRoot 'stop.ps1')
    throw 'Local startup did not pass API/worker health checks. Inspect data/logs.'
}
Write-Output "ImageShield: http://127.0.0.1:$Port (API $($api.Id), worker $($worker.Id))"
if ($Open) { Start-Process "http://127.0.0.1:$Port" }
