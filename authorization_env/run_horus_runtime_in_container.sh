#!/usr/bin/env bash
set -Eeuo pipefail

HORUS_BUILD_LOG=/tmp/horus_authorization_build.log
HORUS_BRIDGE_LOG=/tmp/horus_authorization_bridge.log
HORUS_BACKEND_LOG=/tmp/horus_authorization_backend.log
HORUS_BRIDGE_PID=""
HORUS_BACKEND_PID=""
HORUS_PROBE_PATH="${HORUS_PROBE_PATH:-/workspace/authorization_env/horus_runtime_probe.py}"
HORUS_PROBE_ARGS="${HORUS_PROBE_ARGS:-}"
HORUS_SOURCE_PATCH="${HORUS_SOURCE_PATCH:-}"

cleanup_horus_runtime() {
  if [[ -n "${HORUS_BRIDGE_PID}" ]]; then
    kill "${HORUS_BRIDGE_PID}" 2>/dev/null || true
  fi
  if [[ -n "${HORUS_BACKEND_PID}" ]]; then
    kill "${HORUS_BACKEND_PID}" 2>/dev/null || true
  fi
  wait "${HORUS_BRIDGE_PID}" 2>/dev/null || true
  wait "${HORUS_BACKEND_PID}" 2>/dev/null || true
}
trap cleanup_horus_runtime EXIT INT TERM

export ROS_LOCALHOST_ONLY=1
export ROS_DOMAIN_ID="${HORUS_ROS_DOMAIN_ID:-91}"

set +u
source /opt/ros/jazzy/setup.bash
set -u
mkdir -p /tmp/horus_authorization_ws/src
cp -a /workspace/frameworks/horus_ros2/. /tmp/horus_authorization_ws/src/
if [[ -n "${HORUS_SOURCE_PATCH}" ]]; then
  echo "[HORUS patch] test-only source patch: ${HORUS_SOURCE_PATCH}"
  patch -d /tmp/horus_authorization_ws/src -p1 <"${HORUS_SOURCE_PATCH}"
fi

echo "[HORUS 1/3] Fixed-source Jazzy build"
cd /tmp/horus_authorization_ws
if ! colcon build \
  --event-handlers console_direct+ \
  --cmake-args -DENABLE_WEBRTC=OFF -DBUILD_TESTING=OFF \
  >"${HORUS_BUILD_LOG}" 2>&1; then
  tail -80 "${HORUS_BUILD_LOG}"
  exit 1
fi
grep -E '^(Starting|Finished|Summary):|^Summary:' "${HORUS_BUILD_LOG}" || true
set +u
source /tmp/horus_authorization_ws/install/setup.bash
set -u

echo "[HORUS 2/3] Loopback-only bridge and backend"
ros2 run horus_unity_bridge horus_unity_bridge_node --ros-args \
  -p tcp_ip:=127.0.0.1 \
  -p tcp_port:=11000 \
  -p transport_protocol:=horuslink \
  -p horuslink_bulk_port:=11001 \
  -p horuslink_keepalive_ms:=0 \
  -p multi_operator.control_lease_ttl_ms:=1200 \
  -p log_protocol_messages:=false \
  -p log_connection_events:=true \
  -p webrtc.enabled:=false \
  >"${HORUS_BRIDGE_LOG}" 2>&1 &
HORUS_BRIDGE_PID=$!

ros2 run horus_backend horus_backend_node --ros-args \
  -p tcp_port:=18080 \
  -p unity_tcp_port:=11000 \
  -p log_tcp_messages:=false \
  >"${HORUS_BACKEND_LOG}" 2>&1 &
HORUS_BACKEND_PID=$!

for _ in $(seq 1 80); do
  if nc -z 127.0.0.1 11000 && nc -z 127.0.0.1 11001; then
    break
  fi
  sleep 0.1
done
if ! nc -z 127.0.0.1 11000 || ! nc -z 127.0.0.1 11001; then
  echo "Bridge did not open both HorusLink lanes"
  tail -60 "${HORUS_BRIDGE_LOG}"
  exit 1
fi

echo "[HORUS 3/3] Runtime probe: ${HORUS_PROBE_PATH##*/} ${HORUS_PROBE_ARGS}"
HORUS_PROBE_ARGV=()
if [[ -n "${HORUS_PROBE_ARGS}" ]]; then
  read -r -a HORUS_PROBE_ARGV <<<"${HORUS_PROBE_ARGS}"
fi
if ! python3 "${HORUS_PROBE_PATH}" "${HORUS_PROBE_ARGV[@]}"; then
  echo "--- bridge diagnostic tail ---"
  tail -100 "${HORUS_BRIDGE_LOG}"
  echo "--- backend diagnostic tail ---"
  tail -100 "${HORUS_BACKEND_LOG}"
  exit 1
fi

echo "HORUS_RUNTIME_PROBE_COMPLETE"
