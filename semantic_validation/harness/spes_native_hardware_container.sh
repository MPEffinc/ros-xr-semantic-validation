#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/humble/setup.bash
set -u
export HOME=/tmp/spes-home
mkdir -p "$HOME"
mkdir -p /tmp/spes_overlay
cp -a /repo/semantic_validation/targets/spes_teleop/teleop /tmp/spes_overlay/teleop
cp /repo/semantic_validation/instrumented/spes_frontend/index.html /tmp/spes_overlay/teleop/index.html
cp -a /repo/semantic_validation/instrumented/spes_frontend/assets/. /tmp/spes_overlay/teleop/assets/
python3 - "$SIDEBAND_PORT" <<'PY'
import pathlib,sys
p=pathlib.Path('/tmp/spes_overlay/teleop/assets/quest-operator.js')
s=p.read_text(); old='const host = global.location ? global.location.host : "127.0.0.1:4443";'
new=f'const host = global.location ? `${{global.location.hostname}}:{sys.argv[1]}` : "127.0.0.1:{sys.argv[1]}";'
if s.count(old)!=1: raise SystemExit('sideband URL anchor mismatch')
p.write_text(s.replace(old,new))
PY
export PYTHONPATH="/tmp/spes_overlay:${PYTHONPATH:-}"
cleanup() {
  kill -TERM "${native_pid:-}" "${sideband_pid:-}" 2>/dev/null || true
  wait "${native_pid:-}" "${sideband_pid:-}" 2>/dev/null || true
}
trap cleanup EXIT TERM INT
python3 /repo/semantic_validation/harness/spes_native_sideband.py --run-id "$RUN_ID" --port "$SIDEBAND_PORT" --result-dir /out --topic /robot_target_pose > /out/sideband.stdout.log 2>&1 &
sideband_pid=$!
python3 -m teleop.ros2 --omit-current-pose --host 0.0.0.0 --port "$PRODUCTION_PORT" --ros-args -r target_frame:=/robot_target_pose > /out/native.stdout.log 2>&1 &
native_pid=$!
wait -n "$native_pid" "$sideband_pid"
