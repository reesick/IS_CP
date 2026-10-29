$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$state = Join-Path $projectRoot 'data\processes.json'
if (!(Test-Path $state)) { Write-Output 'No saved ImageShield processes.'; exit 0 }
$saved = Get-Content $state -Raw | ConvertFrom-Json
foreach ($entry in @(@{id=$saved.worker;module='backend.app.worker'}, @{id=$saved.api;module='backend.app.main:app'})) {
    $processId = $entry.id
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction SilentlyContinue
    $expectedPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if ($process -and $process.ExecutablePath -and $process.ExecutablePath.Equals($expectedPython, [StringComparison]::OrdinalIgnoreCase) -and $process.CommandLine.Contains($entry.module)) {
        & taskkill /PID $processId /T /F | Out-Null
    }
}
Remove-Item -LiteralPath $state
Write-Output 'Stopped ImageShield local processes.'
