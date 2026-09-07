#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
test $# -eq 1 || { echo "usage: $0 <run-id>" >&2; exit 2; }
source "$root/semantic_validation/logs/$1/state.env"
remote_log="$(ssh rosxr "find '$remote_dir' -maxdepth 1 -type f -name 'semantic_robot_sink_*.jsonl' -print -quit")"
test -n "$remote_log" || { echo 'Pi sink JSONL not found' >&2; exit 3; }
scp "rosxr:$remote_log" "$result_dir/pi_sink.jsonl"
python3 "$root/semantic_validation/harness/analyze_spes_ros_pi.py" --adapter "$result_dir/adapter.jsonl" --pi "$result_dir/pi_sink.jsonl" --output "$result_dir/correlation.json"
