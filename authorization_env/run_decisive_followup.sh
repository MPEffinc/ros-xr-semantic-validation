#!/usr/bin/env bash
set -Eeuo pipefail

HORUS_ROS2_REVISION="eca75cbf559f09ff793d8993338b2f1ffed1adfd"
HORUS_REVISION="819cdfdc74f1a0c2bd73946dc14897a533f68b61"
HORUS_SDK_REVISION="f4f00dab41910676519d545515531ec243414044"
COMPAS_XR_REVISION="b86e6fbbacdc8e84183fc08c846176a1c79304ca"
COMPAS_UNITY_REVISION="f1516ca568b101447507aebc28a594bdc358df3e"

FOLLOWUP_IMAGE="ros-xr-horus-jazzy:local"
FOLLOWUP_TRIALS=5
FOLLOWUP_OBSERVATION_SEC=10
FOLLOWUP_GOAL_DURATION_SEC=32
FOLLOWUP_LEASE_TTL_MS=1200
FOLLOWUP_REBUILD=0
FOLLOWUP_CASE_TIMEOUT_SEC=900

FOLLOWUP_REVOCATION_CONTAINER="ros-xr-followup-horus-revocation"
FOLLOWUP_HANDOFF_CONTAINER="ros-xr-followup-horus-handoff"
FOLLOWUP_FIX_CONTAINER="ros-xr-followup-horus-fix"
FOLLOWUP_COMPAS_CONTAINER="ros-xr-followup-compas"

usage() {
  printf 'Usage: %s [--trials N] [--observation-sec N] [--goal-duration-sec N] [--rebuild]\n' "$0"
}

parse_positive_integer() {
  local option_name=$1
  local option_value=$2
  if ! [[ "${option_value}" =~ ^[1-9][0-9]*$ ]]; then
    printf '[FAIL] %s requires a positive integer: %s\n' "${option_name}" "${option_value}" >&2
    return 2
  fi
}

while (($# > 0)); do
  case "$1" in
    --trials)
      parse_positive_integer "$1" "${2:-}"
      FOLLOWUP_TRIALS=$2
      shift 2
      ;;
    --observation-sec)
      parse_positive_integer "$1" "${2:-}"
      FOLLOWUP_OBSERVATION_SEC=$2
      shift 2
      ;;
    --goal-duration-sec)
      parse_positive_integer "$1" "${2:-}"
      FOLLOWUP_GOAL_DURATION_SEC=$2
      shift 2
      ;;
    --rebuild)
      FOLLOWUP_REBUILD=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf '[FAIL] unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

followup_cleanup() {
  set +e
  docker rm -f \
    "${FOLLOWUP_REVOCATION_CONTAINER}" \
    "${FOLLOWUP_HANDOFF_CONTAINER}" \
    "${FOLLOWUP_FIX_CONTAINER}" \
    "${FOLLOWUP_COMPAS_CONTAINER}" >/dev/null 2>&1 || true
}

followup_exit() {
  local followup_rc=$?
  trap - EXIT INT TERM
  followup_cleanup
  exit "${followup_rc}"
}

verify_revision() {
  local repository_path=$1
  local expected_revision=$2
  local observed_revision
  local repository_changes

  observed_revision=$(git -C "${repository_path}" rev-parse HEAD)
  if test "${observed_revision}" != "${expected_revision}"; then
    printf '[FAIL] revision mismatch: %s expected=%s observed=%s\n' \
      "${repository_path}" "${expected_revision}" "${observed_revision}"
    return 1
  fi
  repository_changes=$(git -C "${repository_path}" status --porcelain)
  if [[ -n "${repository_changes}" ]]; then
    printf '[FAIL] fixed framework checkout is dirty: %s\n%s\n' \
      "${repository_path}" "${repository_changes}"
    return 1
  fi
  printf '  %s @ %s (clean)\n' "${repository_path##*/}" "${observed_revision}"
}

