# AI toolkit setup: Windows-MCP, Ponytail, Headroom for Claude Code, Codex, Gemini.
# Fresh machine, one line in PowerShell:
#   irm https://raw.githubusercontent.com/huycv18/ai-toolkit-setup/main/scripts/bootstrap.ps1 | iex
# From a local copy:
#   powershell -ExecutionPolicy Bypass -File bootstrap.ps1 [check|apply]
# Check only via one line: $env:AI_TOOLKIT_MODE="check"; irm ... | iex
# Log: %USERPROFILE%\ai-toolkit-setup.log
param([string]$Mode)

# Everything runs inside a script block so nothing leaks into the user's session under iex,
# and no "exit" here or in a child installer can close the user's window.
& {
    param([string]$Mode, [string]$ScriptDir)
    if (-not $Mode) { $Mode = $env:AI_TOOLKIT_MODE }
    if (-not $Mode) { $Mode = "apply" }
    $ErrorActionPreference = "Continue"
    $log = Join-Path $env:USERPROFILE "ai-toolkit-setup.log"
    $repoZip = "https://github.com/huycv18/ai-toolkit-setup/archive/refs/heads/main.zip"
    $env:UV_LINK_MODE = "copy"          # no hardlink warnings when cache and target are on different drives
    $env:PYTHONIOENCODING = "utf-8"
    $code = 1

    function Refresh-Path {
        $m = [Environment]::GetEnvironmentVariable("Path", "Machine")
        $u = [Environment]::GetEnvironmentVariable("Path", "User")
        $env:Path = "$env:USERPROFILE\.local\bin;$env:ProgramFiles\Git\cmd;$m;$u"
    }
    function Has($name) { [bool](Get-Command $name -ErrorAction SilentlyContinue) }
    function Install-Remote($name, $url) {
        # third-party installers call "exit": run them in a child process
        Write-Host "== Installing $name"
        & powershell -NoProfile -ExecutionPolicy Bypass -Command "irm $url | iex"
        Refresh-Path
        if (-not (Has $name)) { throw "$name install failed (see output above)" }
    }

    try { Start-Transcript -Path $log -Force | Out-Null } catch {}
    try {
        Refresh-Path
        if (-not (Has git)) {
            Write-Host "== Installing Git"
            & winget install --id Git.Git -e --silent --accept-source-agreements --accept-package-agreements
            Refresh-Path
            if (-not (Has git)) { throw "Git install failed. Install Git for Windows, then run again." }
        }
        if (-not (Has uv)) { Install-Remote "uv" "https://astral.sh/uv/install.ps1" }
        if (-not (Has claude)) { Install-Remote "claude" "https://claude.ai/install.ps1" }
        & git config --global core.longpaths true   # headroom repo has paths deeper than 260 chars

        $setup = if ($ScriptDir) { Join-Path $ScriptDir "setup.py" } else { "" }
        if (-not $setup -or -not (Test-Path $setup)) {
            Write-Host "== Downloading ai-toolkit-setup"
            $dir = Join-Path $env:TEMP "ai-toolkit-setup"
            Remove-Item $dir -Recurse -Force -ErrorAction SilentlyContinue
            Invoke-WebRequest $repoZip -OutFile "$dir.zip" -UseBasicParsing
            Expand-Archive "$dir.zip" $dir -Force
            $setup = (Get-ChildItem $dir -Recurse -Filter setup.py | Select-Object -First 1).FullName
        }

        Write-Host "== Running setup.py $Mode"
        & uv run --no-project --python 3.13 $setup $Mode
        $code = $LASTEXITCODE
    } catch {
        Write-Host "ERROR: $_" -ForegroundColor Red
    } finally {
        try { Stop-Transcript | Out-Null } catch {}
        $color = if ($code -eq 0) { "Green" } else { "Red" }
        Write-Host "`nDone, exit code $code. Log: $log" -ForegroundColor $color
        if (-not $ScriptDir -and [Environment]::UserInteractive -and $Host.Name -eq "ConsoleHost") {
            Read-Host "Press Enter to close" | Out-Null
        }
    }
    $global:LASTEXITCODE = $code
} $Mode $PSScriptRoot

if ($PSScriptRoot) { exit $LASTEXITCODE }
