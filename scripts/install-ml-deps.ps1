$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:TEMP = Join-Path (Get-Location) '.cache\temp'
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path (Get-Location) '.cache\pip'
& .\.venv-ml\Scripts\python.exe -m pip install diffusers==0.24.0 transformers==4.35.2 huggingface-hub==0.25.2 numpy==1.26.4 Pillow safetensors omegaconf opencv-contrib-python==4.10.0.84 scipy tqdm fastapi uvicorn python-multipart pydantic-settings cryptography scikit-image itsdangerous
if ($LASTEXITCODE -ne 0) { throw 'ML dependencies install failed' }
