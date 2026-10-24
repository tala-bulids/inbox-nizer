#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${PORT:?Render port required}"
if [[ "${APP_ENV:-}" != production ]]; then
    printf '%s\n' 'APP_ENV must be production for the hosted service' >&2
    exit 1
fi
: "${DATABASE_URL:?Runtime database connection required}"
: "${OAUTH_TOKEN_KEYS:?Existing encryption keys required}"
: "${GOOGLE_CLIENT_FILE:?Existing Google web client file required}"
: "${BROWSER_ORIGIN:?Exact HTTPS browser origin required}"
: "${GOOGLE_REDIRECT_URI:?Existing Gmail callback required}"
: "${GOOGLE_LOGIN_REDIRECT_URI:?Existing login callback required}"
export INBOX_RUNTIME_PROFILE=render-free CLASSIFIER_RUNTIME=onnx
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
# No migrations, downloads or inference at startup. Forwarded trust retains
# Uvicorn's loopback default unless the operator supplies verified proxy ranges.
exec python -m uvicorn deploy.render_app:application --factory --host 0.0.0.0 --port "$PORT" --workers 1 --proxy-headers --no-access-log
