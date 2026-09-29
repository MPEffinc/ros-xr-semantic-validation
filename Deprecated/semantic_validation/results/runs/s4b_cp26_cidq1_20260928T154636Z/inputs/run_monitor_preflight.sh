#!/bin/bash
set -eo pipefail
source /opt/ros/humble/setup.bash
source /home/noah/ws_moveit/install/setup.bash
source /monitor_ws/install/setup.bash
export PYTHONPATH=/code:/d1deps:${PYTHONPATH:-}
exec python3 /code/monitor_path_preflight.py --regime "$1"