screen_filter() {
  awk '
    /HORUS_LONG_ACTION_JSON_BEGIN|COMPAS_EXECUTOR_JSON_BEGIN/ { in_json=1; next }
    /HORUS_LONG_ACTION_JSON_END|COMPAS_EXECUTOR_JSON_END/ { in_json=0; next }
    !in_json { print; fflush() }
  '
}

run_horus_suite() {
  local container_name=$1
  local suite=$2
  local log_path=$3
  local domain_id=$4
  local source_patch=${5:-}
  local suite_args
  local run_rc
  local -a docker_args

  suite_args="--suite ${suite} --trials ${FOLLOWUP_TRIALS} --observation-sec ${FOLLOWUP_OBSERVATION_SEC} --goal-duration-sec ${FOLLOWUP_GOAL_DURATION_SEC} --lease-ttl-ms ${FOLLOWUP_LEASE_TTL_MS}"
  if [[ -n "${source_patch}" ]]; then
    suite_args+=" --runtime-label test-only-fix"
  fi
  docker_args=(
    docker run --rm --network none
    --name "${container_name}"
    -v "${FOLLOWUP_ROOT}:/workspace:ro"
    -e HORUS_PROBE_PATH=/workspace/authorization_env/horus_long_action_probe.py
    -e "HORUS_PROBE_ARGS=${suite_args}"
    -e "HORUS_ROS_DOMAIN_ID=${domain_id}"
  )
  if [[ -n "${source_patch}" ]]; then
    docker_args+=( -e "HORUS_SOURCE_PATCH=${source_patch}" )
  fi
  docker_args+=( "${FOLLOWUP_IMAGE}" bash /workspace/authorization_env/run_horus_runtime_in_container.sh )

  set +e
  timeout --foreground --signal=TERM "${FOLLOWUP_CASE_TIMEOUT_SEC}s" \
    "${docker_args[@]}" 2>&1 | tee -a "${log_path}" | screen_filter
  run_rc=${PIPESTATUS[0]}
  set -e
  printf 'suite=%s rc=%s\n' "${suite}" "${run_rc}" | tee -a "${log_path}"
  return "${run_rc}"
}

run_compas_validation() {
  local log_path=$1
  local run_rc

  set +e
  timeout --foreground --signal=TERM "${FOLLOWUP_CASE_TIMEOUT_SEC}s" \
    docker run --rm --network none \
      --name "${FOLLOWUP_COMPAS_CONTAINER}" \
      -v "${FOLLOWUP_ROOT}:/workspace:ro" \
      -e COMPAS_PROBE_PATH=/workspace/authorization_env/compas_executor_probe.py \
      "${FOLLOWUP_IMAGE}" \
      bash /workspace/authorization_env/run_compas_runtime_in_container.sh \
      2>&1 | tee -a "${log_path}" | screen_filter
  run_rc=${PIPESTATUS[0]}
  set -e
  printf 'suite=compas_executor rc=%s\n' "${run_rc}" | tee -a "${log_path}"
  return "${run_rc}"
}

