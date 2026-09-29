#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/humble/setup.bash
python3 -m pip install --no-deps -e /official

workspace=/results/rosmonitoring/humble/edge_ws_03
mkdir -p "${workspace}/src" /results/rosmonitoring/humble/edge_logs_03
cp -a /results/inputs/teleop_bridge_msgs_src "${workspace}/src/teleop_bridge_msgs"
PYTHONPATH=/official/src python3 -m rosmonitoring.cli generate /results/inputs/rosmonitoring_edge_config.yaml --ros-version ros2 --output "${workspace}/src"
cd "${workspace}"
colcon build --event-handlers console_direct+
source "${workspace}/install/setup.bash"

python3 /results/inputs/edge_oracle_fixture.py --mode custom --port 18765 --log /results/rosmonitoring/humble/edge_logs_03/custom_oracle.jsonl > /results/stdout/custom_oracle_03.log 2> /results/stderr/custom_oracle_03.log &
oracle_custom=$!
python3 /results/inputs/edge_oracle_fixture.py --mode disconnect --port 18767 --log /results/rosmonitoring/humble/edge_logs_03/disconnect_oracle.jsonl > /results/stdout/disconnect_oracle_03.log 2> /results/stderr/disconnect_oracle_03.log &
oracle_disconnect=$!
python3 /results/inputs/edge_oracle_fixture.py --mode hang --port 18768 --log /results/rosmonitoring/humble/edge_logs_03/hang_oracle.jsonl > /results/stdout/hang_oracle_03.log 2> /results/stderr/hang_oracle_03.log &
oracle_hang=$!
sleep 1

pids="${oracle_custom} ${oracle_disconnect} ${oracle_hang}"
for id in s4b_custom_guard s4b_absent_guard s4b_disconnect_guard s4b_hang_guard; do
  ros2 run monitor "${id}" > "/results/stdout/${id}_03.log" 2> "/results/stderr/${id}_03.log" &
  pids="${pids} $!"
done

cleanup() {
  kill ${pids} 2>/dev/null || true
  wait ${pids} 2>/dev/null || true
}
trap cleanup EXIT
sleep 3
python3 /results/inputs/edge_case_probe.py
