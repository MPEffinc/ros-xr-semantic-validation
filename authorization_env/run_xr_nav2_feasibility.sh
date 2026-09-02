#!/usr/bin/env bash
set -Eeuo pipefail

# Fixed framework snapshots used by the preceding authorization experiments.
readonly HORUS_ROS2_REVISION="eca75cbf559f09ff793d8993338b2f1ffed1adfd"
readonly HORUS_REVISION="819cdfdc74f1a0c2bd73946dc14897a533f68b61"
readonly HORUS_SDK_REVISION="f4f00dab41910676519d545515531ec243414044"
readonly COMPAS_XR_REVISION="b86e6fbbacdc8e84183fc08c846176a1c79304ca"
readonly COMPAS_UNITY_REVISION="f1516ca568b101447507aebc28a594bdc358df3e"

readonly XR_NAV2_IMAGE="ros-xr-horus-nav2-jazzy:local"
readonly XR_NAV2_CONTAINER="ros-xr-nav2-feasibility"

XR_NAV2_TRIALS_VALUE=5
XR_NAV2_CASES_VALUE="F0,F1,F2,F3,F4,F5,F6"
XR_NAV2_REVOCATION_DELAY_VALUE="2"
XR_NAV2_OBSERVATION_VALUE="5"
XR_NAV2_LEASE_TTL_VALUE=1200
XR_NAV2_RUNTIME_TIMEOUT_VALUE=3600
XR_NAV2_REBUILD=0

XR_NAV2_HOST_OWNS_CONTAINER=0
XR_NAV2_INSIDE_RUN_DIR=""
declare -a XR_NAV2_INSIDE_PROCESS_GROUPS=()

usage() {
  cat <<'EOF'
Usage: run_xr_nav2_feasibility.sh [options]

Options:
  --trials N                 Independent repetitions per case (default: 5)
  --cases LIST               Comma-separated F0..F6 list
  --revocation-delay-sec N   Delay before the XR authority event (default: 2)
  --observation-sec N        Post-event observation window (default: 5)
  --lease-ttl-ms N           HORUS control lease TTL (default: 1200)
  --timeout-sec N            Whole isolated runtime timeout (default: 3600)
  --skip-f6                  Run F0 through F5 only
  --rebuild                  Rebuild the Jazzy image even if it is usable
  --help                     Show this help

The --inside mode is reserved for the isolated Docker invocation.
EOF
}

fail() {
  printf '[FAIL] %s\n' "$*" >&2
  return 1
}

is_positive_integer() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]]
}

is_nonnegative_number() {
  [[ "$1" =~ ^([0-9]+([.][0-9]+)?|[.][0-9]+)$ ]]
}

parse_host_arguments() {
  while (($# > 0)); do
    case "$1" in
      --trials)
        is_positive_integer "${2:-}" || fail "--trials requires a positive integer" || return
        XR_NAV2_TRIALS_VALUE=$2
        shift 2
        ;;
      --cases)
        [[ "${2:-}" =~ ^F[0-6](,F[0-6])*$ ]] || \
          fail "--cases must be a comma-separated subset of F0..F6" || return
        XR_NAV2_CASES_VALUE=$2
        shift 2
        ;;
      --revocation-delay-sec)
        is_nonnegative_number "${2:-}" || \
          fail "--revocation-delay-sec requires a nonnegative number" || return
        XR_NAV2_REVOCATION_DELAY_VALUE=$2
        shift 2
        ;;
      --observation-sec)
        is_nonnegative_number "${2:-}" || \
          fail "--observation-sec requires a nonnegative number" || return
        XR_NAV2_OBSERVATION_VALUE=$2
        shift 2
        ;;
      --lease-ttl-ms)
        is_positive_integer "${2:-}" || fail "--lease-ttl-ms requires a positive integer" || return
        XR_NAV2_LEASE_TTL_VALUE=$2
        shift 2
        ;;
      --timeout-sec)
        is_positive_integer "${2:-}" || fail "--timeout-sec requires a positive integer" || return
        XR_NAV2_RUNTIME_TIMEOUT_VALUE=$2
        shift 2
        ;;
      --skip-f6)
        XR_NAV2_CASES_VALUE="F0,F1,F2,F3,F4,F5"
        shift
        ;;
      --rebuild)
        XR_NAV2_REBUILD=1
        shift
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      *)
        fail "unknown option: $1" || true
        usage >&2
        return 2
        ;;
    esac
  done
}

