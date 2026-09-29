#!/usr/bin/env bash
# One-time workspace build inside the long-lived simulation container.
set -eo pipefail
source /opt/ros/jazzy/setup.bash
set -u
cd /ws
colcon build --event-handlers console_direct+ --cmake-args -DBUILD_TESTING=OFF
echo "[build_ws] done"
