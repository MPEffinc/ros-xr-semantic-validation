#!/usr/bin/env bash

set -Eeuo pipefail

WORKSPACE_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$WORKSPACE_ROOT/semantic_validation/harness/run_no_quest_validation.py" "$@"
