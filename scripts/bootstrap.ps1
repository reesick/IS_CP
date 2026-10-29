param([switch]$ML, [switch]$DownloadModel)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force .cache\temp,.cache\pip,.cache\huggingface | Out-Null
$env:TEMP = Join-Path (Get-Location) '.cache\temp'
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path (Get-Location) '.cache\pip'
$env:HF_HOME = Join-Path (Get-Location) '.cache\huggingface'
if (!(Test-Path .venv\Scripts\python.exe)) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -r requirements-api.lock
if ($LASTEXITCODE -ne 0) { throw 'API installation failed' }
if ($ML) {
    $sourcePath = Join-Path (Get-Location) 'third_party\DiffusionGuard'
    $sourceCommit = '96e28c19124fbb0e0671f48931ffed180775c7ea'
    if (!(Test-Path (Join-Path $sourcePath '.git'))) {
        git clone https://github.com/choi403/DiffusionGuard.git $sourcePath
        if ($LASTEXITCODE -ne 0) { throw 'Official DiffusionGuard source download failed' }
    }
    $origin = git -C $sourcePath remote get-url origin
    if ($origin -notmatch '^https://github.com/choi403/DiffusionGuard(?:\.git)?$') { throw 'Unexpected DiffusionGuard checkout origin' }
    $resolved = git -C $sourcePath rev-parse HEAD
    if ($resolved -ne $sourceCommit) {
        $dirty = git -C $sourcePath status --porcelain
        if ($dirty) { throw 'DiffusionGuard has local changes; refusing to overwrite them' }
        git -C $sourcePath checkout --detach $sourceCommit
        if ($LASTEXITCODE -ne 0) { throw 'Pinned DiffusionGuard checkout failed' }
    }
    if (!(Test-Path .venv-ml\Scripts\python.exe)) { python -m venv .venv-ml }
    & .\.venv-ml\Scripts\python.exe -m pip install -r requirements-ml.lock --extra-index-url https://download.pytorch.org/whl/cu121
    if ($LASTEXITCODE -ne 0) { throw 'ML installation failed' }
    & .\.venv-ml\Scripts\python.exe scripts/setup/check_environment.py --require-cuda
}
if ($DownloadModel) {
    & .\.venv-ml\Scripts\python.exe scripts/setup/download_models.py --model sd15_inpaint --ranged --workers 12
    if ($LASTEXITCODE -ne 0) { throw 'Model download failed; inspect error above' }
}
