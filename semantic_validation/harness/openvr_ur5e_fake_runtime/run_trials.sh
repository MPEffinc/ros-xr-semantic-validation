#!/usr/bin/env bash
set -eo pipefail

result_dir="${1:?result directory required}"
mkdir -p "${result_dir}"
source /opt/ros/jazzy/setup.bash
cd /ws
colcon build --packages-select quest_bridge --event-handlers console_direct+
source /ws/install/setup.bash
set -u

run_trial() {
  local trial_id="$1"
  local valid="$2"
  local tracking_result="$3"
  local grip="$4"
  local grip_sequence="${5:-}"
  local node_pid
  local capture_pid

  python3 /harness/capture_pose.py --duration 1.6 \
    >"${result_dir}/${trial_id}_pose.json" &
  capture_pid=$!
  sleep 0.2
  OPENVR_FAKE_VALID="${valid}" \
  OPENVR_FAKE_TRACKING_RESULT="${tracking_result}" \
  OPENVR_FAKE_GRIP="${grip}" \
  OPENVR_FAKE_GRIP_SEQUENCE="${grip_sequence}" \
  PYTHONPATH="/harness:${PYTHONPATH:-}" \
    setsid /ws/install/quest_bridge/lib/quest_bridge/quest_teleop \
      >"${result_dir}/${trial_id}_node.log" 2>&1 &
  node_pid=$!
  wait "${capture_pid}"
  kill -KILL -- "-${node_pid}" || true
  wait "${node_pid}" || true
}

run_trial V1 true Running_OK true
run_trial V2 true Running_OutOfRange true
run_trial V3 false Running_OK true
run_trial V4 true Running_OK true "1:20,0:20,1:20"

python3 - "${result_dir}" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
summary = {}
for trial in ("V1", "V2", "V3", "V4"):
    data = json.loads((root / f"{trial}_pose.json").read_text())
    summary[trial] = {
        "count": data["count"],
        "first": data["messages"][0] if data["messages"] else None,
        "last": data["messages"][-1] if data["messages"] else None,
    }
print(json.dumps(summary, indent=2, sort_keys=True))
PY
