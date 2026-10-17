param([string]$RuntimeHome = '')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Install uv from https://docs.astral.sh/uv/getting-started/installation/ and reopen PowerShell.'
}
if (-not $RuntimeHome) {
    if (Test-Path -LiteralPath "$PSScriptRoot\ai-runtime.json") {
        $RuntimeHome = (Get-Content -Raw -LiteralPath "$PSScriptRoot\ai-runtime.json" | ConvertFrom-Json).home
    } else {
        $RuntimeHome = 'H:\CodexStorage\ivp-ai\ai-runtime'
    }
}
$RuntimeHome = [System.IO.Path]::GetFullPath($RuntimeHome)
if (-not (Test-Path -LiteralPath ([System.IO.Path]::GetPathRoot($RuntimeHome)))) {
    throw 'The requested runtime drive is unavailable. Connect it or specify -RuntimeHome on an available drive.'
}
$env:UV_CACHE_DIR = Join-Path $RuntimeHome 'uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $RuntimeHome 'python'
uv venv --allow-existing --python 3.11 (Join-Path $RuntimeHome 'venv')
if ($LASTEXITCODE -ne 0) { throw 'Could not create the AI Python environment.' }
$aiPython = Join-Path $RuntimeHome 'venv\Scripts\python.exe'
uv pip install --python $aiPython 'torch==2.11.0+cu128' 'torchvision==0.26.0+cu128' --index-url https://download.pytorch.org/whl/cu128
if ($LASTEXITCODE -ne 0) { throw 'PyTorch installation failed. Check available disk space and network access.' }
uv pip install --python $aiPython -r requirements-ai.txt
if ($LASTEXITCODE -ne 0) { throw 'AI dependency installation failed.' }
@{ home = $RuntimeHome } | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot\ai-runtime.json" -Encoding utf8
Write-Host 'AI runtime ready. Models download on first use.'
