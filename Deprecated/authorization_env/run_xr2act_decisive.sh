#!/usr/bin/env bash
set -Eeuo pipefail

readonly HORUS_ROS2_REVISION="eca75cbf559f09ff793d8993338b2f1ffed1adfd"
readonly HORUS_REVISION="819cdfdc74f1a0c2bd73946dc14897a533f68b61"
readonly HORUS_SDK_REVISION="f4f00dab41910676519d545515531ec243414044"
readonly COMPAS_XR_REVISION="b86e6fbbacdc8e84183fc08c846176a1c79304ca"
readonly COMPAS_UNITY_REVISION="f1516ca568b101447507aebc28a594bdc358df3e"
readonly XR2ACT_IMAGE="ros-xr-horus-nav2-jazzy:local"
readonly XR2ACT_COMPAS_CONTAINER="ros-xr2act-compas"

XR2ACT_TRIALS=10
XR2ACT_TIMEOUT=5400
XR2ACT_CONTAINER_OWNED=0

usage() {
  cat <<'EOF'
Usage: run_xr2act_decisive.sh [--trials N] [--timeout-sec N]

Runs COMPAS fixed-source/authenticated-loopback tests, actual HORUS/Nav2
post-handoff timing matrix, authenticated-scope candidate audit, and negative
controls.  It uses no public broker, host network, privileged container, XR
hardware, or physical robot.
EOF
}

fail() {
  echo "[FAIL] $*" >&2
  return 1
}

cleanup() {
  local rc=$?
  set +e
  if ((XR2ACT_CONTAINER_OWNED == 1)); then
    docker rm -f "${XR2ACT_COMPAS_CONTAINER}" >/dev/null 2>&1 || true
  fi
  return "${rc}"
}
trap cleanup EXIT INT TERM

while (($# > 0)); do
  case "$1" in
    --trials)
      [[ "${2:-}" =~ ^[1-9][0-9]*$ ]] || fail "--trials requires a positive integer" || exit 2
      XR2ACT_TRIALS=$2
      shift 2
      ;;
    --timeout-sec)
      [[ "${2:-}" =~ ^[1-9][0-9]*$ ]] || fail "--timeout-sec requires a positive integer" || exit 2
      XR2ACT_TIMEOUT=$2
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      fail "unknown option: $1" || true
      usage >&2
      exit 2
      ;;
  esac
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
workspace_root=$(cd -- "${script_dir}/.." && pwd)
evidence_dir="${workspace_root}/evidence"
mkdir -p "${evidence_dir}"

if ! docker info >/dev/null 2>&1; then
  docker_members=$(getent group docker | awk -F: '$1 == "docker" { print $4 }')
  if [[ "${XR2ACT_DOCKER_GROUP_ACTIVE:-0}" != 1 && ",${docker_members}," == *",$(id -un),"* ]]; then
    quoted_script=$(printf '%q' "${script_dir}/run_xr2act_decisive.sh")
    exec sg docker -c \
      "XR2ACT_DOCKER_GROUP_ACTIVE=1 ${quoted_script} --trials ${XR2ACT_TRIALS} --timeout-sec ${XR2ACT_TIMEOUT}"
  fi
  fail "Docker daemon access unavailable"
  exit 10
fi

verify_revision() {
  local path=$1
  local expected=$2
  local observed
  observed=$(git -C "${path}" rev-parse HEAD)
  [[ "${observed}" == "${expected}" ]] || fail "revision mismatch ${path}: ${observed}"
  [[ -z "$(git -C "${path}" status --porcelain)" ]] || fail "fixed checkout dirty: ${path}"
  echo "  ${path##*/} @ ${observed} (clean)"
}

echo "[1/10] Context 및 fixed revisions 확인"
verify_revision "${workspace_root}/frameworks/horus_ros2" "${HORUS_ROS2_REVISION}"
verify_revision "${workspace_root}/frameworks/horus" "${HORUS_REVISION}"
verify_revision "${workspace_root}/frameworks/horus_sdk" "${HORUS_SDK_REVISION}"
verify_revision "${workspace_root}/frameworks/compas_xr" "${COMPAS_XR_REVISION}"
verify_revision "${workspace_root}/frameworks/compas_xr_unity_assembly" "${COMPAS_UNITY_REVISION}"
docker image inspect "${XR2ACT_IMAGE}" >/dev/null

