#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${CLASSIFIER_BUNDLE_URL:?Approved HTTPS classifier bundle required}"
: "${CLASSIFIER_BUNDLE_SHA256:?Approved classifier checksum required}"
export INBOX_RUNTIME_PROFILE=render-free CLASSIFIER_RUNTIME=onnx
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python -m pip install -r deploy/requirements-render.txt
python -m pip check
python deploy/install_classifier.py
python -m deploy.check_render_runtime
(cd frontend && npm ci && npm run build)
