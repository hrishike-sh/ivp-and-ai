param([string]$RuntimeRoot = 'H:\CodexStorage\ivp-ai')
# RuntimeRoot selects the existing Python environment only. The portable
# Ollama root is intentionally fixed, matching ollama_runtime.py and Stop-Ollama.ps1.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$python = Join-Path $RuntimeRoot 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'The IVP Python environment is missing. Run Setup.ps1 first; use the same -RuntimeRoot for both scripts.'
}
$visionRoot = 'H:\CodexStorage\ivp-ai\ollama'
if (-not (Test-Path -LiteralPath 'H:\')) { throw 'H: drive is required for this local vision installation.' }
$archive = Join-Path $visionRoot 'downloads\ollama-v0.40.0.zip'
New-Item -ItemType Directory -Force (Split-Path $archive) | Out-Null
if (-not (Test-Path -LiteralPath $archive)) {
    & curl.exe -L --fail --retry 3 --output $archive 'https://github.com/ollama/ollama/releases/download/v0.40.0/ollama-windows-amd64.zip'
    if ($LASTEXITCODE -ne 0) { throw 'Runtime download failed; archive remains on H:.' }
}
$expected = '3623e256762ca89bd6fa99b0cc4106401919ce9df926411673e632e3ea287bb5'
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLower() -ne $expected) {
    throw 'Runtime archive checksum mismatch. Wait for any download to finish or replace the archive before retrying.'
}
$runtime = Join-Path $visionRoot 'runtime'
New-Item -ItemType Directory -Force $runtime | Out-Null
Expand-Archive -LiteralPath $archive -DestinationPath $runtime -Force
& $python -m traffic_ai.ollama_runtime pull
if ($LASTEXITCODE -ne 0) { throw 'Local vision model setup failed; inspect the messages and H: server.log.' }
Write-Host 'Local vision is ready. Runtime, models, profile, logs and temporary files are on H:.'
