#!/usr/bin/env bash
# Runs inside ros-xr-horus-nav2-jazzy:local (see ../PROTOCOL.md). Mounts:
#   /src/horus_ros2 (ro)  /ac (ro, experiments/)  /deprecated_env (ro)  /out (rw)
set -Eeuo pipefail
TRIALS="${AC_TRIALS:-5}"
CASES="${AC_CASES:-C1_normal,C2_release_executing,C3_ttl_expiry_executing,C4_disconnect_reconnect,C5_handoff,C5F_handoff_back_to_back,C6_catalog_change_during_lease,C7_teleop_stream_after_release}"
BASELINES="${AC_BASELINES:-B0_stock B1_existing_primitives}"
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=92
PIDS=()
cleanup() { chown -R "${AC_UID:-0}:${AC_UID:-0}" /out 2>/dev/null || true; for p in "${PIDS[@]}"; do kill -- -"$p" 2>/dev/null || kill "$p" 2>/dev/null || true; done; wait 2>/dev/null || true; }
trap cleanup EXIT
set +u; source /opt/ros/jazzy/setup.bash; set -u

build() { # $1 name $2 patch-or-empty
  local ws=/tmp/ws_$1
  mkdir -p "$ws/src" && cp -a /src/horus_ros2/. "$ws/src/"
  rm -rf "$ws/src/.git"
  if [[ -n "$2" ]]; then patch -d "$ws/src" -p1 <"$2" >"/out/patch_$1.log"; fi
  (cd "$ws" && colcon build --event-handlers console_direct+ \
     --cmake-args -DENABLE_WEBRTC=OFF -DBUILD_TESTING=OFF >"/out/build_$1.log" 2>&1) \
     || { tail -60 "/out/build_$1.log"; exit 3; }
  grep -E '^Summary' "/out/build_$1.log" || true
}
echo "[1] build baselines"; date -u +%FT%TZ
build B0_stock ""
build B1_existing_primitives /ac/baselines/b1_existing_primitives.patch

echo "[2] Nav2 loopback"
setsid ros2 topic pub --rate 10 /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
  '{header: {frame_id: map}, pose: {pose: {position: {x: -2.0, y: -0.5}, orientation: {w: 1.0}}}}' \
  >/out/pose_seed.log 2>&1 & SEED=$!; PIDS+=($SEED)
setsid ros2 launch nav2_bringup tb3_loopback_simulation.launch.py use_rviz:=False \
  use_composition:=False autostart:=True use_robot_state_pub:=True >/out/nav2.log 2>&1 &
PIDS+=($!)
for i in $(seq 1 120); do
  if ros2 lifecycle get /bt_navigator 2>/dev/null | grep -q '^active'; then break; fi; sleep 1
done
ros2 lifecycle get /bt_navigator | grep -q '^active' || { tail -80 /out/nav2.log; exit 4; }
kill -- -"$SEED" 2>/dev/null || true
echo "  Nav2 active after ${i}s"

for B in $BASELINES; do
  echo "[3] baseline $B"
  set +u; source "/tmp/ws_$B/install/setup.bash"; set -u
  setsid ros2 run horus_unity_bridge horus_unity_bridge_node --ros-args \
    -p tcp_ip:=127.0.0.1 -p tcp_port:=11000 -p transport_protocol:=horuslink \
    -p horuslink_bulk_port:=11001 -p horuslink_keepalive_ms:=0 \
    -p multi_operator.control_lease_ttl_ms:=1200 -p log_protocol_messages:=false \
    -p webrtc.enabled:=false >"/out/bridge_$B.log" 2>&1 & BR=$!; PIDS+=($BR)
  setsid ros2 run horus_backend horus_backend_node --ros-args -p tcp_port:=18080 \
    -p unity_tcp_port:=11000 >"/out/backend_$B.log" 2>&1 & BE=$!; PIDS+=($BE)
  for _ in $(seq 1 100); do nc -z 127.0.0.1 11000 && nc -z 127.0.0.1 11001 && break; sleep 0.1; done
  python3 /ac/harness/ac_probe.py --baseline "$B" --trials "$TRIALS" --cases "$CASES" \
    --out /out/trials.jsonl 2>&1 | tee "/out/probe_$B.log" || echo "probe rc!=0 for $B"
  kill -- -"$BR" -"$BE" 2>/dev/null || true; sleep 2
done
date -u +%FT%TZ
echo AC_RUN_COMPLETE
