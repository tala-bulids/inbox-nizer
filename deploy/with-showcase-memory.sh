#!/usr/bin/env sh
set -eu
# Set before Python/native libraries start. Fixed thresholds prevent glibc from
# retaining the encoder's large temporary tensors in growing per-thread heaps.
# These control allocation only: graph, weights, precision and token limit stay
# unchanged. Use the same launcher for serving and constrained qualification.
export MALLOC_ARENA_MAX=2
export MALLOC_MMAP_THRESHOLD_=131072
export MALLOC_TRIM_THRESHOLD_=131072
exec "$@"
