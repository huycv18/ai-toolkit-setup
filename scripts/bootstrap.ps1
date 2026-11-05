# AI toolkit setup: Windows-MCP, Ponytail, Headroom for Claude Code, Codex, Gemini.
# Fresh machine, one line in PowerShell:
#   irm https://raw.githubusercontent.com/huycv18/ai-toolkit-setup/main/scripts/bootstrap.ps1 | iex
# From a local copy:
#   powershell -ExecutionPolicy Bypass -File bootstrap.ps1 [check|apply]
param([string]$Mode = "apply")
if (-not $Mode) { $Mode = "apply" }
$ErrorActionPreference = "Stop"
$repoZip = "https://github.com/huycv18/ai-toolkit-setup/archive/refs/heads/main.zip"
$bin = "$env:USERPROFILE\.local\bin"
$env:Path = "$bin;$env:Path"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Git..."
    winget install --id Git.Git -e --silent --accept-source-agreements --accept-package-agreements
    $env:Path = "$env:ProgramFiles\Git\cmd;$env:Path"
}
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

# Run via irm | iex: no local files, download the repo first
$setup = if ($PSScriptRoot) { Join-Path $PSScriptRoot "setup.py" } else { "" }
if (-not $setup -or -not (Test-Path $setup)) {
    $dir = Join-Path $env:TEMP "ai-toolkit-setup"
    Remove-Item $dir -Recurse -Force -ErrorAction SilentlyContinue
    Invoke-WebRequest $repoZip -OutFile "$dir.zip" -UseBasicParsing
    Expand-Archive "$dir.zip" $dir -Force
    $setup = (Get-ChildItem $dir -Recurse -Filter setup.py | Select-Object -First 1).FullName
}

$env:PYTHONIOENCODING = "utf-8"
uv run --no-project --python 3.13 $setup $Mode
if ($PSScriptRoot) { exit $LASTEXITCODE }  # do not close the user's shell under iex
