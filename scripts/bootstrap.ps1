# Fresh Windows machine: install uv and Claude Code CLI if missing, then run setup.py.
# Usage: powershell -ExecutionPolicy Bypass -File bootstrap.ps1 [check|apply]
param([string]$Mode = "apply")
$ErrorActionPreference = "Stop"
$bin = "$env:USERPROFILE\.local\bin"
$env:Path = "$bin;$env:Path"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
}
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Claude Code CLI..."
    Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression
}
# headroom repo has paths deeper than 260 chars; plugin clones fail without this
git config --global core.longpaths true
$env:PYTHONIOENCODING = "utf-8"
uv run --no-project --python 3.13 "$PSScriptRoot\setup.py" $Mode
exit $LASTEXITCODE
