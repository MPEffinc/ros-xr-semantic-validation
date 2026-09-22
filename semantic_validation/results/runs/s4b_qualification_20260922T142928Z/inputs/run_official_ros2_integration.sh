#!/usr/bin/env bash
set -eo pipefail

source "/opt/ros/${ROS_DISTRO}/setup.bash"
python3 -m pip install ${PIP_BREAK_SYSTEM_PACKAGES:+--break-system-packages} --no-deps -e /official
python3 -m pip freeze | sort
python3 -m rosmonitoring.cli --help
python3 -m pytest -vv -s /official/tests/test_ros2_integration.py
