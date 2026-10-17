$ErrorActionPreference = 'Stop'
$runRoot = Join-Path $PSScriptRoot 'runs'
if (Test-Path -LiteralPath $runRoot) {
    Get-ChildItem -LiteralPath $runRoot -Directory | ForEach-Object {
        $stateFile = Join-Path $_.FullName 'status.json'
        if (Test-Path -LiteralPath $stateFile) {
            $jobState = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
            if ($jobState.state -in @('queued', 'running', 'encoding')) {
                New-Item -ItemType File -Path (Join-Path $_.FullName 'cancel.request') -Force | Out-Null
            }
        }
    }
}
$processFile = Join-Path $PSScriptRoot 'temp\server.json'
if (Test-Path -LiteralPath $processFile) {
    $savedProcess = Get-Content -LiteralPath $processFile -Raw | ConvertFrom-Json
    $serverProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($savedProcess.pid)"
    $appPath = Join-Path $PSScriptRoot 'app.py'
    $webPath = Join-Path $PSScriptRoot 'web_server.py'
    if ($serverProcess -and (($serverProcess.CommandLine.Contains($appPath) -and $serverProcess.CommandLine.Contains('streamlit')) -or $serverProcess.CommandLine.Contains($webPath))) {
        Stop-Process -Id $savedProcess.pid
        Write-Host 'Traffic Lab stopped. Active video workers have been asked to cancel.'
    } else {
        Write-Host 'No matching Traffic Lab server is running.'
    }
}
