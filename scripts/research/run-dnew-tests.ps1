$ErrorActionPreference='Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
& .\.venv\Scripts\python.exe scripts/research/test-dnew.py
if ($LASTEXITCODE -ne 0) { throw 'Dnew tests failed; inspect output and saved results.' }
