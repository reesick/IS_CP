# One command: restart the dashboard, then start the portrait protection in the background.
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'restart-research-demo.ps1')
& (Join-Path $PSScriptRoot 'run-portrait-demo.ps1')
Start-Process 'http://127.0.0.1:8001/dashboard#pipeline'
