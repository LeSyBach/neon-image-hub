& wsl -d Ubuntu-22.04 -u root --cd $PSScriptRoot -- /usr/bin/docker compose -f compose.yaml -f compose.worker-local.yaml -f compose.worker-b-local.yaml --profile local-worker --profile local-worker-b stop worker-local worker-b-local
exit $LASTEXITCODE
