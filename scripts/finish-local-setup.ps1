$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:TEMP = Join-Path (Get-Location) '.cache\temp'
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path (Get-Location) '.cache\pip'
$env:HF_HOME = Join-Path (Get-Location) '.cache\huggingface'
$mlPython = Join-Path (Get-Location) '.venv-ml\Scripts\python.exe'
& $mlPython -m pip install '.cache/torch-2.1.1+cu121-cp311-cp311-win_amd64.whl' '.cache/torchvision-0.16.1+cu121-cp311-cp311-win_amd64.whl'
if ($LASTEXITCODE -ne 0) { throw 'Local CUDA wheel installation failed.' }
& $mlPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'ML dependency check failed.' }
& $mlPython scripts/freeze-ml.py
& $mlPython scripts/check_environment.py --require-cuda
if ($LASTEXITCODE -ne 0) { throw 'CUDA doctor failed.' }
& $mlPython -m backend.app.ml.smoke --output data/ml-smoke --edit
if ($LASTEXITCODE -ne 0) { throw 'Real GPU smoke failed. Inspect the log; do not mark protection successful.' }
