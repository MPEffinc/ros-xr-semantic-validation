#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
run_id="${1:-spes_ros_pi_$(date -u +%Y%m%dT%H%M%SZ)}"
run_dir="$root/semantic_validation/logs/$run_id"
test ! -e "$run_dir" || { echo "refusing to overwrite $run_dir" >&2; exit 2; }
mkdir -p "$run_dir"
result_dir="$run_dir/spes_runtime"
remote_dir="/home/cclab/semantic_robot_endpoint_logs/$run_id"
pi_pid="$(ssh rosxr "mkdir -p '$remote_dir'; nohup bash -lc 'source /opt/ros/humble/setup.bash; source \$HOME/ros2_ws/install/setup.bash; exec ros2 run semantic_robot_endpoint semantic_robot_sink --ros-args -p log_dir:=$remote_dir' > '$remote_dir/sink.stdout' 2>&1 & printf '%s\\n' \$!")"
printf 'run_id=%q\nrun_dir=%q\nresult_dir=%q\nremote_dir=%q\npi_pid=%q\n' "$run_id" "$run_dir" "$result_dir" "$remote_dir" "$pi_pid" > "$run_dir/state.env"
sleep 3
set +e
sg docker -c "docker run --rm --network host --user $(id -u):$(id -g) -e HOME=/tmp -v '$root:/workspace' -w /workspace ros-xr-humble:local bash -lc 'source /opt/ros/humble/setup.bash; PYTHONPATH=/workspace/semantic_validation/harness:\$PYTHONPATH python3 semantic_validation/harness/spes_ros_pi_smoke.py --run-id $run_id --result-dir semantic_validation/logs/$run_id/spes_runtime'" | tee "$run_dir/container.stdout"
rc=${PIPESTATUS[0]}
set -e
printf 'container_exit=%q\n' "$rc" >> "$run_dir/state.env"
exit "$rc"
