& wsl -d Ubuntu-22.04 -u root --cd $PSScriptRoot -- /usr/bin/docker compose -f compose.yaml -f compose.worker-local.yaml -f compose.worker-b-local.yaml --profile monitor-agent --profile local-worker --profile local-worker-b down
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$statePath = Join-Path $PSScriptRoot '.wsl-keepalive.json'
if (Test-Path -LiteralPath $statePath) {
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    $ownedProcess = Get-Process -Id $state.pid -ErrorAction SilentlyContinue
    if ($null -ne $ownedProcess -and $ownedProcess.ProcessName -eq 'wsl' -and $ownedProcess.StartTime.ToUniversalTime().ToString('o') -eq $state.started) {
        Stop-Process -Id $ownedProcess.Id
    }
}
