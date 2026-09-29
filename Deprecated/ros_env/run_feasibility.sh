#!/usr/bin/env bash

set -Eeuo pipefail

HOST_TMP=""
TMP_ROOT=""
CURRENT_STEP="startup"
PIDS=()
BUILD_PID=""

wait_for_text() {
  local file=$1
  local text=$2
  local attempts=${3:-120}
  local attempt
  for ((attempt = 0; attempt < attempts; attempt++)); do
    if test -f "$file" && grep -Fq -- "$text" "$file"; then
      return 0
    fi
    sleep 0.1
  done
  return 1
}

wait_for_text_after() {
  local file=$1
  local text=$2
  local first_line=$3
  local attempts=${4:-120}
  local attempt
  for ((attempt = 0; attempt < attempts; attempt++)); do
    if test -f "$file" && awk -v first="$first_line" -v text="$text" \
        'NR >= first && index($0, text) { found = 1 } END { exit !found }' "$file"; then
      return 0
    fi
    sleep 0.1
  done
  return 1
}

latest_graph() {
  local result_file=$1
  grep '^GRAPH ' "$result_file" 2>/dev/null | tail -n 1 || true
}

wait_for_graph_count() {
  local result_file=$1
  local expected=$2
  local attempts=${3:-120}
  local attempt
  local graph
  for ((attempt = 0; attempt < attempts; attempt++)); do
    graph=$(latest_graph "$result_file")
    if [[ "$graph" == *"publisher_count=${expected} "* ]]; then
      return 0
    fi
    sleep 0.1
  done
  return 1
}

publisher_identity() {
  local graph=$1
  sed -E 's/^.* publishers=([^ ]+) nodes=.*$/\1/' <<<"$graph"
}

container_cleanup() {
  set +e
  local pid
  local attempt
  local running
  for pid in "${PIDS[@]}"; do
    kill -INT "$pid" 2>/dev/null || true
  done
  sleep 0.4
  for pid in "${PIDS[@]}"; do
    kill -TERM "$pid" 2>/dev/null || true
  done
  for ((attempt = 0; attempt < 20; attempt++)); do
    running=0
    for pid in "${PIDS[@]}"; do
      if kill -0 "$pid" 2>/dev/null; then
        running=1
      fi
    done
    ((running == 0)) && break
    sleep 0.1
  done
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill -KILL "$pid" 2>/dev/null || true
    fi
  done
  for pid in "${PIDS[@]}"; do
    wait "$pid" 2>/dev/null || true
  done

  if [[ "$TMP_ROOT" == /tmp/origin-feasibility.* ]]; then
    rm -rf -- "$TMP_ROOT"
  fi
  if test "${WS:-}" = /workspace/ros2_ws; then
    rm -rf -- "$WS/build" "$WS/install" "$WS/log"
  fi
}

