#!/usr/bin/env sh
set -eu
# A file path is nonsecret. Credentials/URLs belong only in the operator descriptor.
exec python -m uvicorn showcase.free_app:application --factory --host 0.0.0.0 --port "${PORT:-10000}" --workers 1 --no-access-log --timeout-keep-alive 5
