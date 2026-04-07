# ferclaudeobs project setup (Windows PowerShell)
# Clones repo, copies config, installs plugins
# Usage: powershell -ExecutionPolicy Bypass -File setup-project.ps1 [project-path]

param(
    [string]$ProjectDir = (Get-Location).Path
)

$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/ferone/ferclaudeobs.git"
$TmpDir = Join-Path ([System.IO.Path]::GetTempPath()) "ferclaudeobs-setup-$(Get-Random)"

function Cleanup {
    if (Test-Path $TmpDir) { Remove-Item -Recurse -Force $TmpDir }
}

trap { Cleanup } EXIT

# Resolve project directory
$ProjectDir = (Resolve-Path $ProjectDir).Path

Write-Host "=== ferclaudeobs Setup ===" -ForegroundColor Cyan
Write-Host "Project: $ProjectDir" -ForegroundColor White
Write-Host ""

if (-not (Test-Path $ProjectDir)) {
    Write-Host "Error: Directory '$ProjectDir' does not exist." -ForegroundColor Red
    exit 1
}

# Warn if .claude/ already exists
$ClaudeDir = Join-Path $ProjectDir ".claude"
if (Test-Path $ClaudeDir) {
    Write-Host "Warning: .claude/ already exists in this project." -ForegroundColor Yellow
    $confirm = Read-Host "Overwrite existing config? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Host "Aborted."
        exit 0
    }
}

# Step 1: Clone and copy
Write-Host "[1/2] Cloning ferclaudeobs and copying config..." -ForegroundColor White

$SrcDir = Join-Path $TmpDir "ferclaudeobs"
git clone --depth 1 $RepoUrl $SrcDir 2>&1 | Select-Object -Last 1

New-Item -ItemType Directory -Force -Path $ClaudeDir | Out-Null

Copy-Item (Join-Path $SrcDir "settings.json") -Destination $ClaudeDir -Force
Copy-Item (Join-Path $SrcDir "rules") -Destination $ClaudeDir -Recurse -Force
Copy-Item (Join-Path $SrcDir "skills") -Destination $ClaudeDir -Recurse -Force
Copy-Item (Join-Path $SrcDir "agents") -Destination $ClaudeDir -Recurse -Force
Copy-Item (Join-Path $SrcDir "hooks") -Destination $ClaudeDir -Recurse -Force
Copy-Item (Join-Path $SrcDir "scripts") -Destination $ClaudeDir -Recurse -Force
Copy-Item (Join-Path $SrcDir "plugins.json") -Destination $ClaudeDir -Force
Copy-Item (Join-Path $SrcDir ".gitignore") -Destination $ClaudeDir -Force

# CLAUDE.md goes to project root
$ClaudeMd = Join-Path $ProjectDir "CLAUDE.md"
if (Test-Path $ClaudeMd) {
    Write-Host "  CLAUDE.md already exists at project root - skipping (won't overwrite)." -ForegroundColor Yellow
} else {
    Copy-Item (Join-Path $SrcDir "CLAUDE.md") -Destination $ProjectDir -Force
}

$LocalMd = Join-Path $ProjectDir "CLAUDE.local.md"
if (-not (Test-Path $LocalMd)) {
    Copy-Item (Join-Path $SrcDir "CLAUDE.local.md.example") -Destination $ProjectDir -Force
}

# Add CLAUDE.local.md to .gitignore
$Gitignore = Join-Path $ProjectDir ".gitignore"
if (Test-Path $Gitignore) {
    $content = Get-Content $Gitignore -Raw
    if ($content -notmatch "CLAUDE\.local\.md") {
        Add-Content $Gitignore "CLAUDE.local.md"
    }
} else {
    "CLAUDE.local.md" | Set-Content $Gitignore
}

Write-Host "  Config files copied." -ForegroundColor Green

# Step 2: Install plugins
Write-Host "[2/2] Installing plugins..." -ForegroundColor White

if (Get-Command "claude" -ErrorAction SilentlyContinue) {
    $installScript = Join-Path $ClaudeDir "scripts" "install-plugins.ps1"
    & powershell -ExecutionPolicy Bypass -File $installScript
} else {
    Write-Host "  'claude' CLI not found - skipping plugin installation." -ForegroundColor Yellow
    Write-Host "  Install Claude Code (https://claude.ai/code), then run:" -ForegroundColor Yellow
    Write-Host "    powershell -ExecutionPolicy Bypass -File $ClaudeDir\scripts\install-plugins.ps1" -ForegroundColor Yellow
}

# Cleanup
Cleanup

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Restart Claude Code (if already running)"
Write-Host "  2. Run /init to select configs and customize for your project"
Write-Host ""