write_initial_summary() {
  local summary_path=$1
  local revocation_rc=$2
  local handoff_rc=$3
  local fix_rc=$4
  local compas_rc=$5
  local revocation_rows=""
  local handoff_rows=""
  local compas_result="structured result unavailable"

  if command -v jq >/dev/null 2>&1; then
    revocation_rows=$(awk '
      /HORUS_LONG_ACTION_JSON_BEGIN/ { capture=1; next }
      /HORUS_LONG_ACTION_JSON_END/ { capture=0 }
      capture
    ' "${FOLLOWUP_REVOCATION_LOG}" | jq -r '
      .aggregate | to_entries[] |
      "| `\(.key)` | `\(.value.trials_complete)/\(.value.trials_requested)` | `\(.value.cancel_requests_at_measurement_end)` | \(.value.outcomes | to_entries | map("`\(.key)`=\(.value)") | join(", ")) |"
    ' 2>/dev/null) || revocation_rows=""
    handoff_rows=$(awk '
      /HORUS_LONG_ACTION_JSON_BEGIN/ { capture=1; next }
      /HORUS_LONG_ACTION_JSON_END/ { capture=0 }
      capture
    ' "${FOLLOWUP_HANDOFF_LOG}" | jq -sr '
      .[] as $suite | $suite.aggregate | to_entries[] |
      "| `\($suite.runtime_label)` | `\(.key)` | `\(.value.trials_complete)/\(.value.trials_requested)` | `\(.value.cancel_requests_at_measurement_end)` | \(.value.outcomes | to_entries | map("`\(.key)`=\(.value)") | join(", ")) |"
    ' 2>/dev/null) || handoff_rows=""
    compas_result=$(awk '
      /COMPAS_EXECUTOR_JSON_BEGIN/ { capture=1; next }
      /COMPAS_EXECUTOR_JSON_END/ { capture=0 }
      capture
    ' "${FOLLOWUP_COMPAS_LOG}" | jq -r '
      "`\(.verdict)`; Case `\(.executor_classification.case)`; physical execution `\(.executor_classification.physical_execution)`; T_A to T_B robot-input test `\(.executor_classification.ta_to_tb_robot_input_test)`"
    ' 2>/dev/null) || compas_result="structured result unavailable"
  fi

  if [[ -z "${revocation_rows}" ]]; then
    revocation_rows='| structured result unavailable | - | - | - |'
  fi
  if [[ -z "${handoff_rows}" ]]; then
    handoff_rows='| - | structured result unavailable | - | - | - |'
  fi

  {
    printf '# Decisive Follow-up Evidence Summary\n\n'
    printf -- '- Generated: %s\n' "$(date -Iseconds)"
    printf -- '- HORUS revision: `%s`\n' "${HORUS_ROS2_REVISION}"
    printf -- '- COMPAS XR revision: `%s`\n' "${COMPAS_XR_REVISION}"
    printf -- '- Trials per revocation/handoff case: `%s`\n' "${FOLLOWUP_TRIALS}"
    printf -- '- Observation window: `%s s`\n' "${FOLLOWUP_OBSERVATION_SEC}"
    printf -- '- Dummy goal duration: `%s s`\n' "${FOLLOWUP_GOAL_DURATION_SEC}"
    printf -- '- Runtime isolation: Docker `--network none`, loopback listeners, no privileged mode\n\n'
    printf '## Runner status\n\n'
    printf '| Suite | Exit status |\n|---|---:|\n'
    printf '| HORUS explicit cancel + R1/R2/R3 | `%s` |\n' "${revocation_rc}"
    printf '| HORUS R4 handoff/conflict | `%s` |\n' "${handoff_rc}"
    printf '| HORUS test-only minimal fix | `%s` |\n' "${fix_rc}"
    printf '| COMPAS executor validation | `%s` |\n\n' "${compas_rc}"
    printf '## Unmodified HORUS aggregate\n\n'
    printf '| Test | Complete | Cancel callbacks | Outcome |\n|---|---:|---:|---|\n'
    printf '%s\n\n' "${revocation_rows}"
    printf '## Handoff and test-only patch aggregate\n\n'
    printf '| Runtime | Test | Complete | Cancel callbacks | Outcome |\n|---|---|---:|---:|---|\n'
    printf '%s\n\n' "${handoff_rows}"
    printf '## COMPAS executor boundary\n\n%s\n\n' "${compas_result}"
    printf 'Structured per-trial timestamps, UUIDs, checkpoints, feedback, cleanup, and modeled distances are retained between JSON markers in the linked raw logs. '
    printf 'The scoped research interpretation is maintained in `DECISIVE_FOLLOWUP_RESULTS.md`.\n\n'
    printf '## Evidence\n\n'
    printf -- '- [HORUS long-run log](/home/cclab/ros_xr/evidence/horus_revocation_longrun.log)\n'
    printf -- '- [HORUS handoff and fix log](/home/cclab/ros_xr/evidence/horus_action_handoff.log)\n'
    printf -- '- [COMPAS executor validation log](/home/cclab/ros_xr/evidence/compas_executor_validation.log)\n'
  } >"${summary_path}"
}

FOLLOWUP_SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
FOLLOWUP_ROOT=$(cd -- "${FOLLOWUP_SCRIPT_DIR}/.." && pwd)
FOLLOWUP_EVIDENCE_DIR="${FOLLOWUP_ROOT}/evidence"
FOLLOWUP_REVOCATION_LOG="${FOLLOWUP_EVIDENCE_DIR}/horus_revocation_longrun.log"
FOLLOWUP_HANDOFF_LOG="${FOLLOWUP_EVIDENCE_DIR}/horus_action_handoff.log"
FOLLOWUP_COMPAS_LOG="${FOLLOWUP_EVIDENCE_DIR}/compas_executor_validation.log"
FOLLOWUP_SUMMARY="${FOLLOWUP_EVIDENCE_DIR}/decisive_followup_summary.md"

if ! docker info >/dev/null 2>&1; then
  docker_members=$(getent group docker | awk -F: '$1 == "docker" { print $4 }')
  if test "${FOLLOWUP_DOCKER_GROUP_ACTIVE:-0}" != 1 && \
    [[ ",${docker_members}," == *",$(id -un),"* ]]; then
    rebuild_arg=""
    if ((FOLLOWUP_REBUILD == 1)); then
      rebuild_arg=" --rebuild"
    fi
    exec sg docker -c \
      "FOLLOWUP_DOCKER_GROUP_ACTIVE=1 '${FOLLOWUP_SCRIPT_DIR}/run_decisive_followup.sh' --trials '${FOLLOWUP_TRIALS}' --observation-sec '${FOLLOWUP_OBSERVATION_SEC}' --goal-duration-sec '${FOLLOWUP_GOAL_DURATION_SEC}'${rebuild_arg}"
  fi
  printf '[FAIL] Docker daemon access unavailable\n' >&2
  exit 10
fi

trap followup_exit EXIT INT TERM
mkdir -p "${FOLLOWUP_EVIDENCE_DIR}"

printf '[1/9] 기존 결과와 환경 확인\n'
verify_revision "${FOLLOWUP_ROOT}/frameworks/horus_ros2" "${HORUS_ROS2_REVISION}"
verify_revision "${FOLLOWUP_ROOT}/frameworks/horus" "${HORUS_REVISION}"
verify_revision "${FOLLOWUP_ROOT}/frameworks/horus_sdk" "${HORUS_SDK_REVISION}"
verify_revision "${FOLLOWUP_ROOT}/frameworks/compas_xr" "${COMPAS_XR_REVISION}"
verify_revision "${FOLLOWUP_ROOT}/frameworks/compas_xr_unity_assembly" "${COMPAS_UNITY_REVISION}"
docker version --format '  Docker client={{.Client.Version}} server={{.Server.Version}}'

printf '[2/9] HORUS 장시간 Action Testbed 준비\n'
if ! docker image inspect "${FOLLOWUP_IMAGE}" >/dev/null 2>&1 || ((FOLLOWUP_REBUILD == 1)); then
  docker build -t "${FOLLOWUP_IMAGE}" "${FOLLOWUP_SCRIPT_DIR}" \
    >/tmp/decisive_followup_image_build.log 2>&1 || {
      tail -80 /tmp/decisive_followup_image_build.log
      exit 11
    }
  printf '  image built: %s\n' "${FOLLOWUP_IMAGE}"
else
  printf '  image reused: %s\n' "${FOLLOWUP_IMAGE}"
fi

followup_timestamp=$(date -Iseconds)
{
  printf 'timestamp=%s\nrevision=%s\n' "${followup_timestamp}" "${HORUS_ROS2_REVISION}"
  printf 'test_ids=EXPLICIT_CANCEL,R1_RELEASE,R2_TTL,R3_DISCONNECT\n'
  printf 'trials=%s observation_sec=%s goal_duration_sec=%s\n' \
    "${FOLLOWUP_TRIALS}" "${FOLLOWUP_OBSERVATION_SEC}" "${FOLLOWUP_GOAL_DURATION_SEC}"
} >"${FOLLOWUP_REVOCATION_LOG}"
{
  printf 'timestamp=%s\nrevision=%s\n' "${followup_timestamp}" "${HORUS_ROS2_REVISION}"
  printf 'test_ids=R4_HANDOFF,TEST_ONLY_MINIMAL_FIX\n'
  printf 'trials=%s observation_sec=%s goal_duration_sec=%s\n' \
    "${FOLLOWUP_TRIALS}" "${FOLLOWUP_OBSERVATION_SEC}" "${FOLLOWUP_GOAL_DURATION_SEC}"
} >"${FOLLOWUP_HANDOFF_LOG}"
{
  printf 'timestamp=%s\nrevision=%s\nunity_revision=%s\n' \
    "${followup_timestamp}" "${COMPAS_XR_REVISION}" "${COMPAS_UNITY_REVISION}"
  printf 'test_ids=COMPAS_EXECUTOR_AUDIT\n'
} >"${FOLLOWUP_COMPAS_LOG}"

overall_rc=0

printf '[3/9] Explicit Cancel 기준선\n'
printf '[4/9] Release / TTL / Disconnect 장시간 실험\n'
if run_horus_suite \
  "${FOLLOWUP_REVOCATION_CONTAINER}" revocation "${FOLLOWUP_REVOCATION_LOG}" 92; then
  revocation_rc=0
else
  revocation_rc=$?
  overall_rc=1
fi

printf '[5/9] Lease Handoff와 충돌 Action 실험\n'
if run_horus_suite \
  "${FOLLOWUP_HANDOFF_CONTAINER}" handoff "${FOLLOWUP_HANDOFF_LOG}" 93; then
  handoff_rc=0
else
  handoff_rc=$?
  overall_rc=1
fi

printf '[6/9] 최소 Fix Coverage 실험\n'
printf '  second action: official adapter 없음; Nav2 epoch isolation으로 제한\n'
printf '\n--- TEST-ONLY PATCH RUN ---\n' >>"${FOLLOWUP_HANDOFF_LOG}"
if run_horus_suite \
  "${FOLLOWUP_FIX_CONTAINER}" fix "${FOLLOWUP_HANDOFF_LOG}" 94 \
  /workspace/authorization_env/horus_revocation_cancel_test.patch; then
  fix_rc=0
else
  fix_rc=$?
  overall_rc=1
fi

printf '[7/9] COMPAS Executor 추적 및 실행 실험\n'
if run_compas_validation "${FOLLOWUP_COMPAS_LOG}"; then
  compas_rc=0
else
  compas_rc=$?
  overall_rc=1
fi

printf '[8/9] 반복 실행·증거 정리\n'
write_initial_summary \
  "${FOLLOWUP_SUMMARY}" "${revocation_rc}" "${handoff_rc}" "${fix_rc}" "${compas_rc}"

followup_cleanup
if docker ps -a --format '{{.Names}}' | grep -Eq '^ros-xr-followup-'; then
  printf '[FAIL] disposable follow-up container remained\n'
  overall_rc=1
fi

printf '[9/9] 연구 판정 및 Handoff 작성\n'
printf '  summary: %s\n' "${FOLLOWUP_SUMMARY}"
printf '  results document: %s\n' "${FOLLOWUP_ROOT}/DECISIVE_FOLLOWUP_RESULTS.md"
printf 'DECISIVE_FOLLOWUP_RUNTIME_COMPLETE overall_rc=%s\n' "${overall_rc}"

trap - EXIT INT TERM
exit "${overall_rc}"
