param([string]$RuntimeRoot = 'H:\CodexStorage\ivp-sem5-runtime', [switch]$Dev)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Install uv from https://docs.astral.sh/uv/getting-started/installation/ and reopen this launcher.'
}
$env:UV_CACHE_DIR = Join-Path $RuntimeRoot 'uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $RuntimeRoot 'python'
$env:UV_PYTHON_BIN_DIR = Join-Path $RuntimeRoot 'bin'
$env:TEMP = Join-Path $RuntimeRoot 'tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Path $env:TEMP -Force | Out-Null
$runtimeVenv = Join-Path $RuntimeRoot 'venv'
New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null
& uv python install 3.11
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 installation failed.' }
$runtimePython = Join-Path $runtimeVenv 'Scripts\python.exe'
if (Test-Path -LiteralPath $runtimePython) {
    & $runtimePython -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 11) else 1)"
    if ($LASTEXITCODE -ne 0) {
        throw 'The existing environment is not usable Python 3.11. Choose a different -RuntimeRoot.'
    }
} else {
    & uv venv --python 3.11 --managed-python $runtimeVenv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 environment creation failed.' }
}
$requirements = if ($Dev) { 'requirements-dev.txt' } else { 'requirements.txt' }
& uv pip install --python $runtimePython -r $requirements
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the network connection and retry Setup.ps1.' }
foreach ($program in @('ffmpeg', 'ffprobe')) {
    if (-not (Get-Command $program -ErrorAction SilentlyContinue)) {
        Write-Warning "$program is missing. Install FFmpeg and add its bin directory to PATH for video support."
    }
}
@{root=[System.IO.Path]::GetFullPath($RuntimeRoot)} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime.json') -Encoding utf8
Write-Host 'Setup complete. Double-click Start.cmd to open IVP Lab.'
