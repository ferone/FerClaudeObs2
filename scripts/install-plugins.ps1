# ferclaudeobs plugin installer (Windows PowerShell)
# Installs all plugins listed in plugins.json on a new machine.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\install-plugins.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoDir = Split-Path -Parent $ScriptDir
$PluginsFile = Join-Path $RepoDir "plugins.json"

# Check prerequisites
if (-not (Get-Command "claude" -ErrorAction SilentlyContinue)) {
    Write-Host "Error: 'claude' CLI not found." -ForegroundColor Red
    Write-Host "Install Claude Code first: https://claude.ai/code"
    exit 1
}

if (-not (Test-Path $PluginsFile)) {
    Write-Host "Error: plugins.json not found at $PluginsFile" -ForegroundColor Red
    exit 1
}

Write-Host "=== ferclaudeobs Plugin Installer ===" -ForegroundColor Cyan
Write-Host ""

$config = Get-Content $PluginsFile | ConvertFrom-Json

# Add marketplaces
Write-Host "Adding marketplaces..."

if ($config.marketplaces.impeccable) {
    Write-Host "  Adding impeccable marketplace..."
    try {
        claude plugin marketplace add impeccable --source git --url $config.marketplaces.impeccable.url 2>$null
    } catch {
        Write-Host "  (already added or failed)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Installing plugins..."

$total = 0
$success = 0
$failed = 0
$skipped = 0

foreach ($plugin in $config.plugins) {
    $total++
    $parts = $plugin -split "@"
    $pluginName = $parts[0]
    $marketplace = $parts[1]

    Write-Host "  [$total] $pluginName ($marketplace)... " -NoNewline

    try {
        $output = claude plugin install $plugin 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "installed" -ForegroundColor Green
            $success++
        } else {
            # Check if already installed
            $list = claude plugin list 2>&1
            if ($list -match $pluginName) {
                Write-Host "already installed" -ForegroundColor Yellow
                $skipped++
            } else {
                Write-Host "failed" -ForegroundColor Red
                $failed++
            }
        }
    } catch {
        Write-Host "failed" -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan
Write-Host "  Installed: $success" -ForegroundColor Green
Write-Host "  Already installed: $skipped" -ForegroundColor Yellow
if ($failed -gt 0) {
    Write-Host "  Failed: $failed" -ForegroundColor Red
}
Write-Host "  Total: $total"
Write-Host ""
Write-Host "Restart Claude Code to load new plugins."
