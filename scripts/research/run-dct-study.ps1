$ErrorActionPreference='Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
# Keep GPU optimization and editor inference sequential. Other GPU jobs must
# have finished before invoking this research batch.
& .\.venv-ml\Scripts\python.exe scripts/research/check-dct-math.py
if ($LASTEXITCODE -ne 0) { throw 'DCT mathematical checks failed.' }
& .\.venv-ml\Scripts\python.exe scripts/research/run-dct-shield.py
if ($LASTEXITCODE -ne 0) { throw 'DCT optimization failed.' }
& .\.venv-ml\Scripts\python.exe scripts/research/run-dct-pairs.py
if ($LASTEXITCODE -ne 0) { throw 'Paired editor diagnostics failed.' }
& .\.venv\Scripts\python.exe scripts/research/build-research-gallery.py
if ($LASTEXITCODE -ne 0) { throw 'Local evidence gallery generation failed.' }
