$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:HF_HOME=Join-Path (Get-Location) '.cache\huggingface'
$env:TEMP=Join-Path (Get-Location) '.cache\temp'
& .\.venv-ml\Scripts\python.exe scripts/download-research-encoder.py
if ($LASTEXITCODE -ne 0) { throw 'Verified research encoder download failed.' }
