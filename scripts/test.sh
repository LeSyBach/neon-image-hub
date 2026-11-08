#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
docker compose run --rm --no-deps -v "$(pwd)/tests:/app/tests:ro" -v "$(pwd)/worker:/app/worker:ro" -v "$(pwd)/requirements-test.txt:/app/requirements-test.txt:ro" api sh -c 'pip install --no-cache-dir -q -r requirements-test.txt && python -m pytest -q /app/tests'
