#!/usr/bin/env sh
# Preparation only; not connected to Render until separately approved.
set -eu
: "${SHOWCASE_ARTIFACT_DESCRIPTOR:?Provide an approved build-time descriptor file}"
python -m pip install -r deploy/requirements-showcase-free.txt
python -m pip check
python -m showcase.acquire_artifacts --descriptor "$SHOWCASE_ARTIFACT_DESCRIPTOR" --output local_models/showcase-free
npm --prefix frontend ci
npm --prefix frontend run build:showcase