echo "[2/10] COMPAS official execution path 탐색"
echo "[3/10] COMPAS T_A→T_B end-to-end 검증"
docker rm -f "${XR2ACT_COMPAS_CONTAINER}" >/dev/null 2>&1 || true
XR2ACT_CONTAINER_OWNED=1
set +e
docker run --rm --network none \
  --name "${XR2ACT_COMPAS_CONTAINER}" \
  -v "${workspace_root}:/workspace:ro" \
  -v "${evidence_dir}:/workspace/evidence:rw" \
  -e "XR2ACT_OUTPUT_UID=$(id -u)" \
  -e "XR2ACT_OUTPUT_GID=$(id -g)" \
  -e COMPAS_REQUIRE_AUTH=1 \
  "${XR2ACT_IMAGE}" bash -lc '
    set -uo pipefail
    output=/workspace/evidence/compas_e2e_execution.log
    : >"${output}"
    echo COMPAS_SOURCE_AUDIT_BEGIN >>"${output}"
    /opt/compas-venv/bin/python /workspace/authorization_env/compas_executor_probe.py \
      --workspace /workspace >>"${output}" 2>&1
    source_rc=$?
    echo COMPAS_SOURCE_AUDIT_END >>"${output}"
    echo COMPAS_RUNTIME_BEGIN >>"${output}"
    COMPAS_REQUIRE_AUTH=1 \
      /workspace/authorization_env/run_compas_runtime_in_container.sh \
      >>"${output}" 2>&1
    runtime_rc=$?
    echo COMPAS_RUNTIME_END >>"${output}"
    chown "${XR2ACT_OUTPUT_UID}:${XR2ACT_OUTPUT_GID}" "${output}" 2>/dev/null || true
    if ((source_rc != 0 || runtime_rc != 0)); then
      exit 1
    fi
  '
compas_rc=$?
set -e
XR2ACT_CONTAINER_OWNED=0
docker rm -f "${XR2ACT_COMPAS_CONTAINER}" >/dev/null 2>&1 || true
if ((compas_rc == 0)); then
  echo "  COMPAS source/runtime probe PASS (credential-authenticated loopback broker)"
else
  echo "  COMPAS source/runtime probe FAIL rc=${compas_rc}; continuing other tracks"
fi

echo "[4/10] HORUS post-handoff baseline 준비"
echo "  actual HorusLink + fixed HORUS + actual Nav2 loopback; ${XR2ACT_TRIALS} trials per timing mode"
echo "[5/10] HORUS stale-state / B-control interference 검증"
set +e
XR_NAV2_PROBE_MODE=post-handoff \
  "${script_dir}/run_xr_nav2_feasibility.sh" \
    --trials "${XR2ACT_TRIALS}" \
    --cases F5 \
    --revocation-delay-sec 0.5 \
    --observation-sec 1 \
    --lease-ttl-ms 1200 \
    --timeout-sec "${XR2ACT_TIMEOUT}"
horus_rc=$?
set -e
if ((horus_rc != 0)); then
  echo "  HORUS post-handoff runtime FAIL rc=${horus_rc}; continuing evidence synthesis"
fi

echo "[6/10] 실제 authenticated scope-bound bridge 후보 선정"
set +e
python3 "${script_dir}/xr2act_scope_audit.py" >"${evidence_dir}/bridge_scope_bypass.log"
scope_rc=$?
set -e
echo "[7/10] Cross-principal scope bypass 검증"
if ((scope_rc == 0)); then
  rg 'final_classification|real_authenticated_multi_principal_threat_boundary_available' \
    "${evidence_dir}/bridge_scope_bypass.log" | sed 's/^/  /'
else
  echo "  scope candidate audit failed rc=${scope_rc}"
fi

echo "[8/10] Negative Control 실행"
set +e
python3 "${script_dir}/xr2act_summarize.py" --evidence-dir "${evidence_dir}"
summary_rc=$?
set -e
if ((summary_rc == 0)); then
  rg 'test_oracle_distinguishes_safe_behavior|direct_exact_cancel_success|same_id_t_b_rejected' \
    "${evidence_dir}/negative_control.log" | sed 's/^/  /'
else
  echo "  negative-control summary failed rc=${summary_rc}"
fi

echo "[9/10] Existing-work collision 및 통합 가능성 판정"
echo "  Runtime evidence complete; claim-level collision matrix is maintained in XR2ACT_DECISIVE_RESULTS.md"

echo "[10/10] Evidence 정리 및 GPT Handoff 작성"
for name in \
  compas_e2e_execution.log \
  horus_post_handoff.log \
  bridge_scope_bypass.log \
  negative_control.log \
  xr2act_decisive_summary.md; do
  if [[ -s "${evidence_dir}/${name}" ]]; then
    echo "  ${name} $(stat -c %s "${evidence_dir}/${name}") bytes"
  else
    echo "  missing-or-empty ${name}"
  fi
done

if ((compas_rc != 0 || horus_rc != 0 || scope_rc != 0 || summary_rc != 0)); then
  exit 1
fi
echo "XR2ACT_DECISIVE_RUNTIME_COMPLETE"
