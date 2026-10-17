param([string]$RuntimeRoot = 'H:\CodexStorage\ivp-ai')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $RuntimeRoot 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'The H-drive Python environment is missing. See INSTALL.md. No packages were installed on C:.'
}
& $projectPython (Join-Path $PSScriptRoot 'launch.py')
if ($LASTEXITCODE -ne 0) { throw 'The app could not start. See the message above and temp/server.log.' }
