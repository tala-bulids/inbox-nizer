#!/usr/bin/env sh
set -eu
# Artifact credentials are only needed during build, not by the web process.
unset SHOWCASE_GITHUB_TOKEN
exec sh "$(dirname "$0")/with-showcase-memory.sh" python -m uvicorn showcase.free_app:application --factory --host 0.0.0.0 --port "${PORT:-10000}" --workers 1 --no-access-log --timeout-keep-alive 5
