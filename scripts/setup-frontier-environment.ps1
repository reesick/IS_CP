$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
# Reclaim only completed downloader caches, never installed environments/weights.
$partPaths=@('.cache\torch-2.1.1+cu121-cp311-cp311-win_amd64.whl.parts','.cache\torchvision-0.16.1+cu121-cp311-cp311-win_amd64.whl.parts','models\sd15_inpaint\unet\diffusion_pytorch_model.fp16.safetensors.parts','models\sd15_inpaint\vae\diffusion_pytorch_model.fp16.safetensors.parts','models\sd15_inpaint\safety_checker\model.fp16.safetensors.parts')
foreach ($relative in $partPaths) {
    $candidate=Join-Path $projectRoot $relative
    if (Test-Path -LiteralPath $candidate) {
        $resolved=(Resolve-Path -LiteralPath $candidate).Path
        $completedFile=$resolved.Substring(0,$resolved.Length-6)
        if (!$resolved.StartsWith($projectRoot+'\',[StringComparison]::OrdinalIgnoreCase) -or !$resolved.EndsWith('.parts') -or !(Test-Path -LiteralPath $completedFile -PathType Leaf)) { throw 'Refusing unsafe or incomplete cache cleanup.' }
        Write-Output "Removing verified in-workspace completed download chunks: $resolved"
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
$env:TEMP=Join-Path $projectRoot '.cache\temp'
$env:TMP=$env:TEMP
$env:PIP_CACHE_DIR=Join-Path $projectRoot '.cache\frontier-pip'
if (!(Test-Path .venv-frontier\Scripts\python.exe)) { & .\.venv\Scripts\python.exe -m venv .venv-frontier }
& .\.venv-ml\Scripts\python.exe scripts/download-frontier-wheels.py
if ($LASTEXITCODE -ne 0) { throw 'Official frontier wheel download failed.' }
& .\.venv-frontier\Scripts\python.exe -m pip install '.cache/torch-2.6.0+cu124-cp311-cp311-win_amd64.whl' '.cache/torchvision-0.21.0+cu124-cp311-cp311-win_amd64.whl'
if ($LASTEXITCODE -ne 0) { throw 'Separate frontier Torch installation failed.' }
& .\.venv-frontier\Scripts\python.exe -m pip install -r requirements-frontier.in
if ($LASTEXITCODE -ne 0) { throw 'Frontier dependency installation failed.' }
& .\.venv-frontier\Scripts\python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Frontier dependency check failed.' }
& .\.venv-frontier\Scripts\python.exe -m pip freeze | Set-Content .cache\requirements-frontier-installed.freeze
Write-Output 'Modern environment installed separately. Full model weights/access and efficacy still require validation.'
