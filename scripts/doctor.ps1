$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
Write-Output 'API environment (no model loading)'
& .\.venv\Scripts\python.exe scripts/setup/check_environment.py
$apiExit = $LASTEXITCODE
Write-Output 'ML environment (CUDA preflight, no model loading)'
& .\.venv-ml\Scripts\python.exe scripts/setup/check_environment.py --require-cuda
$mlExit = $LASTEXITCODE
if ($apiExit -ne 0 -or $mlExit -ne 0) { exit 1 }
