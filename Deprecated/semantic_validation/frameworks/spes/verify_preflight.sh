#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
git -C "$root/semantic_validation/targets/spes_teleop" rev-parse HEAD
test -f "$root/semantic_validation/harness/spes_ros_callback_adapter.py"
docker compose -f "$root/ros_env/compose.yaml" config --quiet
echo "PRECHECK_ONLY: Docker daemon access and Pi sink start are separate checks."
