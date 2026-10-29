$ErrorActionPreference='Stop'
$projectRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $projectRoot
& .\.venv-frontier\Scripts\python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency consistency check failed.' }
& .\.venv-frontier\Scripts\python.exe scripts/research/check-cad-flux.py
if ($LASTEXITCODE -ne 0) { throw 'Actual FLUX architecture contract failed.' }
& .\.venv-frontier\Scripts\python.exe scripts/setup/check-frontier-preflight.py
if ($LASTEXITCODE -ne 0) { throw 'Preflight could not run.' }
& .\.venv-frontier\Scripts\python.exe scripts/setup/freeze-frontier.py
if ($LASTEXITCODE -ne 0) { throw 'Environment provenance export failed.' }
