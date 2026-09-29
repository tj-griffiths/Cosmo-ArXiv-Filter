# Cosmo Installer for Windows PowerShell - run this once after downloading/extracting the repo

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppPath = Join-Path $ScriptDir "app.py"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppPath = Join-Path $ScriptDir "app.py"

# --- Find the real Python interpreter ---
# Asking Python for sys.executable gives its full path, and filters out the
# Microsoft Store "python" stub (exists on PATH but only prints an error).
function Get-PythonExe([string]$Cmd) {
    $ErrorActionPreference = "Continue"   # PS 5.1 treats stderr as fatal under "Stop"
    try {
        $out = & $Cmd -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) { return ($out | Select-Object -Last 1).Trim() }
    } catch { }
    return $null
}

$PythonExe = Get-PythonExe "python"
if (-not $PythonExe) { $PythonExe = Get-PythonExe "py" }
if (-not $PythonExe) {
    throw "No working Python found. Install Python 3.11+ from python.org (tick 'Add python.exe to PATH'), then re-run."
}
Write-Host "Using Python: $PythonExe"

# --- Write a cosmo.cmd launcher next to app.py ---
# .cmd files aren't blocked by execution policy (profiles are), and work in
# PowerShell 5.1, PowerShell 7 and cmd.exe. %~dp0 = this file's folder.
$Launcher = Join-Path $ScriptDir "cosmo.cmd"
Set-Content -Path $Launcher -Encoding Oem -Value @"
@echo off
"$PythonExe" "%~dp0app.py" %*
"@

# --- Add the Cosmo folder to the user PATH ---
# Read/write the registry directly so entries like %USERPROFILE%\bin aren't
# expanded and overwritten, which [Environment]::SetEnvironmentVariable does.
$UserPath = (Get-Item "HKCU:\Environment").GetValue("Path", "", "DoNotExpandEnvironmentNames")
$Entries  = @($UserPath -split ";" | Where-Object { $_ -ne "" })

if ($Entries | Where-Object { $_.TrimEnd("\") -ieq $ScriptDir.TrimEnd("\") }) {
    Write-Host "Already installed - $ScriptDir is already on your PATH"
} else {
    Set-ItemProperty -Path "HKCU:\Environment" -Name Path -Type ExpandString -Value ((@($Entries) + $ScriptDir) -join ";")
    # Set-and-clear a dummy variable so Windows tells new terminals PATH changed
    [Environment]::SetEnvironmentVariable("COSMO_TMP", "1", "User")
    [Environment]::SetEnvironmentVariable("COSMO_TMP", $null, "User")
    Write-Host "Added $ScriptDir to your user PATH"
}

Write-Host ""
Write-Host "Setup complete! Open a NEW PowerShell or Command Prompt window"
Write-Host "then type 'cosmo' from anywhere to launch the app."