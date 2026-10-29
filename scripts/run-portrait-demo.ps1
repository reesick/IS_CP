# Runs the portrait protection + tamper test in the background.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts/run-portrait-demo.ps1
param([int]$Steps=1000,[switch]$Foreground)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Set-Location $root
if (-not $Foreground) {
    New-Item -ItemType Directory -Force outputs\portrait-demo | Out-Null
    $log=Join-Path $root 'outputs\portrait-demo\run.log'
    $p=Start-Process powershell -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',$PSCommandPath,'-Steps',"$Steps",'-Foreground') -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError "$log.err" -PassThru
    Write-Output "Portrait demo started in background (PID $($p.Id)). Progress shows on the dashboard; log: outputs\portrait-demo\run.log"
    exit 0
}
$env:HF_HOME=Join-Path $root '.cache\huggingface'
$env:CUDA_MODULE_LOADING='LAZY'
$ml=Join-Path $root '.venv-ml\Scripts\python.exe'
$frontier=Join-Path $root '.venv-frontier\Scripts\python.exe'
& $ml scripts/run-portrait-demo.py protect --steps $Steps
if ($LASTEXITCODE -ne 0) { throw 'Portrait protection failed; see outputs\portrait-demo\run.log' }
if (Test-Path $frontier) { & $frontier scripts/run-portrait-demo.py edit --offload } else { & $ml scripts/run-portrait-demo.py edit }
if ($LASTEXITCODE -ne 0) { throw 'Portrait tamper test failed; see outputs\portrait-demo\run.log' }
Write-Output 'Portrait demo complete. Refresh the dashboard.'
