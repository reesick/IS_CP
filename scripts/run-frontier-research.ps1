$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
# Keep independently launched research GPU jobs serialized.
while (Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'scripts[\\/]run-paper-baselines\.py' }) {
    Start-Sleep -Seconds 5
}
& .\.venv-ml\Scripts\python.exe scripts/run-contrastive-probe.py --steps 250
if ($LASTEXITCODE -ne 0) { throw 'Experimental surrogate probe failed; no editor refusal claim is valid.' }