container_exit() {
  local rc=$?
  trap - EXIT
  if ((rc != 0)); then
    printf '[FAIL] stage=%s rc=%s\n' "$CURRENT_STEP" "$rc"
    local log_file
    for log_file in "$TMP_ROOT"/*.log; do
      if test -f "$log_file"; then
        printf '%s\n' "--- $(basename "$log_file") 핵심 ---"
        tail -n 20 "$log_file"
      fi
    done
  fi
  container_cleanup
  exit "$rc"
}

container_main() {
  set +u
  source /opt/ros/humble/setup.bash
  set -u

  WS=/workspace/ros2_ws
  POLICY=/workspace/security/policy.xml
  test "$(readlink -f "$WS")" = /workspace/ros2_ws
  test -f "$POLICY"

  TMP_ROOT=$(mktemp -d /tmp/origin-feasibility.XXXXXX)
  trap container_exit EXIT INT TERM

  export ROS_DOMAIN_ID=0
  export ROS_LOCALHOST_ONLY=1
  export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
  export ROS_SECURITY_ENABLE=true
  export ROS_SECURITY_STRATEGY=Enforce
  export ROS_SECURITY_KEYSTORE="$TMP_ROOT/keystore"
  export ROS2CLI_DISABLE_DAEMON=1
  export RCUTILS_COLORIZED_OUTPUT=0
  export FASTDDS_LOG_VERBOSITY=Info
  export NO_PROXY=127.0.0.1,localhost
  export no_proxy=127.0.0.1,localhost
  unset ROS_SECURITY_ENCLAVE_OVERRIDE || true

  CURRENT_STEP="[2/6] SROS2 정책 및 테스트 Node 구성"
  printf '\n[2/6] SROS2 정책 및 테스트 Node 구성\n'
  rm -rf -- "$WS/build" "$WS/install" "$WS/log"

  if ! colcon --log-base "$TMP_ROOT/colcon-log" build \
      --base-paths "$WS/src" \
      --build-base "$TMP_ROOT/build" \
      --install-base "$TMP_ROOT/install" \
      --merge-install \
      --packages-select origin_test \
      >"$TMP_ROOT/colcon.log" 2>&1; then
    printf '[FAIL] origin_test build\n'
    return 21
  fi
  set +u
  source "$TMP_ROOT/install/setup.bash"
  set -u
  ORIGIN_EXEC="$TMP_ROOT/install/lib/origin_test/origin_test"
  ROSBRIDGE_EXEC="$(ros2 pkg prefix rosbridge_server)/lib/rosbridge_server/rosbridge_websocket"
  test -x "$ORIGIN_EXEC"
  test -x "$ROSBRIDGE_EXEC"
  python3 -c 'import websocket'
  ros2 pkg prefix rosbridge_server >/dev/null
  printf '[PASS] origin_test build, rosbridge_server, WebSocket client dependency\n'

  if ! ros2 security create_keystore "$ROS_SECURITY_KEYSTORE" \
      >"$TMP_ROOT/security.log" 2>&1; then
    printf '[FAIL] keystore 생성\n'
    return 22
  fi
  if ! ros2 security generate_artifacts \
      -k "$ROS_SECURITY_KEYSTORE" \
      -p "$POLICY" \
      >>"$TMP_ROOT/security.log" 2>&1; then
    printf '[FAIL] policy artifact 생성\n'
    return 23
  fi

  local enclave
  for enclave in robot authorized low trusted_bridge; do
    test -f "$ROS_SECURITY_KEYSTORE/enclaves/$enclave/cert.pem"
    test -f "$ROS_SECURITY_KEYSTORE/enclaves/$enclave/permissions.xml"
    test -f "$ROS_SECURITY_KEYSTORE/enclaves/$enclave/permissions.p7s"
  done
  awk '
    /<deny_rule>/ { in_deny = 1 }
    /<\/deny_rule>/ { in_deny = 0 }
    /<allow_rule>/ { in_allow = 1 }
    /<\/allow_rule>/ { in_allow = 0 }
    in_deny && /<topic>rt\/cmd_vel<\/topic>/ { denied = 1 }
    in_allow && /<topic>rt\/cmd_vel<\/topic>/ { allowed = 1 }
    END { exit !(denied && !allowed) }
  ' "$ROS_SECURITY_KEYSTORE/enclaves/low/permissions.xml"
  grep -Fq '<default>DENY</default>' \
    "$ROS_SECURITY_KEYSTORE/enclaves/low/permissions.xml"
  local low_subject
  local bridge_subject
  low_subject=$(openssl x509 \
    -in "$ROS_SECURITY_KEYSTORE/enclaves/low/cert.pem" -noout -subject)
  bridge_subject=$(openssl x509 \
    -in "$ROS_SECURITY_KEYSTORE/enclaves/trusted_bridge/cert.pem" -noout -subject)
  [[ "$low_subject" == *'/low'* ]]
  [[ "$bridge_subject" == *'/trusted_bridge'* ]]
  printf '[PASS] Enforce keystore와 4개 enclave signed artifact 생성\n'

  local result_file="$TMP_ROOT/robot.events"
  local robot_log="$TMP_ROOT/robot.log"
  "$ORIGIN_EXEC" robot --result-file "$result_file" \
    --ros-args --enclave /robot \
    >"$robot_log" 2>&1 &
  local robot_pid=$!
  PIDS+=("$robot_pid")
  if ! wait_for_text "$robot_log" 'ROBOT_READY' 150; then
    printf '[FAIL] Dummy Robot 시작\n'
    return 24
  fi
  kill -0 "$robot_pid"
  printf '[PASS] Dummy Robot node=/dummy_robot enclave=/robot\n'

  CURRENT_STEP="[3/6] SROS2 Allow/Block 기준 실험"
  printf '\n[3/6] SROS2 Allow/Block 기준 실험\n'
  local auth_log="$TMP_ROOT/authorized.log"
  if ! "$ORIGIN_EXEC" publish --linear-x 0.330 --count 4 \
      --ros-args --enclave /authorized \
      >"$auth_log" 2>&1; then
    printf '[FAIL] Authorized publisher 실행\n'
    return 31
  fi
  if ! wait_for_text "$result_file" 'RECEIVED linear_x=0.330' 100; then
    printf '[FAIL] Authorized command 미수신\n'
    return 32
  fi
  if ! wait_for_graph_count "$result_file" 0 100; then
    printf '[FAIL] Authorized publisher 종료 후 graph 정리\n'
    return 33
  fi
  printf '[PASS] Test A Authorized Direct Publish = ALLOW, Dummy Robot 수신\n'

  local low_gate="$TMP_ROOT/low.gate"
  local low_log="$TMP_ROOT/low.log"
  local low_graph_first_line
  low_graph_first_line=$(( $(wc -l <"$result_file") + 1 ))
  "$ORIGIN_EXEC" publish --linear-x 0.440 --count 4 --gate-file "$low_gate" \
    --ros-args --enclave /low \
    >"$low_log" 2>&1 &
  local low_pid=$!
  PIDS+=("$low_pid")
  if ! wait_for_text "$low_log" 'DIRECT_WAIT_GATE' 100; then
    printf '[FAIL] Low publisher가 gate 전 준비되지 않음\n'
    return 34
  fi
  if ! wait_for_text "$low_log" '/keystore/enclaves/low' 100 || \
      ! wait_for_text_after "$result_file" '/direct_publisher@/low' \
        "$low_graph_first_line" 100; then
    printf '[FAIL] Low publisher의 node 참여 또는 /low security identity 미확인\n'
    return 35
  fi
  touch "$low_gate"
  set +e
  wait "$low_pid"
  local low_rc=$?
  set -e
  sleep 0.8
  if grep -Fq 'RECEIVED linear_x=0.440' "$result_file"; then
    printf '[FAIL] Low-Privilege command가 Dummy Robot에 전달됨\n'
    return 36
  fi
  local denial_line
  denial_line=$(grep -E -m1 \
    'rt/cmd_vel.*(denied by deny rule|not found in allow rule)' \
    "$low_log" 2>/dev/null || true)
  if test -z "$denial_line" || \
      ! grep -Fq 'SECURITY' "$low_log" || \
      ! grep -Fq 'check_create_datawriter' "$low_log" || \
      ((low_rc == 0)); then
    printf '[FAIL] Low BLOCK의 SROS2 runtime denial 증거 부족 (rc=%s)\n' "$low_rc"
    return 37
  fi
  if ! wait_for_graph_count "$result_file" 0 100; then
    printf '[FAIL] Low publisher 종료 후 graph 정리\n'
    return 38
  fi
  printf '[PASS] Test B Low-Privilege Direct Publish = BLOCK, Dummy Robot 미수신\n'
  printf '  evidence: %s\n' "$denial_line"

  CURRENT_STEP="[4/6] ROS Bridge 및 External Client 구성"
  printf '\n[4/6] ROS Bridge 및 External Client 구성\n'
  local bridge_log="$TMP_ROOT/bridge.log"
  local bridge_graph_first_line
  bridge_graph_first_line=$(( $(wc -l <"$result_file") + 1 ))
  env -u ROS_SECURITY_ENCLAVE_OVERRIDE \
    "$ROSBRIDGE_EXEC" \
      --address 127.0.0.1 \
      --port 9090 \
      --topics_pub_glob "['/cmd_vel']" \
      --topics_sub_glob "[]" \
      --services_glob "[]" \
      --actions_glob "[]" \
      --unregister_timeout 1.0 \
      --ros-args --enclave /trusted_bridge \
      >"$bridge_log" 2>&1 &
  local bridge_pid=$!
  PIDS+=("$bridge_pid")

  local port_ready=0
  local attempt
  for ((attempt = 0; attempt < 150; attempt++)); do
    if ! kill -0 "$bridge_pid" 2>/dev/null; then
      break
    fi
    if (exec 9<>/dev/tcp/127.0.0.1/9090) 2>/dev/null; then
      exec 9>&- 2>/dev/null || true
      port_ready=1
      break
    fi
    sleep 0.1
  done
  if ((port_ready != 1)); then
    printf '[FAIL] rosbridge loopback port 시작 실패\n'
    return 41
  fi
  if ! wait_for_text "$bridge_log" '/keystore/enclaves/trusted_bridge' 100 || \
      ! wait_for_text_after "$result_file" '/rosbridge_websocket@/trusted_bridge' \
        "$bridge_graph_first_line" 100; then
    printf '[FAIL] rosbridge node 참여 또는 /trusted_bridge security identity 미확인\n'
    return 42
  fi
  printf '[PASS] rosbridge_websocket loopback-only, enclave=/trusted_bridge\n'

  CURRENT_STEP="[5/6] Principal Collapse / Privilege Laundering PoC"
  printf '\n[5/6] Principal Collapse / Privilege Laundering PoC\n'
  local client_a_log="$TMP_ROOT/client_a.log"
  local client_b_log="$TMP_ROOT/client_b.log"

  "$ORIGIN_EXEC" external-client \
    --client-id A --linear-x 0.440 --hold-seconds 8 \
    >"$client_a_log" 2>&1 &
  local client_a_pid=$!
  PIDS+=("$client_a_pid")
  if ! wait_for_text "$client_a_log" 'EXTERNAL_SENT client=A' 150; then
    printf '[FAIL] External Client A publish 실패\n'
    return 51
  fi
  if ! wait_for_text "$result_file" 'RECEIVED linear_x=0.440' 100; then
    printf '[FAIL] Bridge-mediated Client A command 미수신\n'
    return 52
  fi
  sleep 0.5
  local graph_a
  graph_a=$(latest_graph "$result_file")
  if [[ "$graph_a" != *'publisher_count=1 '* ]] || \
      [[ "$graph_a" != *'/rosbridge_websocket@/trusted_bridge#'* ]]; then
    printf '[FAIL] Client A bridge publisher identity 불일치: %s\n' "$graph_a"
    return 53
  fi
  local identity_a
  identity_a=$(publisher_identity "$graph_a")
  local bridge_gid
  bridge_gid=${identity_a##*#}
  printf '[PASS] Client A linear.x=0.440 전달, publisher=/rosbridge_websocket enclave=/trusted_bridge gid=%s\n' "$bridge_gid"

  "$ORIGIN_EXEC" external-client \
    --client-id B --linear-x 0.550 --hold-seconds 12 \
    >"$client_b_log" 2>&1 &
  local client_b_pid=$!
  PIDS+=("$client_b_pid")
  if ! wait_for_text "$client_b_log" 'EXTERNAL_SENT client=B' 150; then
    printf '[FAIL] External Client B publish 실패\n'
    return 54
  fi
  if ! wait_for_text "$result_file" 'RECEIVED linear_x=0.550' 100; then
    printf '[FAIL] Bridge-mediated Client B command 미수신\n'
    return 55
  fi
  sleep 0.5
  local graph_both
  graph_both=$(latest_graph "$result_file")
  local identity_both
  identity_both=$(publisher_identity "$graph_both")
  local nodes_both
  nodes_both=${graph_both##* nodes=}
  if [[ "$graph_both" != *'publisher_count=1 '* ]] || \
      [[ "$identity_both" != "$identity_a" ]] || \
      [[ "$nodes_both" != '/dummy_robot@/robot,/rosbridge_websocket@/trusted_bridge' ]]; then
    printf '[FAIL] Multi-client identity 축약 불일치: %s\n' "$graph_both"
    return 56
  fi
  printf '[PASS] Client A/B 동시 연결에도 ROS publisher 1개, 동일 GID\n'

  set +e
  wait "$client_a_pid"
  local client_a_rc=$?
  set -e
  if ((client_a_rc != 0)) || ! kill -0 "$client_b_pid" 2>/dev/null; then
    printf '[FAIL] Client A 종료/B 유지 상태 구성 실패\n'
    return 57
  fi
  sleep 1.5
  local graph_after_a
  graph_after_a=$(latest_graph "$result_file")
  local identity_after_a
  identity_after_a=$(publisher_identity "$graph_after_a")
  if [[ "$graph_after_a" != *'publisher_count=1 '* ]] || \
      [[ "$identity_after_a" != "$identity_a" ]]; then
    printf '[FAIL] Client A 종료 후 B publisher 유지 불일치: %s\n' "$graph_after_a"
    return 58
  fi
  printf '[PASS] Client A 종료 후 B 연결 동안 같은 bridge publisher 유지\n'

  set +e
  wait "$client_b_pid"
  local client_b_rc=$?
  set -e
  if ((client_b_rc != 0)); then
    printf '[FAIL] Client B 종료 코드=%s\n' "$client_b_rc"
    return 59
  fi
  if ! wait_for_graph_count "$result_file" 0 80; then
    printf '[FAIL] 모든 External Client 종료 후 bridge publisher 정리 안 됨\n'
    return 60
  fi
  kill -0 "$bridge_pid"
  printf '[PASS] 모든 Client 종료 후 /cmd_vel publisher=0, bridge node는 유지\n'

  CURRENT_STEP="[6/6] 결과 기록 및 정리"
  printf '\n[6/6] 결과 기록 및 정리\n'
  printf 'SUMMARY authorized_direct=ALLOW low_direct=BLOCK bridge=ALLOW\n'
  printf 'SUMMARY external_a=DELIVERED external_b=DELIVERED\n'
  printf 'SUMMARY publisher_identity=/rosbridge_websocket enclave=/trusted_bridge gid=%s external_ros_nodes=0\n' "$bridge_gid"
  printf 'SUMMARY identity_bound_by=ROS_graph_plus_security_log_plus_certificate_CN\n'
  printf 'SUMMARY direct_low_value=0.440 bridge_value=0.440 principal_collapse=CONFIRMED\n'

  container_cleanup
  trap - EXIT INT TERM
  test ! -e "$WS/build"
  test ! -e "$WS/install"
  test ! -e "$WS/log"
  printf '[PASS] background process와 임시 resource 정리 완료\n'
}

host_cleanup() {
  set +e
  if test -n "$BUILD_PID" && kill -0 "$BUILD_PID" 2>/dev/null; then
    kill -TERM "$BUILD_PID" 2>/dev/null || true
    local attempt
    for ((attempt = 0; attempt < 20; attempt++)); do
      kill -0 "$BUILD_PID" 2>/dev/null || break
      sleep 0.1
    done
    if kill -0 "$BUILD_PID" 2>/dev/null; then
      kill -KILL "$BUILD_PID" 2>/dev/null || true
    fi
    wait "$BUILD_PID" 2>/dev/null || true
  fi
  if test -n "${COMPOSE_FILE:-}"; then
    docker compose -p ros_xr_feasibility -f "$COMPOSE_FILE" \
      down --remove-orphans >/dev/null 2>&1 || true
  fi
  if [[ "$HOST_TMP" == /tmp/origin-feasibility-host.* ]]; then
    rm -rf -- "$HOST_TMP"
  fi
}

host_exit() {
  local rc=$?
  trap - EXIT INT TERM
  host_cleanup
  exit "$rc"
}

host_signal() {
  local signal=$1
  trap - EXIT INT TERM
  host_cleanup
  if test "$signal" = INT; then
    exit 130
  fi
  exit 143
}

host_main() {
  local script_dir
  script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
  COMPOSE_FILE="$script_dir/compose.yaml"

  if ! docker info >/dev/null 2>&1; then
    local docker_members
    docker_members=$(getent group docker | awk -F: '$1 == "docker" { print $4 }')
    if test "${FEASIBILITY_DOCKER_GROUP_ACTIVE:-0}" != 1 && \
        [[ ",$docker_members," == *",$(id -un),"* ]]; then
      exec sg docker -c \
        "FEASIBILITY_DOCKER_GROUP_ACTIVE=1 '$script_dir/run_feasibility.sh'"
    fi
    printf '[FAIL] Docker daemon 접근 권한 없음\n'
    return 10
  fi

  HOST_TMP=$(mktemp -d /tmp/origin-feasibility-host.XXXXXX)
  trap host_exit EXIT
  trap 'host_signal INT' INT
  trap 'host_signal TERM' TERM

  printf '[1/6] 현재 환경 확인\n'
  docker version --format '  Docker client={{.Client.Version}} server={{.Server.Version}}'
  printf '  Compose %s\n' "$(docker compose version --short)"
  docker compose -p ros_xr_feasibility -f "$COMPOSE_FILE" config --quiet
  if docker image inspect ros-xr-humble:local >/dev/null 2>&1; then
    printf '  기존 image 확인: ros-xr-humble:local (build cache 재사용)\n'
  else
    printf '  기존 image 없음: 새로 build\n'
  fi
  docker compose -p ros_xr_feasibility -f "$COMPOSE_FILE" \
    build >"$HOST_TMP/image-build.log" 2>&1 &
  BUILD_PID=$!
  while kill -0 "$BUILD_PID" 2>/dev/null; do
    sleep 5
    if kill -0 "$BUILD_PID" 2>/dev/null; then
      printf '  image build 진행 중...\n'
    fi
  done
  set +e
  wait "$BUILD_PID"
  local build_rc=$?
  BUILD_PID=""
  set -e
  if ((build_rc != 0)); then
    printf '[FAIL] Docker image build\n'
    tail -n 30 "$HOST_TMP/image-build.log"
    return 11
  fi
  printf '[PASS] Docker image 준비 완료\n'

  docker compose -p ros_xr_feasibility -f "$COMPOSE_FILE" \
    run --rm -T --no-deps \
    ros bash /workspace/run_feasibility.sh --container
  printf '[PASS] Feasibility 자동 실행 완료, image 보존\n'
}

if test "${1:-}" = "--container"; then
  container_main
else
  host_main
fi
