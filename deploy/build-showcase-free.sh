#!/usr/bin/env sh
# Preparation only; not connected to Render until separately approved.
set -eu
# Render supplies env vars at build and runtime. Keep this credential out of
# dependency installers and frontend build subprocesses.
# Clear any inherited export attribute before keeping the token in this shell.
unset github_token
github_token=${SHOWCASE_GITHUB_TOKEN:-}
unset SHOWCASE_GITHUB_TOKEN
if [ -n "$github_token" ] && [ -n "${SHOWCASE_ARTIFACT_DESCRIPTOR:-}" ]; then
    echo 'Choose only one artifact delivery method.' >&2
    exit 1
fi
if [ -n "$github_token" ]; then
    SHOWCASE_GITHUB_TOKEN="$github_token" python -m showcase.github_artifacts --output local_models/showcase-free
elif [ -n "${SHOWCASE_ARTIFACT_DESCRIPTOR:-}" ]; then
    python -m showcase.acquire_artifacts --descriptor "$SHOWCASE_ARTIFACT_DESCRIPTOR" --output local_models/showcase-free
else
    echo 'Provide approved private artifact access.' >&2
    exit 1
fi
unset github_token
python -m pip install -r deploy/requirements-showcase-free.txt
python -m pip check
npm --prefix frontend ci
npm --prefix frontend run build:showcase
