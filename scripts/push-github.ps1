# Commit everything (code only; models, outputs, data and venvs are git-ignored) and push to GitHub.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts/push-github.ps1 "your commit message"
param([string]$Message = "ImageShield: dashboard, pipeline, verify page and audit trail")
$ErrorActionPreference = 'Continue'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$repo = 'https://github.com/reesick/IS_CP.git'
Get-ChildItem .git -Filter *.lock -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
if (-not (Test-Path .git)) { git init | Out-Null }
git config user.name  *> $null; if ($LASTEXITCODE -ne 0) { Write-Host 'Set your git identity first: git config --global user.name "Your Name"; git config --global user.email "you@example.com"' -ForegroundColor Red; exit 1 }
Write-Host 'Files to commit:' -ForegroundColor Cyan
git add -A
git status --short
$big = git diff --cached --name-only | Where-Object { (Test-Path $_) -and ((Get-Item $_).Length -gt 50MB) }
if ($big) { Write-Host "Refusing to push files over 50 MB: $big" -ForegroundColor Red; exit 1 }
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) { git commit -m $Message | Out-Null; Write-Host 'Committed.' -ForegroundColor Green } else { Write-Host 'Nothing new to commit.' -ForegroundColor DarkGray }
git branch -M main
if (git remote | Select-String -SimpleMatch origin -Quiet) { git remote set-url origin $repo } else { git remote add origin $repo }
git fetch origin 2>$null
git rev-parse --verify origin/main *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Host 'Merging what is already on GitHub (e.g. its README)...' -ForegroundColor Cyan
    git pull origin main --allow-unrelated-histories --no-rebase --no-edit -X ours
}
git push -u origin main
if ($LASTEXITCODE -eq 0) { Write-Host "Pushed: $repo" -ForegroundColor Green } else { Write-Host 'Push failed. If GitHub asks you to sign in, complete the browser login and run this again.' -ForegroundColor Red }
