param([string]$RuntimeRoot = 'H:\CodexStorage\ivp-ai')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Install uv from https://docs.astral.sh/uv/getting-started/installation/ and reopen this launcher.'
}
$env:UV_CACHE_DIR = Join-Path $RuntimeRoot 'uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $RuntimeRoot 'python'
$runtimeVenv = Join-Path $RuntimeRoot 'venv'
New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null
& uv venv --python 3.11 --allow-existing $runtimeVenv
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 environment creation failed.' }
& uv pip install --python (Join-Path $runtimeVenv 'Scripts\python.exe') -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the network connection and retry Setup.ps1.' }
foreach ($program in @('ffmpeg', 'ffprobe')) {
    if (-not (Get-Command $program -ErrorAction SilentlyContinue)) {
        Write-Warning "$program is missing. Install FFmpeg and add its bin directory to PATH for video support."
    }
}
Write-Host 'Setup complete. Double-click Start.cmd to open Traffic Lab.'
