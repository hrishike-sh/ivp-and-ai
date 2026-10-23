param([string]$RuntimeRoot)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not $RuntimeRoot) {
    $settingsPath = Join-Path $PSScriptRoot 'runtime.json'
    $RuntimeRoot = if (Test-Path -LiteralPath $settingsPath) { (Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json).root } else { 'H:\CodexStorage\ivp-sem5-runtime' }
}
$projectPython = Join-Path $RuntimeRoot 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'The H-drive Python environment is missing. See INSTALL.md. No packages were installed on C:.'
}
& $projectPython (Join-Path $PSScriptRoot 'launch.py')
if ($LASTEXITCODE -ne 0) { throw 'The app could not start. See the message above and temp/server.log.' }
