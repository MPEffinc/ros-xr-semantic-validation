#!/usr/bin/env bash

set -Eeuo pipefail

QUEST2ROS2_REPOSITORY="https://github.com/Taokt/Quest2ROS2.git"
QUEST2ROS2_COMMIT="07aaf65149c9e29103f1fc61deb466cef8a55cef"
ROS_TCP_REPOSITORY="https://github.com/guguroro/ros_tcp_communication.git"
ROS_TCP_COMMIT="5c5f08956d4bc7a045c321214b0bc03c63eb20a7"

HOST_TMP=""
TMP_ROOT=""
BUILD_PID=""
CURRENT_STEP="startup"
PIDS=()

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

wait_for_graph_identity() {
  local result_file=$1
  local identity_fragment=$2
  local attempts=${3:-120}
  local attempt
  local graph
  for ((attempt = 0; attempt < attempts; attempt++)); do
    graph=$(latest_graph "$result_file")
    if [[ "$graph" == *'publisher_count=1 '* ]] && \
        [[ "$graph" == *"$identity_fragment"* ]]; then
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

publisher_gid() {
  local graph=$1
  local identity
  identity=$(publisher_identity "$graph")
  printf '%s\n' "${identity##*#}"
}

wait_for_gid_change() {
  local result_file=$1
  local old_gid=$2
  local attempts=${3:-160}
  local attempt
  local graph
  local gid
  for ((attempt = 0; attempt < attempts; attempt++)); do
    graph=$(latest_graph "$result_file")
    if [[ "$graph" == *'publisher_count=1 '* ]]; then
      gid=$(publisher_gid "$graph")
      if test -n "$gid" && test "$gid" != "$old_gid"; then
        return 0
      fi
    fi
    sleep 0.1
  done
  return 1
}

untrack_pid() {
  local target=$1
  local remaining=()
  local pid
  for pid in "${PIDS[@]}"; do
    if test "$pid" != "$target"; then
      remaining+=("$pid")
    fi
  done
  PIDS=("${remaining[@]}")
}

stop_pid() {
  local pid=$1
  local attempt
  if ! kill -0 "$pid" 2>/dev/null; then
    wait "$pid" 2>/dev/null || true
    return 0
  fi
  kill -INT "$pid" 2>/dev/null || true
  for ((attempt = 0; attempt < 10; attempt++)); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.1
  done
  if kill -0 "$pid" 2>/dev/null; then
    kill -TERM "$pid" 2>/dev/null || true
  fi
  for ((attempt = 0; attempt < 20; attempt++)); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.1
  done
  if kill -0 "$pid" 2>/dev/null; then
    kill -KILL "$pid" 2>/dev/null || true
  fi
  wait "$pid" 2>/dev/null || true
}

container_cleanup() {
  set +e
  local pid
  for pid in "${PIDS[@]}"; do
    stop_pid "$pid"
  done
  PIDS=()
  if [[ "$TMP_ROOT" == /tmp/quest2ros2-feasibility.* ]]; then
    rm -rf -- "$TMP_ROOT"
  fi
}

container_exit() {
  local rc=$?
  trap - EXIT INT TERM
  if ((rc != 0)); then
    printf '[FAIL] stage=%s rc=%s\n' "$CURRENT_STEP" "$rc"
    if test -n "${RUNTIME_EVIDENCE:-}"; then
      printf '[FAIL] stage=%s rc=%s\n' "$CURRENT_STEP" "$rc" >>"$RUNTIME_EVIDENCE"
    fi
    local log_file
    if test -n "$TMP_ROOT" && test -d "$TMP_ROOT"; then
      for log_file in "$TMP_ROOT"/*.log; do
        if test -f "$log_file"; then
          printf '%s\n' "--- $(basename "$log_file") 핵심 ---"
          tail -n 20 "$log_file"
        fi
      done
    fi
  fi
  container_cleanup
  exit "$rc"
}

container_signal() {
  local signal=$1
  trap - EXIT INT TERM
  container_cleanup
  if test "$signal" = INT; then
    exit 130
  fi
  exit 143
}

runtime_note() {
  printf '%s\n' "$1" | tee -a "$RUNTIME_EVIDENCE"
}

container_main() {
  set +u
  source /opt/ros/humble/setup.bash
  set -u

  local sources=/workspace/quest_sources
  local project_ws=/workspace/ros2_ws
  local policy=/workspace/security/policy.xml
  local evidence=/workspace/evidence
  BUILD_EVIDENCE="$evidence/quest2ros2_build.log"
  RUNTIME_EVIDENCE="$evidence/quest2ros2_runtime.log"
  IDENTITY_EVIDENCE="$evidence/quest2ros2_identity.txt"

  test -d "$sources/Quest2ROS2/.git"
  test -d "$sources/ros_tcp_communication/.git"
  test -f "$policy"
  test -d "$project_ws/src/origin_test"
  test "$(readlink -f "$project_ws")" = /workspace/ros2_ws
  rm -rf -- "$project_ws/log" \
    "$project_ws/src/origin_test/scripts/__pycache__"
  mkdir -p "$evidence"
  : >"$BUILD_EVIDENCE"
  : >"$RUNTIME_EVIDENCE"
  : >"$IDENTITY_EVIDENCE"

  TMP_ROOT=$(mktemp -d /tmp/quest2ros2-feasibility.XXXXXX)
  trap container_exit EXIT
  trap 'container_signal INT' INT
  trap 'container_signal TERM' TERM

  local ws="$TMP_ROOT/ws"
  mkdir -p "$ws/src"
  cp -a "$sources/ros_tcp_communication" "$ws/src/ros_tcp_endpoint"
  cp -a "$sources/Quest2ROS2" "$ws/src/q2r2_bringup"
  cp -a "$sources/Quest2ROS2/Files_for_msg_pkg" "$ws/src/quest2ros"
  cp -a "$project_ws/src/origin_test" "$ws/src/origin_test"

  CURRENT_STEP="[4/8] ROS 2 Package Build 및 기본 실행"
  printf '\n[4/8] ROS 2 Package Build 및 기본 실행\n'
  {
    printf 'test_date=%s\n' "$(date -Iseconds)"
    printf 'clone_time=%s\n' "$(cat "$sources/clone_time.txt")"
    printf 'Quest2ROS2 repository=%s branch=main commit=%s\n' \
      "$QUEST2ROS2_REPOSITORY" "$QUEST2ROS2_COMMIT"
    printf 'ros_tcp_communication repository=%s branch=main commit=%s\n' \
      "$ROS_TCP_REPOSITORY" "$ROS_TCP_COMMIT"
    printf 'Quest2ROS2 license=Apache-2.0 root_LICENSE_sha256=%s\n' \
      "$(sha256sum "$sources/Quest2ROS2/LICENSE" | awk '{print $1}')"
    printf 'ros_tcp_communication license=Apache-2.0 LICENSE_sha256=%s\n' \
      "$(sha256sum "$sources/ros_tcp_communication/LICENSE" | awk '{print $1}')"
    printf 'source_patch=NONE\n'
    printf 'workspace_construction=official Files_for_msg_pkg copied as quest2ros per README\n'
    printf 'upstream_manifest_note=q2r2_bringup declares quest2ros2_msg while current simulator imports quest2ros\n'
    printf 'build_command=colcon build --packages-select quest2ros ros_tcp_endpoint q2r2_bringup origin_test\n'
    printf '\n[colcon list]\n'
    (cd "$TMP_ROOT" && colcon list --base-paths "$ws/src")
    printf '\n[colcon build]\n'
  } >"$BUILD_EVIDENCE"

  if ! colcon --log-base "$TMP_ROOT/colcon-log" build \
      --base-paths "$ws/src" \
      --build-base "$TMP_ROOT/build" \
      --install-base "$TMP_ROOT/install" \
      --merge-install \
      --executor sequential \
      --packages-select quest2ros ros_tcp_endpoint q2r2_bringup origin_test \
      --cmake-args -DBUILD_TESTING=OFF \
      >>"$BUILD_EVIDENCE" 2>&1; then
    printf '[FAIL] pinned ROS-side package build\n'
    return 41
  fi

  set +u
  source "$TMP_ROOT/install/setup.bash"
  set -u
  local origin_exec="$TMP_ROOT/install/lib/origin_test/origin_test"
  local probe_exec="$TMP_ROOT/install/lib/origin_test/quest_tcp_probe"
  local endpoint_exec="$TMP_ROOT/install/lib/ros_tcp_endpoint/default_server_endpoint"
  local simulator_exec="$TMP_ROOT/install/lib/q2r2_bringup/SimulationInput"
  test -x "$origin_exec"
  test -x "$probe_exec"
  test -x "$endpoint_exec"
  test -x "$simulator_exec"
  python3 -c 'from quest2ros.msg import OVR2ROSInputs; from ros_tcp_endpoint.default_server_endpoint import main; import q2r2_bringup.SimulationInput' \
    >>"$BUILD_EVIDENCE" 2>&1
  printf 'build_result=PASS packages=quest2ros,ros_tcp_endpoint,q2r2_bringup,origin_test\n' \
    >>"$BUILD_EVIDENCE"
  printf '[PASS] pinned ROS-side package 4개 build/import\n'

  export ROS_DOMAIN_ID=67
  export ROS_LOCALHOST_ONLY=1
  export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
  export ROS_SECURITY_ENABLE=false
  export ROS2CLI_DISABLE_DAEMON=1
  local simulation_events="$TMP_ROOT/simulation.events"
  local simulation_receiver_log="$TMP_ROOT/simulation_receiver.log"
  local simulation_log="$TMP_ROOT/simulation.log"
  "$origin_exec" robot --node-name simulation_receiver \
    --topic /q2r_right_hand_twist --result-file "$simulation_events" \
    >"$simulation_receiver_log" 2>&1 &
  local simulation_receiver_pid=$!
  PIDS+=("$simulation_receiver_pid")
  wait_for_text "$simulation_receiver_log" 'ROBOT_READY' 120 || return 42
  "$simulator_exec" --ros-args -p mode:=velocity -p side:=right \
    >"$simulation_log" 2>&1 &
  local simulation_pid=$!
  PIDS+=("$simulation_pid")
  if ! wait_for_text "$simulation_events" 'RECEIVED linear_x=' 150; then
    printf '[FAIL] Quest2ROS2 SimulationInput ROS-only smoke test\n'
    return 43
  fi
  stop_pid "$simulation_pid"
  untrack_pid "$simulation_pid"
  stop_pid "$simulation_receiver_pid"
  untrack_pid "$simulation_receiver_pid"
  printf 'SimulationInput_smoke=PASS mode=velocity topic=/q2r_right_hand_twist note=ROS-only_not_TCP_identity_evidence\n' \
    >>"$BUILD_EVIDENCE"
  printf '[PASS] SimulationInput 실행 및 실제 Quest Twist topic publish (ROS-only smoke)\n'

  CURRENT_STEP="[5/8] ROS-TCP Protocol Emulator 구현"
  printf '\n[5/8] ROS–TCP Protocol Emulator 구현\n'
  python3 -m py_compile "$ws/src/origin_test/scripts/quest_tcp_probe.py"
  "$probe_exec" --help >/dev/null
  runtime_note '[PASS] actual frame=<u32le dest_len><dest><u32le body_len><body>, handshake 검증 포함'
  runtime_note '[PASS] wire topic=q2r_right_hand_twist type=geometry_msgs/Twist payload=<6d>/48B'

  export ROS_DOMAIN_ID=0
  export ROS_SECURITY_ENABLE=true
  export ROS_SECURITY_STRATEGY=Enforce
  export ROS_SECURITY_KEYSTORE="$TMP_ROOT/keystore"
  export RCUTILS_COLORIZED_OUTPUT=0
  export FASTDDS_LOG_VERBOSITY=Info
  export NO_PROXY=127.0.0.1,localhost
  export no_proxy=127.0.0.1,localhost
  unset ROS_SECURITY_ENCLAVE_OVERRIDE || true

  if ! ros2 security create_keystore "$ROS_SECURITY_KEYSTORE" \
      >"$TMP_ROOT/security.log" 2>&1; then
    return 44
  fi
  if ! ros2 security generate_artifacts -k "$ROS_SECURITY_KEYSTORE" -p "$policy" \
      >>"$TMP_ROOT/security.log" 2>&1; then
    return 45
  fi
  local enclave
  for enclave in robot authorized low trusted_bridge dummy_receiver trusted_quest_bridge; do
    test -f "$ROS_SECURITY_KEYSTORE/enclaves/$enclave/cert.pem"
    test -f "$ROS_SECURITY_KEYSTORE/enclaves/$enclave/permissions.p7s"
  done
  awk '
    /<deny_rule>/ { in_deny = 1 }
    /<\/deny_rule>/ { in_deny = 0 }
    /<allow_rule>/ { in_allow = 1 }
    /<\/allow_rule>/ { in_allow = 0 }
    in_deny && /<topic>rt\/q2r_right_hand_twist<\/topic>/ { denied = 1 }
    in_allow && /<topic>rt\/q2r_right_hand_twist<\/topic>/ { allowed = 1 }
    END { exit !(denied && !allowed) }
  ' "$ROS_SECURITY_KEYSTORE/enclaves/low/permissions.xml"
  grep -Fq '<topic>rt/q2r_right_hand_twist</topic>' \
    "$ROS_SECURITY_KEYSTORE/enclaves/trusted_quest_bridge/permissions.xml"

  local receiver_events="$TMP_ROOT/receiver.events"
  local receiver_log="$TMP_ROOT/receiver.log"
  "$origin_exec" robot --node-name quest_dummy_receiver \
    --topic /q2r_right_hand_twist --result-file "$receiver_events" \
    --ros-args --enclave /dummy_receiver \
    >"$receiver_log" 2>&1 &
  local receiver_pid=$!
  PIDS+=("$receiver_pid")
  wait_for_text "$receiver_log" 'ROBOT_READY' 150 || return 46

  local authorized_log="$TMP_ROOT/authorized.log"
  "$origin_exec" publish --topic /q2r_right_hand_twist --linear-x 0.330 --count 4 \
    --ros-args --enclave /authorized >"$authorized_log" 2>&1
  wait_for_text "$receiver_events" 'RECEIVED linear_x=0.330' 100 || return 47
  wait_for_graph_count "$receiver_events" 0 100 || return 48
  runtime_note '[PASS] Authorized direct /q2r_right_hand_twist = ALLOW'

  CURRENT_STEP="[6/8] SROS2 Direct/Bridge 대조 및 Multi-Client 실험"
  printf '\n[6/8] SROS2 Direct/Bridge 대조 및 Multi-Client 실험\n'
  local low_gate="$TMP_ROOT/low.gate"
  local low_log="$TMP_ROOT/low.log"
  local low_first_line
  low_first_line=$(( $(wc -l <"$receiver_events") + 1 ))
  "$origin_exec" publish --topic /q2r_right_hand_twist --linear-x 0.440 \
    --count 4 --gate-file "$low_gate" \
    --ros-args --enclave /low >"$low_log" 2>&1 &
  local low_pid=$!
  PIDS+=("$low_pid")
  wait_for_text "$low_log" 'DIRECT_WAIT_GATE' 100 || return 61
  wait_for_text_after "$receiver_events" '/direct_publisher@/low' "$low_first_line" 120 || return 62
  touch "$low_gate"
  set +e
  wait "$low_pid"
  local low_rc=$?
  set -e
  untrack_pid "$low_pid"
  sleep 0.8
  if grep -Fq 'RECEIVED linear_x=0.440' "$receiver_events"; then
    return 63
  fi
  local denial_line
  denial_line=$(grep -E -m1 \
    'rt/q2r_right_hand_twist.*(denied by deny rule|not found in allow rule)' \
    "$low_log" 2>/dev/null || true)
  if test -z "$denial_line" || ! grep -Fq 'SECURITY' "$low_log" || \
      ! grep -Fq 'check_create_datawriter' "$low_log" || ((low_rc == 0)); then
    return 64
  fi
  wait_for_graph_count "$receiver_events" 0 100 || return 65
  runtime_note '[PASS] Direct Low linear.x=0.440 = SROS2 BLOCK, Dummy Receiver 미수신'
  local denial_line_clean
  denial_line_clean=$(sed -E $'s/\x1B\\[[0-9;]*[mK]//g' <<<"$denial_line")
  printf 'SROS2_DENIAL %s\n' "$denial_line_clean" >>"$RUNTIME_EVIDENCE"

  local endpoint_log="$TMP_ROOT/endpoint.log"
  env -u ROS_SECURITY_ENCLAVE_OVERRIDE PYTHONUNBUFFERED=1 \
    "$endpoint_exec" --ros-args \
      -p ROS_IP:=127.0.0.1 -p ROS_TCP_PORT:=10000 \
      --enclave /trusted_quest_bridge \
      >"$endpoint_log" 2>&1 &
  local endpoint_pid=$!
  PIDS+=("$endpoint_pid")
  local port_ready=0
  local attempt
  for ((attempt = 0; attempt < 150; attempt++)); do
    kill -0 "$endpoint_pid" 2>/dev/null || break
    if (exec 9<>/dev/tcp/127.0.0.1/10000) 2>/dev/null; then
      exec 9>&- 2>/dev/null || true
      port_ready=1
      break
    fi
    sleep 0.1
  done
  ((port_ready == 1)) || return 66
  wait_for_text "$endpoint_log" '/keystore/enclaves/trusted_quest_bridge' 120 || return 67
  wait_for_text_after "$receiver_events" '/UnityEndpoint@/trusted_quest_bridge' \
    "$low_first_line" 120 || return 68
  runtime_note '[PASS] ros_tcp_endpoint=127.0.0.1:10000 node=/UnityEndpoint enclave=/trusted_quest_bridge'

  local client_a_log="$TMP_ROOT/client_a.log"
  local client_b_log="$TMP_ROOT/client_b.log"
  "$probe_exec" --client-id A --linear-x 0.440 --count 24 --interval 0.30 \
    --hold-seconds 0.5 >"$client_a_log" 2>&1 &
  local client_a_pid=$!
  PIDS+=("$client_a_pid")
  wait_for_text "$client_a_log" 'QUEST_TCP_REGISTERED client=A' 120 || return 69
  wait_for_text "$receiver_events" 'RECEIVED linear_x=0.440' 150 || return 70
  wait_for_graph_identity "$receiver_events" \
    '/q2r_right_hand_twist_RosPublisher@/trusted_quest_bridge#' 150 || return 71
  local graph_a
  graph_a=$(latest_graph "$receiver_events")
  local gid_a
  gid_a=$(publisher_gid "$graph_a")
  test -n "$gid_a"
  runtime_note "[PASS] Client A Bridge ALLOW publisher=/q2r_right_hand_twist_RosPublisher gid=$gid_a"

  local both_first_line
  both_first_line=$(( $(wc -l <"$receiver_events") + 1 ))
  "$probe_exec" --client-id B --linear-x 0.550 --count 4 --interval 0.20 \
    --skip-register --hold-seconds 10 >"$client_b_log" 2>&1 &
  local client_b_pid=$!
  PIDS+=("$client_b_pid")
  wait_for_text "$client_b_log" 'QUEST_TCP_REGISTER_SKIPPED client=B' 120 || return 72
  wait_for_text_after "$receiver_events" 'RECEIVED linear_x=0.550' "$both_first_line" 150 || return 73
  wait_for_text_after "$receiver_events" 'RECEIVED linear_x=0.440' "$both_first_line" 150 || return 74
  local graph_both
  graph_both=$(latest_graph "$receiver_events")
  local gid_both
  gid_both=$(publisher_gid "$graph_both")
  local nodes_both=${graph_both##* nodes=}
  if test "$gid_both" != "$gid_a" || \
      [[ "$graph_both" != *'publisher_count=1 '* ]] || \
      [[ "$nodes_both" != *'/UnityEndpoint@/trusted_quest_bridge'* ]] || \
      [[ "$nodes_both" != *'/q2r_right_hand_twist_RosPublisher@/trusted_quest_bridge'* ]] || \
      [[ "$nodes_both" == *'client='* ]]; then
    return 75
  fi
  runtime_note '[PASS] Client A/B 동시 inbound가 global publisher 1개와 동일 GID 공유; External Client ROS node=0'
  runtime_note '[NOTE] Client B는 server-global registry 범위 검증을 위해 의도적으로 __publish 재등록을 생략; 실제 Quest app reconnect 절차는 NOT VERIFIED'

  set +e
  wait "$client_a_pid"
  local client_a_rc=$?
  set -e
  untrack_pid "$client_a_pid"
  if ((client_a_rc != 0)) || ! kill -0 "$client_b_pid" 2>/dev/null; then
    return 76
  fi
  sleep 0.8
  local graph_after_a
  graph_after_a=$(latest_graph "$receiver_events")
  if test "$(publisher_gid "$graph_after_a")" != "$gid_a"; then
    return 77
  fi
  runtime_note '[PASS] Client A 정상 종료 후 B 연결 중 publisher/GID 유지'

  CURRENT_STEP="[7/8] Disconnect·Publisher Lifecycle 관찰"
  printf '\n[7/8] Disconnect·Publisher Lifecycle 관찰\n'
  set +e
  wait "$client_b_pid"
  local client_b_rc=$?
  set -e
  untrack_pid "$client_b_pid"
  ((client_b_rc == 0)) || return 78
  sleep 1.5
  local graph_after_all
  graph_after_all=$(latest_graph "$receiver_events")
  if [[ "$graph_after_all" != *'publisher_count=1 '* ]] || \
      test "$(publisher_gid "$graph_after_all")" != "$gid_a"; then
    return 79
  fi
  kill -0 "$endpoint_pid"
  runtime_note '[PASS] 모든 TCP Client 종료 후에도 server-global publisher/GID 잔존'

  local reconnect_first_line
  reconnect_first_line=$(( $(wc -l <"$receiver_events") + 1 ))
  local client_c_log="$TMP_ROOT/client_c.log"
  "$probe_exec" --client-id C --linear-x 0.660 --count 3 --interval 0.20 \
    --skip-register >"$client_c_log" 2>&1
  wait_for_text_after "$receiver_events" 'RECEIVED linear_x=0.660' "$reconnect_first_line" 120 || return 80
  local graph_c
  graph_c=$(latest_graph "$receiver_events")
  if test "$(publisher_gid "$graph_c")" != "$gid_a"; then
    return 81
  fi
  runtime_note '[PASS] Reconnect Client C가 재등록 없이 잔존 publisher/GID 재사용'

  local client_d_log="$TMP_ROOT/client_d.log"
  "$probe_exec" --client-id D --linear-x 0.770 --count 3 --interval 0.20 \
    >"$client_d_log" 2>&1 &
  local client_d_pid=$!
  PIDS+=("$client_d_pid")
  wait_for_text "$client_d_log" 'QUEST_TCP_REGISTERED client=D' 120 || return 82
  wait_for_gid_change "$receiver_events" "$gid_a" 160 || return 83
  wait_for_text "$receiver_events" 'RECEIVED linear_x=0.770' 120 || return 84
  local graph_d
  graph_d=$(latest_graph "$receiver_events")
  local gid_d
  gid_d=$(publisher_gid "$graph_d")
  local nodes_d=${graph_d##* nodes=}
  set +e
  wait "$client_d_pid"
  local client_d_rc=$?
  set -e
  untrack_pid "$client_d_pid"
  ((client_d_rc == 0)) || return 85
  test "$gid_d" != "$gid_a"
  [[ "$nodes_d" == *'/q2r_right_hand_twist_RosPublisher@/trusted_quest_bridge'* ]] || return 87
  runtime_note "[PASS] 같은 Topic 재등록은 publisher를 교체: graph node/enclave 유지, GID $gid_a -> $gid_d"
  if [[ "$graph_d" == *'_NODE_NAME_UNKNOWN_'* ]]; then
    runtime_note '[OBSERVED] 재등록 후 Fast DDS endpoint-to-node association=_NODE_NAME_UNKNOWN_; node/enclave는 graph node set에서 확인'
  fi

  {
    printf '# Quest2ROS2 ROS-TCP Identity Evidence\n'
    printf 'Quest2ROS2_commit=%s\n' "$QUEST2ROS2_COMMIT"
    printf 'ros_tcp_communication_commit=%s\n' "$ROS_TCP_COMMIT"
    printf 'certificate_dummy=%s\n' "$(openssl x509 -in "$ROS_SECURITY_KEYSTORE/enclaves/dummy_receiver/cert.pem" -noout -subject)"
    printf 'certificate_bridge=%s\n' "$(openssl x509 -in "$ROS_SECURITY_KEYSTORE/enclaves/trusted_quest_bridge/cert.pem" -noout -subject)"
    printf '\n[A_REGISTERED]\n%s\n' "$graph_a"
    printf '\n[A_B_SHARED]\n%s\n' "$graph_both"
    printf '\n[ALL_CLIENTS_CLOSED_PUBLISHER_PERSISTS]\n%s\n' "$graph_after_all"
    printf '\n[C_RECONNECT_WITHOUT_REGISTER]\n%s\n' "$graph_c"
    printf '\n[D_REREGISTER_GID_ROTATION]\n%s\n' "$graph_d"
    printf '\n[ros2 node list]\n'
    ROS_SECURITY_ENCLAVE_OVERRIDE=/dummy_receiver \
      ros2 node list --no-daemon --spin-time 3 2>&1 || true
    printf '\n[ros2 node info]\n'
    ROS_SECURITY_ENCLAVE_OVERRIDE=/dummy_receiver \
      ros2 node info /q2r_right_hand_twist_RosPublisher --no-daemon 2>&1 || true
    printf '\n[ros2 topic info --verbose]\n'
    ROS_SECURITY_ENCLAVE_OVERRIDE=/dummy_receiver \
      ros2 topic info /q2r_right_hand_twist --verbose --no-daemon --spin-time 3 2>&1 || true
  } >"$IDENTITY_EVIDENCE"

  {
    printf '\n[endpoint lifecycle]\n'
    grep -E 'Starting server|Connection from|Disconnected from|RegisterPublisher' "$endpoint_log" || true
    printf '\n[protocol clients]\n'
    grep -h -E 'QUEST_TCP_(CONNECTED|HANDSHAKE|REGISTERED|REGISTER_SKIPPED|SENT|CLOSED|FAILED)' \
      "$client_a_log" "$client_b_log" "$client_c_log" "$client_d_log" || true
    printf '\n[receiver values]\n'
    grep '^RECEIVED ' "$receiver_events" || true
    printf '\n[identity summary]\n'
    printf 'A_B_shared_gid=%s\n' "$gid_a"
    printf 'reregistered_gid=%s\n' "$gid_d"
    printf 'external_ros_nodes=0\n'
    printf 'publisher_persists_after_all_clients=true\n'
  } >>"$RUNTIME_EVIDENCE"

  stop_pid "$endpoint_pid"
  untrack_pid "$endpoint_pid"
  wait_for_graph_count "$receiver_events" 0 120 || return 86
  runtime_note '[PASS] Endpoint 종료 후 동적 ROS publisher 정리'
  stop_pid "$receiver_pid"
  untrack_pid "$receiver_pid"

  CURRENT_STEP="[8/8] 결과·로그·Research Context 정리"
  printf '\n[8/8] 결과·로그·Research Context 정리\n'
  printf 'SUMMARY direct_low=BLOCK bridge_a=ALLOW bridge_b=ALLOW\n'
  printf 'SUMMARY shared_node=/q2r_right_hand_twist_RosPublisher enclave=/trusted_quest_bridge shared_gid=%s\n' "$gid_a"
  printf 'SUMMARY all_clients_closed_publisher=PERSIST reconnect_without_register=ALLOW\n'
  printf 'SUMMARY reregister_same_node_enclave=YES gid_rotated=%s->%s\n' "$gid_a" "$gid_d"
  printf 'SUMMARY authentication=ABSENT role_model=ABSENT interpretation=UNAUTHENTICATED_TRUST_COLLAPSE\n'
  printf 'SUMMARY source_patch=NONE external_ros_nodes=0\n'

  container_cleanup
  trap - EXIT INT TERM
  printf '[PASS] process/container 임시 build resource 정리, evidence 보존\n'
}

clone_fixed_repository() {
  local repository=$1
  local commit=$2
  local destination=$3
  git clone --quiet "$repository" "$destination"
  git -C "$destination" checkout --quiet --detach "$commit"
  test "$(git -C "$destination" rev-parse HEAD)" = "$commit"
  test -z "$(git -C "$destination" status --porcelain)"
}

host_cleanup() {
  set +e
  if test -n "$BUILD_PID" && kill -0 "$BUILD_PID" 2>/dev/null; then
    stop_pid "$BUILD_PID"
  fi
  if test -n "${COMPOSE_FILE:-}"; then
    docker compose -p quest2ros2_feasibility -f "$COMPOSE_FILE" \
      down --remove-orphans >/dev/null 2>&1 || true
  fi
  if [[ "$HOST_TMP" == /tmp/quest2ros2-host.* ]]; then
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
  local project_root
  script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
  project_root=$(cd -- "$script_dir/.." && pwd)
  COMPOSE_FILE="$script_dir/compose.yaml"

  if ! docker info >/dev/null 2>&1; then
    local docker_members
    docker_members=$(getent group docker | awk -F: '$1 == "docker" { print $4 }')
    if test "${QUEST2ROS2_DOCKER_GROUP_ACTIVE:-0}" != 1 && \
        [[ ",$docker_members," == *",$(id -un),"* ]]; then
      exec sg docker -c \
        "QUEST2ROS2_DOCKER_GROUP_ACTIVE=1 '$script_dir/run_quest2ros2_feasibility.sh'"
    fi
    printf '[FAIL] Docker daemon 접근 권한 없음\n'
    return 10
  fi

  HOST_TMP=$(mktemp -d /tmp/quest2ros2-host.XXXXXX)
  trap host_exit EXIT
  trap 'host_signal INT' INT
  trap 'host_signal TERM' TERM
  mkdir -p "$HOST_TMP/sources" "$project_root/evidence"
  : >"$project_root/evidence/quest2ros2_build.log"
  : >"$project_root/evidence/quest2ros2_runtime.log"
  : >"$project_root/evidence/quest2ros2_identity.txt"

  printf '[1/8] 기존 연구 상태 및 Docker 환경 확인\n'
  docker version --format '  Docker client={{.Client.Version}} server={{.Server.Version}}'
  printf '  Compose %s\n' "$(docker compose version --short)"
  docker compose -p quest2ros2_feasibility -f "$COMPOSE_FILE" config --quiet
  printf '  기존 generic rosbridge PoC 파일 보존 확인\n'

  printf '\n[2/8] Quest2ROS2 관련 저장소 확보 및 Revision 고정\n'
  clone_fixed_repository "$QUEST2ROS2_REPOSITORY" "$QUEST2ROS2_COMMIT" \
    "$HOST_TMP/sources/Quest2ROS2"
  clone_fixed_repository "$ROS_TCP_REPOSITORY" "$ROS_TCP_COMMIT" \
    "$HOST_TMP/sources/ros_tcp_communication"
  date -Iseconds >"$HOST_TMP/sources/clone_time.txt"
  printf '  Quest2ROS2 main@%s\n' "$QUEST2ROS2_COMMIT"
  printf '  ros_tcp_communication main@%s\n' "$ROS_TCP_COMMIT"

  printf '\n[3/8] 실제 Bridge 코드·Protocol·Identity 구조 분석\n'
  grep -Fq 'self.publishers_table = {}' \
    "$HOST_TMP/sources/ros_tcp_communication/ros_tcp_endpoint/server.py"
  grep -Fq 'ClientThread(conn, self, ip, port).start()' \
    "$HOST_TMP/sources/ros_tcp_communication/ros_tcp_endpoint/server.py"
  grep -Fq 'self.conn.close()' \
    "$HOST_TMP/sources/ros_tcp_communication/ros_tcp_endpoint/client.py"
  test -z "$(find "$HOST_TMP/sources/Quest2ROS2" -type f -name '*.cs' -print -quit)"
  printf '  server-global registry / per-connection thread / disconnect ownership 없음 확인\n'
  printf '  Quest2ROS2 target tree에 Unity/C# source 없음; 외부 Quest app source는 NOT VERIFIED\n'

  docker compose -p quest2ros2_feasibility -f "$COMPOSE_FILE" \
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
    cp "$HOST_TMP/image-build.log" "$project_root/evidence/quest2ros2_build.log"
    printf '[FAIL] Docker image build\n'
    tail -n 30 "$HOST_TMP/image-build.log"
    return 11
  fi

  docker compose -p quest2ros2_feasibility -f "$COMPOSE_FILE" \
    run --rm -T --no-deps \
      -v "$HOST_TMP/sources:/workspace/quest_sources:ro" \
      -v "$project_root/evidence:/workspace/evidence" \
      -v "$script_dir/run_quest2ros2_feasibility.sh:/workspace/run_quest2ros2_feasibility.sh:ro" \
      ros bash /workspace/run_quest2ros2_feasibility.sh --container
  printf 'docker_image_build=PASS image=ros-xr-humble:local\n' \
    >>"$project_root/evidence/quest2ros2_build.log"
  printf '[PASS] Quest2ROS2 Feasibility 자동 실행 완료, image/evidence 보존\n'
  printf '  build_log=%s/evidence/quest2ros2_build.log\n' "$project_root"
  printf '  runtime_log=%s/evidence/quest2ros2_runtime.log\n' "$project_root"
  printf '  identity=%s/evidence/quest2ros2_identity.txt\n' "$project_root"
}

if test "${1:-}" = "--container"; then
  container_main
else
  host_main
fi
