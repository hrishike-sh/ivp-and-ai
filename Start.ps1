$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    & (Join-Path $PSScriptRoot 'Setup.ps1')
}
& $projectPython (Join-Path $PSScriptRoot 'launch.py')
if ($LASTEXITCODE -ne 0) { throw 'The app could not start. See the message above and temp/server.log.' }
