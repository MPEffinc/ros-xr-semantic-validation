#!/bin/bash
set -eo pipefail
source /opt/ros/humble/setup.bash
source /home/noah/ws_moveit/install/setup.bash
source /monitor_ws/install/setup.bash
export PYTHONPATH=/code:/d1deps:${PYTHONPATH:-}
export TRIAL_ROOT=/results
export INFO_REGIME="$1"
exec python3 /code/d3_monitor_tick_preflight.py --regime "$1"
