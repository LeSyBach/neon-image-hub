param([ValidateSet('sd-turbo','dreamshaper-8-lcm')][string]$Model = 'sd-turbo')
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'start.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Server startup failed.' }
$files = @('-f','compose.yaml','-f','compose.worker-local.yaml','-f','compose.worker-b-local.yaml','--profile','local-worker','--profile','local-worker-b')
if ($Model -eq 'dreamshaper-8-lcm') {
    & wsl -d Ubuntu-22.04 -u root --cd $PSScriptRoot -- /usr/bin/docker compose @files stop worker-local
    & wsl -d Ubuntu-22.04 -u root --cd $PSScriptRoot -- python3 scripts/setup_worker_b.py
    $selected = 'worker-b-local'
    $pausePath = Join-Path $PSScriptRoot 'data/worker-3.1/pause'
} else {
    & wsl -d Ubuntu-22.04 -u root --cd $PSScriptRoot -- /usr/bin/docker compose @files stop worker-b-local
    & wsl -d Ubuntu-22.04 -u root --cd $PSScriptRoot -- python3 scripts/setup_worker.py
    $selected = 'worker-local'
    $pausePath = Join-Path $PSScriptRoot 'data/worker-2.1/pause'
}
if ($LASTEXITCODE -ne 0) { throw 'Worker setup failed.' }
if (Test-Path -LiteralPath $pausePath) { Remove-Item -LiteralPath $pausePath }
& wsl -d Ubuntu-22.04 -u root --cd $PSScriptRoot -- /usr/bin/docker compose @files up -d --build $selected
if ($LASTEXITCODE -ne 0) { throw 'Worker startup failed.' }
