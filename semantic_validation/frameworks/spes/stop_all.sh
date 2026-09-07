#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "$0")/spes_stop_all.sh" "$@"
