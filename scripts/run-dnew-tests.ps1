$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& .\.venv\Scripts\python.exe scripts/test-dnew.py
if ($LASTEXITCODE -ne 0) { throw 'Dnew tests failed; inspect output and saved results.' }
