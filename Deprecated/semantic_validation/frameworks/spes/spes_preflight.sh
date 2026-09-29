#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
sg docker -c "docker info --format '{{.ServerVersion}}' >/dev/null; docker compose -f '$root/ros_env/compose.yaml' config --quiet"
ssh rosxr 'bash -lc '\''source /opt/ros/humble/setup.bash; source "$HOME/ros2_ws/install/setup.bash"; hostname; test -d "$HOME/semantic_robot_endpoint_logs"; ros2 pkg executables semantic_robot_endpoint | grep -qx "semantic_robot_endpoint semantic_robot_sink"'\'''
echo 'PASS: Docker/Pi observation-only Spes preflight.'
