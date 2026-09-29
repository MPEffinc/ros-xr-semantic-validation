#!/usr/bin/env bash
# Generate and build the official ROSMonitoring monitor for the OpenVR I_FULL envelope (Jazzy).
set -eo pipefail
source /opt/ros/jazzy/setup.bash
export PYTHONPATH=/official/src:${PYTHONPATH:-}
python3 -m rosmonitoring.cli validate /code/ovr_rosmonitoring.yaml --ros-version ros2
mkdir -p /out/monitor_ws/src
python3 -m rosmonitoring.cli generate /code/ovr_rosmonitoring.yaml --ros-version ros2 --output /out/monitor_ws/src
cd /out/monitor_ws
colcon build --event-handlers console_direct+
