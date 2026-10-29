param([int]$Port=8001)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
$env:IMAGESHIELD_ML_PYTHON=Join-Path $projectRoot '.venv-frontier\Scripts\python.exe'
$env:HF_HOME=Join-Path $projectRoot '.cache\huggingface'
$env:CUDA_MODULE_LOADING='LAZY'
$statePath=Join-Path $projectRoot 'data\research-demo-process.json'
try {
    $health=Invoke-RestMethod "http://127.0.0.1:$Port/api/state" -TimeoutSec 2
    if ($health.status -eq 'preloaded') {
        Write-Output "Research demo already running: http://127.0.0.1:$Port"
        exit 0
    }
} catch {}
$python=Join-Path $projectRoot '.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force data\logs | Out-Null
$server=Start-Process -FilePath $python -ArgumentList @('-m','uvicorn','backend.research_demo:app','--host','127.0.0.1','--port',"$Port") -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput data\logs\research-demo.log -RedirectStandardError data\logs\research-demo-error.log
@{pid=$server.Id;port=$Port} | ConvertTo-Json | Set-Content $statePath
for ($attempt=0;$attempt -lt 30;$attempt++) {
    try {
        $health=Invoke-RestMethod "http://127.0.0.1:$Port/api/state" -TimeoutSec 2
        if ($health.status) { Write-Output "Research demo: http://127.0.0.1:$Port"; exit 0 }
    } catch {}
    Start-Sleep -Seconds 1
}
throw 'Research demo failed startup; inspect data/logs/research-demo-error.log.'
