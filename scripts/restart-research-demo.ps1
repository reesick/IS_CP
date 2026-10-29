# Stops the running dashboard (port 8001) and starts it again with the latest code.
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Set-Location $root
$statePath=Join-Path $root 'data\research-demo-process.json'
if (Test-Path $statePath) {
    $state=Get-Content $statePath -Raw | ConvertFrom-Json
    $proc=Get-CimInstance Win32_Process -Filter "ProcessId=$($state.pid)" -ErrorAction SilentlyContinue
    if ($proc -and $proc.CommandLine -like '*backend.research_demo:app*') { taskkill /PID $state.pid /T /F | Out-Null; Start-Sleep -Seconds 2 }
}
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*backend.research_demo:app*' } | ForEach-Object { taskkill /PID $_.ProcessId /T /F | Out-Null }
& (Join-Path $PSScriptRoot 'start-research-demo.ps1')
