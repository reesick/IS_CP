$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
$reference=Join-Path $projectRoot '.cache\portfolio-reference\portfolio-x-main'
$fonts=Join-Path $projectRoot 'frontend\research-demo\fonts'
New-Item -ItemType Directory -Force $fonts | Out-Null
Get-ChildItem -LiteralPath (Join-Path $reference 'fonts') -Filter '*.woff2' | Copy-Item -Destination $fonts
Copy-Item -LiteralPath (Join-Path $reference 'LICENSE') -Destination (Join-Path $fonts 'portfolio-reference-LICENSE.txt')
foreach ($family in @('inter','instrumentserif')) {
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/google/fonts/main/ofl/$family/OFL.txt" -OutFile (Join-Path $fonts "$family-OFL.txt") -UseBasicParsing -TimeoutSec 25
}
Write-Output 'Local font assets and reference/font licenses retained.'
