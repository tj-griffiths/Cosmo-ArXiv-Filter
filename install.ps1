# Cosmo Installer for Windows PowerShell - run this once after downloading/extracting the repo

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppPath = Join-Path $ScriptDir "app.py"

if (-not (Test-Path -Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
}

$FunctionBlock = @"
function cosmo {
    python "$AppPath" @args
}
"@

$ExistingContent = Get-Content -Path $PROFILE -Raw -ErrorAction SilentlyContinue

if ($ExistingContent -and $ExistingContent.Contains($FunctionBlock)) {
    Write-Host "Already installed - 'cosmo' is already set in $PROFILE"
} else {
    Add-Content -Path $PROFILE -Value "`n# Added by Cosmo's install.ps1`n$FunctionBlock"
    Write-Host "Added 'cosmo' command to $PROFILE"
}

Write-Host ""
Write-Host "Setup complete! Open a NEW PowerShell window (or run: . `$PROFILE)"
Write-Host "then type 'cosmo' from anywhere to launch the app."