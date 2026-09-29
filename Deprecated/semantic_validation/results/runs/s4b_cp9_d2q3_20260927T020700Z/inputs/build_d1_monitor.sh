#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/humble/setup.bash
source /home/noah/ws_moveit/install/setup.bash
export PYTHONPATH=/official/src:${PYTHONPATH:-}
python3 -m rosmonitoring.cli validate /code/d1_rosmonitoring.yaml --ros-version ros2
mkdir -p /results/monitor_ws/src
python3 -m rosmonitoring.cli generate /code/d1_rosmonitoring.yaml --ros-version ros2 --output /results/monitor_ws/src
cd /results/monitor_ws
colcon build --event-handlers console_direct+
