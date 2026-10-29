$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:TEMP = Join-Path (Get-Location) '.cache\temp'
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path (Get-Location) '.cache\pip'
$env:HF_HOME = Join-Path (Get-Location) '.cache\huggingface'
& .\.venv\Scripts\python.exe -m pip install fastapi uvicorn python-multipart Pillow numpy cryptography pydantic-settings pytest httpx scikit-image itsdangerous
if ($LASTEXITCODE -ne 0) { throw 'API install failed' }
& .\.venv\Scripts\python.exe -m pip freeze | Set-Content requirements-api.lock
& .\.venv-ml\Scripts\python.exe -m pip install torch==2.1.1 torchvision==0.16.1 --index-url https://download.pytorch.org/whl/cu121
if ($LASTEXITCODE -ne 0) { throw 'CUDA install failed' }
& .\.venv-ml\Scripts\python.exe -m pip install diffusers==0.24.0 transformers==4.35.2 huggingface-hub==0.25.2 accelerate==0.24.1 numpy==1.26.4 Pillow safetensors omegaconf opencv-contrib-python==4.10.0.84 scipy tqdm fastapi uvicorn python-multipart pydantic-settings cryptography scikit-image itsdangerous
if ($LASTEXITCODE -ne 0) { throw 'ML install failed' }
& .\.venv-ml\Scripts\python.exe -m pip freeze | Set-Content requirements-ml.lock
& .\.venv-ml\Scripts\python.exe scripts/check_environment.py --require-cuda

