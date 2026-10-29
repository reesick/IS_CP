# Closes ports 8000/8001, then opens visible windows with live logs:
#   1) Dashboard server (port 8001) + Playground model progress
#   2) Portrait protection job (step by step)
#   3) Raw model-process log (errors, CUDA messages)
param([switch]$NoPortrait,[switch]$RerunPortrait)
$root=Split-Path $PSScriptRoot -Parent
Set-Location $root
Write-Host 'Closing ports 8000/8001 and old ImageShield processes...' -ForegroundColor Yellow
Get-NetTCPConnection -LocalPort 8000,8001 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { taskkill /PID $_ /T /F 2>$null | Out-Null }
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*ImageShield*' -and $_.CommandLine -match 'research_demo|ml_runner|run-portrait-demo|backend.app' -and $_.ProcessId -ne $PID } | ForEach-Object { taskkill /PID $_.ProcessId /T /F 2>$null | Out-Null }
Start-Sleep -Seconds 2
New-Item -ItemType Directory -Force data\logs,outputs\portrait-demo | Out-Null
if (-not (Test-Path data\logs\ml-runtime.log)) { New-Item data\logs\ml-runtime.log | Out-Null }

$server = @"
`$Host.UI.RawUI.WindowTitle='ImageShield dashboard :8001'
Set-Location '$root'
`$env:IMAGESHIELD_ML_PYTHON='$root\.venv-frontier\Scripts\python.exe'
`$env:HF_HOME='$root\.cache\huggingface'
`$env:CUDA_MODULE_LOADING='LAZY'
`$env:PYTHONUNBUFFERED='1'
Write-Host 'Dashboard: http://127.0.0.1:8001  (Ctrl+C to stop)' -ForegroundColor Cyan
& '$root\.venv\Scripts\python.exe' -m uvicorn backend.research_demo:app --host 127.0.0.1 --port 8001
"@
Start-Process powershell -ArgumentList @('-NoExit','-NoProfile','-ExecutionPolicy','Bypass','-Command',$server)

$tail = @"
`$Host.UI.RawUI.WindowTitle='ImageShield model log'
Write-Host 'Model process log (SD1.5 loading, CUDA, errors)' -ForegroundColor Cyan
Get-Content '$root\data\logs\ml-runtime.log' -Tail 30 -Wait
"@
Start-Process powershell -ArgumentList @('-NoExit','-NoProfile','-Command',$tail)

$portraitDone=(Test-Path outputs\portrait-demo\results.json) -and (Select-String -Path outputs\portrait-demo\progress.json -Pattern '"done"' -Quiet -ErrorAction SilentlyContinue)
if ($portraitDone -and -not $RerunPortrait) { Write-Host 'Portrait already protected and tested; skipping (use -RerunPortrait to redo).' -ForegroundColor DarkGray }
if (-not $NoPortrait -and (-not $portraitDone -or $RerunPortrait)) {
    $job = @"
`$Host.UI.RawUI.WindowTitle='ImageShield portrait job'
Set-Location '$root'
`$env:PYTHONUNBUFFERED='1'
& powershell -NoProfile -ExecutionPolicy Bypass -File '$root\scripts\run-portrait-demo.ps1' -Foreground
"@
    Start-Process powershell -ArgumentList @('-NoExit','-NoProfile','-ExecutionPolicy','Bypass','-Command',$job)
}

for ($i=0;$i -lt 40;$i++) { try { Invoke-RestMethod http://127.0.0.1:8001/api/state -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep 1 } }
Start-Process 'http://127.0.0.1:8001/dashboard#pipeline'
Write-Host 'Started. Watch the three windows for live logs.' -ForegroundColor Green
