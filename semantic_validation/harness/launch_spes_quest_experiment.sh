#!/usr/bin/env bash
set -euo pipefail

validation_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Compatibility entrypoint: hardware trials are now fully in-headset and detached.
exec "${validation_root}/start_quest_experiment.sh" "$@"
