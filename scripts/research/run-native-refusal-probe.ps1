$ErrorActionPreference='Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
# This is a reduced experimental profile, never the paper's88percent result.
& .\.venv-ml\Scripts\python.exe scripts/research/run-contrastive-probe.py --steps 5000 --native
if ($LASTEXITCODE -ne 0) { throw 'Native refusal-surrogate experiment failed.' }
