#!/usr/bin/env bash

set -Eeuo pipefail

VALIDATION_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PY_DEPS=${SEMANTIC_PY_DEPS:-/tmp/ros_xr_semantic_deps}

node "$VALIDATION_ROOT/harness/spes_frontend_s1.mjs" \
  --output "$VALIDATION_ROOT/logs/s1_frontend.jsonl"

if [[ ! -d "$PY_DEPS/numpy" ]]; then
  printf 'Missing Python dependencies at %s\n' "$PY_DEPS" >&2
  printf 'See semantic_validation/README.md for the non-root setup command.\n' >&2
  exit 2
fi

PYTHONPATH="$PY_DEPS:$VALIDATION_ROOT/targets/spes_teleop${PYTHONPATH:+:$PYTHONPATH}" \
  python3 "$VALIDATION_ROOT/harness/spes_server_replay.py" \
  --output "$VALIDATION_ROOT/logs/s1_server_replay.jsonl"