host_cleanup() {
  local cleanup_rc=$?
  set +e
  if ((XR_NAV2_HOST_OWNS_CONTAINER == 1)); then
    docker rm -f "${XR_NAV2_CONTAINER}" >/dev/null 2>&1 || true
  fi
  rm -f -- /tmp/xr_nav2_feasibility_image_build.log
  return "${cleanup_rc}"
}

host_exit() {
  local host_rc=$1
  trap - EXIT INT TERM
  host_cleanup || true
  exit "${host_rc}"
}

terminate_process_group() {
  local group_leader=$1
  local attempt

  if ! kill -0 -- "-${group_leader}" 2>/dev/null; then
    wait "${group_leader}" 2>/dev/null || true
    return
  fi

  kill -TERM -- "-${group_leader}" 2>/dev/null || true
  for attempt in $(seq 1 50); do
    if ! kill -0 -- "-${group_leader}" 2>/dev/null; then
      break
    fi
    sleep 0.1
  done
  if kill -0 -- "-${group_leader}" 2>/dev/null; then
    kill -KILL -- "-${group_leader}" 2>/dev/null || true
  fi
  wait "${group_leader}" 2>/dev/null || true
}

inside_cleanup() {
  local inside_rc=$1
  local evidence_name
  local index

  trap - EXIT INT TERM
  set +e
  for ((index=${#XR_NAV2_INSIDE_PROCESS_GROUPS[@]} - 1; index >= 0; --index)); do
    terminate_process_group "${XR_NAV2_INSIDE_PROCESS_GROUPS[index]}"
  done
  if [[ "$(id -u)" == 0 && "${XR_NAV2_EVIDENCE_UID:-}" =~ ^[0-9]+$ && \
        "${XR_NAV2_EVIDENCE_GID:-}" =~ ^[0-9]+$ ]]; then
    for evidence_name in \
      xr_mock_timeline.log \
      nav2_revocation_runtime.log \
      nav2_handoff_runtime.log \
      xr_nav2_feasibility_summary.md \
      horus_post_handoff.log; do
      if [[ -e "/workspace/evidence/${evidence_name}" ]]; then
        chown "${XR_NAV2_EVIDENCE_UID}:${XR_NAV2_EVIDENCE_GID}" \
          "/workspace/evidence/${evidence_name}" 2>/dev/null || true
      fi
    done
  fi
  if [[ -n "${XR_NAV2_INSIDE_RUN_DIR}" && \
        "${XR_NAV2_INSIDE_RUN_DIR}" == /tmp/xr_nav2_feasibility.* ]]; then
    rm -rf -- "${XR_NAV2_INSIDE_RUN_DIR}"
  fi
  exit "${inside_rc}"
}

start_process_group() {
  local result_variable=$1
  local log_path=$2
  local process_pid
  shift 2

  setsid -- "$@" >"${log_path}" 2>&1 &
  process_pid=$!
  XR_NAV2_INSIDE_PROCESS_GROUPS+=("${process_pid}")
  printf -v "${result_variable}" '%s' "${process_pid}"
}

source_ros_environment() {
  set +u
  # ROS setup scripts may inspect variables that are intentionally unset.
  source /opt/ros/jazzy/setup.bash
  set -u
}

source_horus_overlay() {
  local overlay_path=$1
  set +u
  source "${overlay_path}"
  set -u
}

nav2_is_ready() {
  local action_list
  local lifecycle_state
  local lifecycle_node

  action_list=$(timeout 5s ros2 action list 2>/dev/null) || return 1
  grep -qx '/navigate_to_pose' <<<"${action_list}" || return 1

  for lifecycle_node in /map_server /planner_server /controller_server /bt_navigator; do
    lifecycle_state=$(timeout 5s ros2 lifecycle get "${lifecycle_node}" 2>/dev/null) || return 1
    grep -Eq '^[[:space:]]*active \[3\][[:space:]]*$' <<<"${lifecycle_state}" || return 1
  done
}

loopback_initialpose_is_ready() {
  local topic_info

  topic_info=$(timeout 5s ros2 topic info /initialpose 2>/dev/null) || return 1
  grep -Eq 'Subscription count: [1-9][0-9]*' <<<"${topic_info}"
}

horus_is_ready() {
  local service_list

  nc -z 127.0.0.1 11000 || return 1
  nc -z 127.0.0.1 11001 || return 1
  service_list=$(timeout 5s ros2 service list 2>/dev/null) || return 1
  grep -qx '/horus/register_robot' <<<"${service_list}"
}

inside_main() {
  local horus_ws
  local build_log
  local nav2_log
  local pose_seed_log
  local bridge_log
  local backend_log
  local nav2_pid=""
  local pose_seed_pid=""
  local bridge_pid=""
  local backend_pid=""
  local readiness_attempt
  local probe_rc
  local probe_timeout
  local trials=${XR_NAV2_TRIALS:-5}
  local cases=${XR_NAV2_CASES:-F0,F1,F2,F3,F4,F5,F6}
  local revocation_delay=${XR_NAV2_REVOCATION_DELAY_SEC:-2}
  local observation_sec=${XR_NAV2_OBSERVATION_SEC:-5}
  local lease_ttl_ms=${XR_NAV2_LEASE_TTL_MS:-1200}
  local probe_mode=${XR_NAV2_PROBE_MODE:-feasibility}

  export ROS_LOCALHOST_ONLY=1
  export ROS_DOMAIN_ID="${XR_NAV2_ROS_DOMAIN_ID:-95}"
  export PYTHONUNBUFFERED=1

  test -d /workspace/frameworks/horus_ros2 || fail "read-only HORUS ROS 2 source mount missing"
  test -f /workspace/authorization_env/xr_mock_client.py || fail "xr_mock_client.py missing"
  if [[ "${probe_mode}" == post-handoff ]]; then
    test -f /workspace/authorization_env/xr2act_horus_probe.py || \
      fail "xr2act_horus_probe.py missing"
  fi
  test -d /workspace/evidence || fail "writable evidence mount missing"

  XR_NAV2_INSIDE_RUN_DIR=$(mktemp -d /tmp/xr_nav2_feasibility.XXXXXX)
  horus_ws="${XR_NAV2_INSIDE_RUN_DIR}/horus_ws"
  build_log="${XR_NAV2_INSIDE_RUN_DIR}/horus_build.log"
  nav2_log="${XR_NAV2_INSIDE_RUN_DIR}/nav2.log"
  pose_seed_log="${XR_NAV2_INSIDE_RUN_DIR}/pose_seed.log"
  bridge_log="${XR_NAV2_INSIDE_RUN_DIR}/bridge.log"
  backend_log="${XR_NAV2_INSIDE_RUN_DIR}/backend.log"
  mkdir -p "${horus_ws}/src"

  trap 'inside_cleanup $?' EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM

  echo "[inside 1/5] ROS 2 Jazzy and official Nav2 loopback verification"
  source_ros_environment
  dpkg-query -W \
    ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup \
    ros-jazzy-nav2-loopback-sim \
    ros-jazzy-nav2-msgs
  test -f /opt/ros/jazzy/share/nav2_bringup/launch/tb3_loopback_simulation.launch.py || \
    fail "official tb3_loopback_simulation.launch.py is not installed"

  echo "[inside 2/5] Fixed HORUS ROS 2 build in disposable /tmp workspace"
  cp -a /workspace/frameworks/horus_ros2/. "${horus_ws}/src/"
  if ! timeout --foreground --signal=TERM --kill-after=15s 900s \
    colcon --log-base "${horus_ws}/log" build \
      --base-paths "${horus_ws}/src" \
      --build-base "${horus_ws}/build" \
      --install-base "${horus_ws}/install" \
      --event-handlers console_direct+ \
      --cmake-args -DENABLE_WEBRTC=OFF -DBUILD_TESTING=OFF \
      >"${build_log}" 2>&1; then
    tail -120 "${build_log}"
    fail "HORUS ROS 2 build failed"
  fi
  grep -E '^(Starting|Finished|Summary):|^Summary:' "${build_log}" || true
  source_horus_overlay "${horus_ws}/install/setup.bash"

  echo "[inside 3/5] Official headless TB3 loopback plus actual Nav2 stack"
  # Keep publishing the deterministic reset pose while Nav2 starts.  The
  # lifecycle manager can otherwise attempt planner activation before the
  # loopback simulator has produced map->odom->base TF.
  start_process_group pose_seed_pid "${pose_seed_log}" \
    ros2 topic pub --rate 10 /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
      '{header: {frame_id: map}, pose: {pose: {position: {x: -2.0, y: -0.5, z: 0.0}, orientation: {w: 1.0}}}}'
  start_process_group nav2_pid "${nav2_log}" \
    ros2 launch nav2_bringup tb3_loopback_simulation.launch.py \
      use_rviz:=False \
      use_composition:=False \
      autostart:=True \
      use_robot_state_pub:=True

  # The Jazzy loopback ignores cmd_vel until it receives an initial pose.  On
  # the tested package build, planner/BT activation also waits on the resulting
  # map->odom->base TF chain, so seed it before waiting for full lifecycle state.
  for readiness_attempt in $(seq 1 90); do
    if ! kill -0 "${nav2_pid}" 2>/dev/null; then
      tail -160 "${nav2_log}"
      fail "Nav2 launch exited before its initialpose subscription appeared"
    fi
    if loopback_initialpose_is_ready; then
      break
    fi
    if ((readiness_attempt % 15 == 0)); then
      printf '  waiting for loopback /initialpose subscriber (%ss)\n' "${readiness_attempt}"
    fi
    sleep 1
  done
  if ! loopback_initialpose_is_ready; then
    tail -160 "${nav2_log}"
    fail "loopback /initialpose subscriber did not appear within 90 seconds"
  fi
  for readiness_attempt in $(seq 1 180); do
    if ! kill -0 "${nav2_pid}" 2>/dev/null; then
      tail -160 "${nav2_log}"
      fail "Nav2 launch exited before lifecycle/action readiness"
    fi
    if nav2_is_ready; then
      break
    fi
    if ((readiness_attempt % 15 == 0)); then
      printf '  waiting for Nav2 lifecycle/action readiness (%ss)\n' "${readiness_attempt}"
    fi
    sleep 1
  done
  if ! nav2_is_ready; then
    tail -160 "${nav2_log}"
    fail "Nav2 did not become active within 180 seconds"
  fi
  terminate_process_group "${pose_seed_pid}"
  echo "  Nav2 active: /navigate_to_pose, map_server, planner, controller, bt_navigator"
  echo "  pose reset: runner seeds TF once; xr_mock_client resets /initialpose and odom baselines per trial"

  echo "[inside 4/5] Actual HorusLink bridge and HORUS backend/Nav2 adapter"
  start_process_group bridge_pid "${bridge_log}" \
    ros2 run horus_unity_bridge horus_unity_bridge_node --ros-args \
      -p tcp_ip:=127.0.0.1 \
      -p tcp_port:=11000 \
      -p transport_protocol:=horuslink \
      -p horuslink_bulk_port:=11001 \
      -p horuslink_keepalive_ms:=0 \
      -p "multi_operator.control_lease_ttl_ms:=${lease_ttl_ms}" \
      -p log_protocol_messages:=false \
      -p log_connection_events:=true \
      -p webrtc.enabled:=false

  start_process_group backend_pid "${backend_log}" \
    ros2 run horus_backend horus_backend_node --ros-args \
      -p tcp_port:=18080 \
      -p unity_tcp_port:=11000 \
      -p log_tcp_messages:=false

  for readiness_attempt in $(seq 1 90); do
    if ! kill -0 "${bridge_pid}" 2>/dev/null; then
      tail -120 "${bridge_log}"
      fail "HORUS bridge exited before readiness"
    fi
    if ! kill -0 "${backend_pid}" 2>/dev/null; then
      tail -120 "${backend_log}"
      fail "HORUS backend exited before readiness"
    fi
    if horus_is_ready; then
      break
    fi
    if ((readiness_attempt % 15 == 0)); then
      printf '  waiting for HorusLink lanes and backend service (%ss)\n' "${readiness_attempt}"
    fi
    sleep 1
  done
  if ! horus_is_ready; then
    echo "--- HORUS bridge diagnostic tail ---"
    tail -120 "${bridge_log}"
    echo "--- HORUS backend diagnostic tail ---"
    tail -120 "${backend_log}"
    fail "HORUS bridge/backend did not become ready"
  fi

  echo "[inside 5/5] Probe mode=${probe_mode} through actual HORUS and Nav2"
  printf '  trials=%s cases=%s revocation_delay=%ss observation=%ss lease_ttl=%sms\n' \
    "${trials}" "${cases}" "${revocation_delay}" "${observation_sec}" "${lease_ttl_ms}"
  probe_timeout=$(( ${XR_NAV2_RUNTIME_TIMEOUT_SEC:-3600} - 30 ))
  if ((probe_timeout < 60)); then
    probe_timeout=60
  fi

  set +e
  if [[ "${probe_mode}" == post-handoff ]]; then
    timeout --foreground --signal=TERM --kill-after=15s "${probe_timeout}s" \
      python3 /workspace/authorization_env/xr2act_horus_probe.py \
        --trials "${trials}" \
        --revocation-delay-sec "${revocation_delay}" \
        --lease-ttl-ms "${lease_ttl_ms}" \
        --timeline-log /tmp/xr2act_horus_timeline.log \
        --output-log /workspace/evidence/horus_post_handoff.log
    probe_rc=$?
  else
    timeout --foreground --signal=TERM --kill-after=15s "${probe_timeout}s" \
      python3 /workspace/authorization_env/xr_mock_client.py \
        --trials "${trials}" \
        --cases "${cases}" \
        --revocation-delay-sec "${revocation_delay}" \
        --observation-sec "${observation_sec}" \
        --lease-ttl-ms "${lease_ttl_ms}" \
        --timeline-log /workspace/evidence/xr_mock_timeline.log \
        --revocation-log /workspace/evidence/nav2_revocation_runtime.log \
        --handoff-log /workspace/evidence/nav2_handoff_runtime.log \
        --summary-md /workspace/evidence/xr_nav2_feasibility_summary.md \
        --start-x -2.0 \
        --start-y -0.5 \
        --goal-a-x 1.5 \
        --goal-a-y -0.5 \
        --goal-b-x -1.5 \
        --goal-b-y 1.0
    probe_rc=$?
  fi
  set -e

  if ((probe_rc != 0)); then
    printf '[FAIL] xr_mock_client exited rc=%s\n' "${probe_rc}"
    echo "--- Nav2 diagnostic tail ---"
    tail -100 "${nav2_log}"
    echo "--- HORUS backend diagnostic tail ---"
    tail -100 "${backend_log}"
    return "${probe_rc}"
  fi

  echo "XR_NAV2_FEASIBILITY_RUNTIME_COMPLETE"
}

verify_revision() {
  local repository_path=$1
  local expected_revision=$2
  local observed_revision
  local repository_changes

  test -d "${repository_path}/.git" || fail "framework checkout missing: ${repository_path}"
  observed_revision=$(git -C "${repository_path}" rev-parse HEAD)
  if [[ "${observed_revision}" != "${expected_revision}" ]]; then
    fail "revision mismatch: ${repository_path} expected=${expected_revision} observed=${observed_revision}"
    return
  fi
  repository_changes=$(git -C "${repository_path}" status --porcelain)
  if [[ -n "${repository_changes}" ]]; then
    printf '[FAIL] fixed framework checkout is dirty: %s\n%s\n' \
      "${repository_path}" "${repository_changes}" >&2
    return 1
  fi
  printf '  %s @ %s (clean)\n' "${repository_path##*/}" "${observed_revision}"
}

image_has_required_nav2() {
  docker image inspect "${XR_NAV2_IMAGE}" >/dev/null 2>&1 || return 1
  docker run --rm --network none "${XR_NAV2_IMAGE}" bash -lc '
    set -e
    dpkg-query -W ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-nav2-loopback-sim >/dev/null
    test -f /opt/ros/jazzy/share/nav2_bringup/launch/tb3_loopback_simulation.launch.py
  ' >/dev/null 2>&1
}

docker_group_reexec() {
  local script_path=$1
  local docker_members
  local rebuild_argument=()
  local -a rerun_command
  local quoted_command=""
  local command_word

  docker_members=$(getent group docker | awk -F: '$1 == "docker" { print $4 }')
  if [[ "${XR_NAV2_DOCKER_GROUP_ACTIVE:-0}" == 1 || \
        ",${docker_members}," != *",$(id -un),"* ]]; then
    return 1
  fi

  if ((XR_NAV2_REBUILD == 1)); then
    rebuild_argument=(--rebuild)
  fi
  rerun_command=(
    env XR_NAV2_DOCKER_GROUP_ACTIVE=1
    "${script_path}"
    --trials "${XR_NAV2_TRIALS_VALUE}"
    --cases "${XR_NAV2_CASES_VALUE}"
    --revocation-delay-sec "${XR_NAV2_REVOCATION_DELAY_VALUE}"
    --observation-sec "${XR_NAV2_OBSERVATION_VALUE}"
    --lease-ttl-ms "${XR_NAV2_LEASE_TTL_VALUE}"
    --timeout-sec "${XR_NAV2_RUNTIME_TIMEOUT_VALUE}"
    "${rebuild_argument[@]}"
  )
  for command_word in "${rerun_command[@]}"; do
    printf -v quoted_command '%s%q ' "${quoted_command}" "${command_word}"
  done
  exec sg docker -c "${quoted_command% }"
}

host_main() {
  local script_dir
  local workspace_root
  local evidence_dir
  local build_log=/tmp/xr_nav2_feasibility_image_build.log
  local runtime_rc
  local stale_container_running
  local evidence_file

  parse_host_arguments "$@"
  script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
  workspace_root=$(cd -- "${script_dir}/.." && pwd)
  evidence_dir="${workspace_root}/evidence"

  if ! docker info >/dev/null 2>&1; then
    docker_group_reexec "${script_dir}/run_xr_nav2_feasibility.sh" || {
      fail "Docker daemon access unavailable; Docker group re-entry was not possible"
      return 10
    }
  fi

  trap 'host_exit $?' EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM

  echo "[1/6] Context and fixed framework revisions"
  verify_revision "${workspace_root}/frameworks/horus_ros2" "${HORUS_ROS2_REVISION}"
  verify_revision "${workspace_root}/frameworks/horus" "${HORUS_REVISION}"
  verify_revision "${workspace_root}/frameworks/horus_sdk" "${HORUS_SDK_REVISION}"
  verify_revision "${workspace_root}/frameworks/compas_xr" "${COMPAS_XR_REVISION}"
  verify_revision "${workspace_root}/frameworks/compas_xr_unity_assembly" "${COMPAS_UNITY_REVISION}"
  test -f "${script_dir}/xr_mock_client.py" || fail "missing ${script_dir}/xr_mock_client.py"

  echo "[2/6] Jazzy image and official Nav2 loopback packages"
  if ((XR_NAV2_REBUILD == 1)) || ! image_has_required_nav2; then
    if ! timeout --foreground --signal=TERM --kill-after=20s 1800s \
      docker build -t "${XR_NAV2_IMAGE}" "${script_dir}" >"${build_log}" 2>&1; then
      tail -120 "${build_log}"
      fail "Docker image build failed"
      return 11
    fi
    echo "  image built: ${XR_NAV2_IMAGE}"
  else
    echo "  verified image reused: ${XR_NAV2_IMAGE}"
  fi
  if ! image_has_required_nav2; then
    fail "image does not contain the official Jazzy Nav2 loopback launch"
    return 12
  fi

  echo "[3/6] Isolated runtime (--network none, read-only framework sources)"
  mkdir -p "${evidence_dir}"
  if docker container inspect "${XR_NAV2_CONTAINER}" >/dev/null 2>&1; then
    stale_container_running=$(docker container inspect \
      --format '{{.State.Running}}' "${XR_NAV2_CONTAINER}")
    if [[ "${stale_container_running}" == true ]]; then
      fail "a feasibility container is already running: ${XR_NAV2_CONTAINER}"
      return 13
    fi
    echo "  removing stopped stale container: ${XR_NAV2_CONTAINER}"
    docker rm "${XR_NAV2_CONTAINER}" >/dev/null
  fi

  XR_NAV2_HOST_OWNS_CONTAINER=1
  set +e
  timeout --foreground --signal=TERM --kill-after=20s "${XR_NAV2_RUNTIME_TIMEOUT_VALUE}s" \
    docker run --rm --network none \
      --name "${XR_NAV2_CONTAINER}" \
      -v "${workspace_root}:/workspace:ro" \
      -v "${evidence_dir}:/workspace/evidence:rw" \
      -e "XR_NAV2_TRIALS=${XR_NAV2_TRIALS_VALUE}" \
      -e "XR_NAV2_CASES=${XR_NAV2_CASES_VALUE}" \
      -e "XR_NAV2_REVOCATION_DELAY_SEC=${XR_NAV2_REVOCATION_DELAY_VALUE}" \
      -e "XR_NAV2_OBSERVATION_SEC=${XR_NAV2_OBSERVATION_VALUE}" \
      -e "XR_NAV2_LEASE_TTL_MS=${XR_NAV2_LEASE_TTL_VALUE}" \
      -e "XR_NAV2_RUNTIME_TIMEOUT_SEC=${XR_NAV2_RUNTIME_TIMEOUT_VALUE}" \
      -e "XR_NAV2_PROBE_MODE=${XR_NAV2_PROBE_MODE:-feasibility}" \
      -e "XR_NAV2_EVIDENCE_UID=$(id -u)" \
      -e "XR_NAV2_EVIDENCE_GID=$(id -g)" \
      -e XR_NAV2_ROS_DOMAIN_ID=95 \
      "${XR_NAV2_IMAGE}" \
      bash /workspace/authorization_env/run_xr_nav2_feasibility.sh --inside
  runtime_rc=$?
  set -e

  docker rm -f "${XR_NAV2_CONTAINER}" >/dev/null 2>&1 || true
  XR_NAV2_HOST_OWNS_CONTAINER=0

  echo "[4/6] Runtime result"
  if ((runtime_rc == 124)); then
    echo "  result=TIMEOUT timeout_sec=${XR_NAV2_RUNTIME_TIMEOUT_VALUE}"
  elif ((runtime_rc != 0)); then
    echo "  result=FAIL rc=${runtime_rc}"
  else
    echo "  result=PASS"
  fi

  echo "[5/6] Evidence inventory"
  for evidence_file in \
    xr_mock_timeline.log \
    nav2_revocation_runtime.log \
    nav2_handoff_runtime.log \
    xr_nav2_feasibility_summary.md; do
    if [[ -s "${evidence_dir}/${evidence_file}" ]]; then
      printf '  %s (%s bytes)\n' "${evidence_dir}/${evidence_file}" \
        "$(stat -c '%s' "${evidence_dir}/${evidence_file}")"
    else
      printf '  missing-or-empty: %s\n' "${evidence_dir}/${evidence_file}"
    fi
  done

  echo "[6/6] Cleanup"
  if docker container inspect "${XR_NAV2_CONTAINER}" >/dev/null 2>&1; then
    fail "disposable runtime container remained"
    return 14
  fi
  echo "  no runtime container or process group remains"

  if ((runtime_rc != 0)); then
    return "${runtime_rc}"
  fi
  echo "XR_NAV2_FEASIBILITY_COMPLETE"
}

if [[ "${1:-}" == "--inside" ]]; then
  shift
  inside_main "$@"
else
  host_main "$@"
fi
