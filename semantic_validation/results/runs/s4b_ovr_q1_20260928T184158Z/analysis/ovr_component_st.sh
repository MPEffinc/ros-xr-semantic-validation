#!/bin/bash
# No-Gazebo OpenVR production component run (one mode x case). Trial-owned container only.
set -eo pipefail
export TRIAL_ROOT=/results
source /opt/ros/jazzy/setup.bash
source /ws/install/setup.bash
export PYTHONPATH=/code:/ovrdeps:${PYTHONPATH:-}
pids=()
if [ "$MODE" = b2 ]; then
  source /monitor_ws/install/setup.bash
  export XR_D3_PROPERTY_LOG=/results/property.jsonl
  python3 -u /official/oracle/TLOracle/oracle.py --online --discrete --property ovr_tloracle_property --port 18851 > /results/oracle.stdout 2> /results/oracle.stderr & pids+=($!)
  sleep 1
  python3 /diagcopy/guard_st.py > /results/monitor.stdout 2> /results/monitor.stderr & pids+=($!)
  python3 /code/ovr_nodes.py > /results/stripper.stdout 2> /results/stripper.stderr & pids+=($!)
fi
python3 /code/ovr_production.py > /results/production.stdout 2> /results/production.stderr & pids+=($!)
python3 /analysis/ovr_component_driver.py
for p in "${pids[@]}"; do kill -INT "$p" 2>/dev/null || true; done
sleep 1
for p in "${pids[@]}"; do kill -KILL "$p" 2>/dev/null || true; done
