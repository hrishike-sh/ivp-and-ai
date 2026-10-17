$ErrorActionPreference = 'Stop'
$visionRoot = 'H:\CodexStorage\ivp-ai\ollama'
$record = Join-Path $visionRoot 'process.json'
if (-not (Test-Path -LiteralPath $record)) { Write-Host 'No project Ollama process record found.'; exit }
$processInfo = Get-Content -LiteralPath $record -Raw | ConvertFrom-Json
$process = Get-Process -Id $processInfo.pid -ErrorAction SilentlyContinue
if (-not $process) { Write-Host 'Project Ollama server is already stopped.'; exit }
$expected = [System.IO.Path]::GetFullPath((Join-Path $visionRoot 'runtime\ollama.exe'))
if ([System.IO.Path]::GetFullPath($process.Path) -ne $expected) { throw 'Process identity changed; refusing to stop an unrelated process.' }
Stop-Process -Id $process.Id
Write-Host 'Project Ollama server stopped. Models and reviews remain on H:.'
