#!/usr/bin/env bash

set -u

VALIDATION_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$VALIDATION_ROOT/harness/run_semantic_validation.py" "$@"
