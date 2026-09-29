#!/usr/bin/env bash
set -Eeuo pipefail

HORUS_ROS2_REVISION="eca75cbf559f09ff793d8993338b2f1ffed1adfd"
HORUS_REVISION="819cdfdc74f1a0c2bd73946dc14897a533f68b61"
HORUS_SDK_REVISION="f4f00dab41910676519d545515531ec243414044"
COMPAS_XR_REVISION="b86e6fbbacdc8e84183fc08c846176a1c79304ca"
COMPAS_UNITY_REVISION="f1516ca568b101447507aebc28a594bdc358df3e"
AUTH_IMAGE="ros-xr-horus-jazzy:local"
AUTH_HORUS_CONTAINER="ros-xr-authorization-horus"
AUTH_COMPAS_CONTAINER="ros-xr-authorization-compas"

authorization_cleanup() {
  set +e
  docker rm -f "${AUTH_HORUS_CONTAINER}" >/dev/null 2>&1 || true
  docker rm -f "${AUTH_COMPAS_CONTAINER}" >/dev/null 2>&1 || true
}

authorization_exit() {
  local authorization_rc=$?
  trap - EXIT INT TERM
  authorization_cleanup
  exit "${authorization_rc}"
}

verify_revision() {
  local repository_path=$1
  local expected_revision=$2
  local observed_revision
  observed_revision=$(git -C "${repository_path}" rev-parse HEAD)
  if test "${observed_revision}" != "${expected_revision}"; then
    printf '[FAIL] revision mismatch: %s expected=%s observed=%s\n' \
      "${repository_path}" "${expected_revision}" "${observed_revision}"
    return 1
  fi
  printf '  %s @ %s\n' "${repository_path##*/}" "${observed_revision}"
}

