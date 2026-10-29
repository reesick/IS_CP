# Protects + tamper-tests every face sample that is not done yet, one after another.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts/run-faces.ps1            (skip finished ones)
#         powershell -ExecutionPolicy Bypass -File scripts/run-faces.ps1 -Rerun     (redo all)
param([int]$Steps=1000,[switch]$Rerun,[string[]]$Only)
$root=Split-Path $PSScriptRoot -Parent
Set-Location $root
$env:HF_HOME=Join-Path $root '.cache\huggingface'
$env:CUDA_MODULE_LOADING='LAZY'
$env:PYTHONUNBUFFERED='1'
$ml=Join-Path $root '.venv-ml\Scripts\python.exe'
$frontier=Join-Path $root '.venv-frontier\Scripts\python.exe'
$dirs=@('portrait-demo','face-2-demo','face-3-demo')
if ($Only) { $dirs=$Only }
foreach ($d in $dirs) {
    $folder=Join-Path $root "outputs\$d"
    if (-not (Test-Path (Join-Path $folder 'source.png'))) { Write-Host "[$d] no source.png, skipping" -ForegroundColor DarkGray; continue }
    $progress=Join-Path $folder 'progress.json'
    $done=(Test-Path $progress) -and (Select-String -Path $progress -Pattern '"state": "done"' -Quiet)
    if ($done -and -not $Rerun) { Write-Host "[$d] already done, skipping" -ForegroundColor DarkGray; continue }
    Write-Host "==== [$d] protecting ($Steps steps, about 10 minutes) ====" -ForegroundColor Cyan
    & $ml scripts/run-portrait-demo.py protect --dir $d --steps $Steps
    if ($LASTEXITCODE -ne 0) { Write-Host "[$d] protection FAILED, moving on" -ForegroundColor Red; continue }
    Write-Host "==== [$d] tamper test (PNG + JPEG-85) ====" -ForegroundColor Cyan
    if (Test-Path $frontier) { & $frontier scripts/run-portrait-demo.py edit --dir $d --offload } else { & $ml scripts/run-portrait-demo.py edit --dir $d }
    if ($LASTEXITCODE -ne 0) { Write-Host "[$d] tamper test FAILED" -ForegroundColor Red; continue }
    Write-Host "[$d] done. It appears in the dashboard automatically." -ForegroundColor Green
}
Write-Host 'All face jobs finished.' -ForegroundColor Green
