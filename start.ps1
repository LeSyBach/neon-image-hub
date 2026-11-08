param([switch]$WithWorker)
$ErrorActionPreference = 'Stop'
$statePath = Join-Path $PSScriptRoot '.wsl-keepalive.json'
$alive = $false
if (Test-Path -LiteralPath $statePath) {
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    $ownedProcess = Get-Process -Id $state.pid -ErrorAction SilentlyContinue
    $alive = $null -ne $ownedProcess -and $ownedProcess.ProcessName -eq 'wsl' -and $ownedProcess.StartTime.ToUniversalTime().ToString('o') -eq $state.started
}
if (-not $alive) {
    $ownedProcess = Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu-22.04','-u','root','--','sleep','infinity') -WindowStyle Hidden -PassThru
    @{pid=$ownedProcess.Id;started=$ownedProcess.StartTime.ToUniversalTime().ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $statePath
}
& wsl -d Ubuntu-22.04 -u root --cd $PSScriptRoot -- bash -lc 'systemctl start docker && python3 scripts/init.py && /usr/bin/docker compose up -d --build'
if ($LASTEXITCODE -ne 0) { throw 'Server startup failed. See Docker Compose logs.' }
if (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.credentials/beszel-agent.env')) {
    & wsl -d Ubuntu-22.04 -u root --cd $PSScriptRoot -- /usr/bin/docker compose --profile monitor-agent up -d beszel-agent
}
& wsl -d Ubuntu-22.04 -u root --cd $PSScriptRoot -- python3 scripts/setup_notifications.py
Write-Host 'Kho ảnh: http://127.0.0.1:8080'
Write-Host 'Giám sát: http://127.0.0.1:8090'
Write-Host 'Log điện thoại: http://127.0.0.1:8091'