authorization_main() {
  local authorization_script_dir
  local authorization_root
  local authorization_evidence_dir
  local authorization_timestamp
  local authorization_horus_log
  local authorization_compas_log
  local authorization_build_log

  authorization_script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
  authorization_root=$(cd -- "${authorization_script_dir}/.." && pwd)
  authorization_evidence_dir="${authorization_root}/evidence"

  if ! docker info >/dev/null 2>&1; then
    local authorization_docker_members
    authorization_docker_members=$(getent group docker | awk -F: '$1 == "docker" { print $4 }')
    if test "${AUTHORIZATION_DOCKER_GROUP_ACTIVE:-0}" != 1 && \
      [[ ",${authorization_docker_members}," == *",$(id -un),"* ]]; then
      exec sg docker -c \
        "AUTHORIZATION_DOCKER_GROUP_ACTIVE=1 '${authorization_script_dir}/run_authorization_continuity.sh'"
    fi
    printf '[FAIL] Docker daemon 접근 권한 없음\n'
    return 10
  fi

  trap authorization_exit EXIT INT TERM
  mkdir -p "${authorization_evidence_dir}"
  authorization_timestamp=$(date -Iseconds)
  authorization_horus_log="${authorization_evidence_dir}/authorization_continuity_horus_runtime.log"
  authorization_compas_log="${authorization_evidence_dir}/authorization_continuity_compas_runtime.log"
  authorization_build_log=/tmp/authorization_continuity_image_build.log

  echo "[1/5] Environment and fixed revisions"
  verify_revision "${authorization_root}/frameworks/horus_ros2" "${HORUS_ROS2_REVISION}"
  verify_revision "${authorization_root}/frameworks/horus" "${HORUS_REVISION}"
  verify_revision "${authorization_root}/frameworks/horus_sdk" "${HORUS_SDK_REVISION}"
  verify_revision "${authorization_root}/frameworks/compas_xr" "${COMPAS_XR_REVISION}"
  verify_revision "${authorization_root}/frameworks/compas_xr_unity_assembly" "${COMPAS_UNITY_REVISION}"
  docker version --format '  Docker client={{.Client.Version}} server={{.Server.Version}}'

  echo "[2/5] Isolated Jazzy/COMPAS image"
  if ! docker image inspect "${AUTH_IMAGE}" >/dev/null 2>&1 || test "${1:-}" = "--rebuild"; then
    if ! docker build -t "${AUTH_IMAGE}" "${authorization_script_dir}" \
      >"${authorization_build_log}" 2>&1; then
      tail -80 "${authorization_build_log}"
      return 11
    fi
    echo "  image built: ${AUTH_IMAGE}"
  else
    echo "  existing image reused: ${AUTH_IMAGE}"
  fi

  {
    printf 'timestamp=%s\n' "${authorization_timestamp}"
    printf 'framework=HORUS ROS 2\n'
    printf 'revision=%s\n' "${HORUS_ROS2_REVISION}"
    printf 'command_id=HORUS-A1-A6\n'
    printf 'expected=normal arbitration plus observation of fail-open/catalog/lifecycle semantics\n'
    printf 'command=docker run --rm --network none %s run_horus_runtime_in_container.sh\n' "${AUTH_IMAGE}"
  } >"${authorization_horus_log}"

  echo "[3/5] HORUS runtime: two clients, lease, catalog, Nav2 action"
  set +e
  docker run --rm --network none \
    --name "${AUTH_HORUS_CONTAINER}" \
    -v "${authorization_root}:/workspace:ro" \
    "${AUTH_IMAGE}" \
    bash /workspace/authorization_env/run_horus_runtime_in_container.sh \
    2>&1 | tee -a "${authorization_horus_log}"
  local authorization_horus_rc=${PIPESTATUS[0]}
  set -e
  if ((authorization_horus_rc != 0)); then
    printf 'verdict=FAIL rc=%s\n' "${authorization_horus_rc}" | tee -a "${authorization_horus_log}"
    return 12
  fi
  printf 'verdict=PASS\n' | tee -a "${authorization_horus_log}"

  {
    printf 'timestamp=%s\n' "${authorization_timestamp}"
    printf 'framework=COMPAS XR\n'
    printf 'revision=%s\n' "${COMPAS_XR_REVISION}"
    printf 'unity_revision=%s\n' "${COMPAS_UNITY_REVISION}"
    printf 'command_id=COMPAS-B1-B6\n'
    printf 'expected=normal handoff plus observation of identity/action/vote binding semantics\n'
    printf 'command=docker run --rm --network none %s run_compas_runtime_in_container.sh\n' "${AUTH_IMAGE}"
  } >"${authorization_compas_log}"

  echo "[4/5] COMPAS XR runtime: official schema/transport, local MQTT, inert sink"
  set +e
  docker run --rm --network none \
    --name "${AUTH_COMPAS_CONTAINER}" \
    -v "${authorization_root}:/workspace:ro" \
    "${AUTH_IMAGE}" \
    bash /workspace/authorization_env/run_compas_runtime_in_container.sh \
    2>&1 | tee -a "${authorization_compas_log}"
  local authorization_compas_rc=${PIPESTATUS[0]}
  set -e
  if ((authorization_compas_rc != 0)); then
    printf 'verdict=FAIL rc=%s\n' "${authorization_compas_rc}" | tee -a "${authorization_compas_log}"
    return 13
  fi
  printf 'verdict=PASS\n' | tee -a "${authorization_compas_log}"

  echo "[5/5] Cleanup and evidence"
  authorization_cleanup
  if docker ps -a --format '{{.Names}}' | grep -Eq \
    "^(${AUTH_HORUS_CONTAINER}|${AUTH_COMPAS_CONTAINER})$"; then
    echo "[FAIL] disposable container remained"
    return 14
  fi
  printf '  HORUS evidence: %s\n' "${authorization_horus_log}"
  printf '  COMPAS evidence: %s\n' "${authorization_compas_log}"
  echo "AUTHORIZATION_CONTINUITY_RUNTIME_COMPLETE"
  trap - EXIT INT TERM
}

authorization_main "$@"
