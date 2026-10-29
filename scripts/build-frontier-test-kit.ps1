param([int]$Steps=5000,[double]$EpsilonLevels=2,[string]$InitialDir,[string]$OutputDir,[switch]$PublishDownloads)
$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$arguments=@('scripts/build-frontier-test-kit.py','--steps',"$Steps",'--epsilon-levels',"$EpsilonLevels")
if ($PublishDownloads) {$arguments+='--publish-downloads'}
if ($InitialDir) {$arguments+=@('--initial-dir',$InitialDir)}
if ($OutputDir) {$arguments+=@('--out',$OutputDir)}
& .\.venv-ml\Scripts\python.exe @arguments
if ($LASTEXITCODE -ne 0) {throw "Experimental export batch failed or was quality rejected (exit $LASTEXITCODE)."}
