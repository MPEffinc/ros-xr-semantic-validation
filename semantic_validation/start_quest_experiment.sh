#!/usr/bin/env bash
set -euo pipefail

validation_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd "${validation_root}/.." && pwd)"
semantic_deps="${SEMANTIC_PY_DEPS:-/tmp/ros_xr_semantic_deps}"
run_id="${1:-spes_quest_hw_$(date -u +%Y%m%dT%H%M%SZ)}"
port="${2:-4443}"
state_dir="${validation_root}/run/spes_quest_hw"
result_root="${validation_root}/logs/quest_hw"
run_dir="${result_root}/${run_id}"
pid_file="${state_dir}/server.pid"
server_pid=""
backend=""
systemd_unit="spes_quest_hw.service"

cleanup_failed_start() {
    if [[ "${backend}" == "systemd_user" ]]; then
        systemctl --user stop "${systemd_unit}" >/dev/null 2>&1 || true
    elif [[ -n "${server_pid}" ]] && kill -0 "${server_pid}" 2>/dev/null; then
        kill -TERM "${server_pid}" 2>/dev/null || true
    fi
}
trap cleanup_failed_start ERR

if [[ ! "${run_id}" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    echo "Invalid run id: ${run_id}" >&2
    exit 2
fi

mkdir -p "${state_dir}" "${run_dir}"
if systemctl --user is-active --quiet "${systemd_unit}" 2>/dev/null; then
    echo "Experiment server already running as ${systemd_unit}" >&2
    exit 3
fi
if [[ -f "${pid_file}" ]]; then
    old_pid="$(<"${pid_file}")"
    if [[ "${old_pid}" =~ ^[0-9]+$ ]] && kill -0 "${old_pid}" 2>/dev/null; then
        echo "Experiment server already running: PID=${old_pid}" >&2
        exit 3
    fi
fi

if ! PYTHONPATH="${semantic_deps}" python3 -c 'import fastapi, numpy, transforms3d, uvicorn, websockets'; then
    echo "Hardware dependencies are missing from ${semantic_deps}." >&2
    exit 4
fi

cd "${workspace_root}"
PYTHONPATH="${semantic_deps}" python3 semantic_validation/harness/run_spes_hardware_preflight.py \
    --output "${run_dir}/preflight.jsonl"

stdout_log="${run_dir}/server.stdout.log"
stderr_log="${run_dir}/server.stderr.log"
if command -v systemd-run >/dev/null 2>&1 && systemctl --user is-system-running >/dev/null 2>&1; then
    backend="systemd_user"
    systemctl --user reset-failed "${systemd_unit}" >/dev/null 2>&1 || true
    systemd-run --user --quiet --collect --unit="${systemd_unit}" \
        --property="Type=exec" \
        --property="WorkingDirectory=${workspace_root}" \
        --property="StandardOutput=append:${stdout_log}" \
        --property="StandardError=append:${stderr_log}" \
        --setenv="PYTHONPATH=${semantic_deps}" \
        /usr/bin/python3 "${validation_root}/harness/spes_hardware_server.py" \
        --no-console \
        --host 0.0.0.0 \
        --port "${port}" \
        --run-id "${run_id}" \
        --result-root "${result_root}"
    for _attempt in $(seq 1 50); do
        server_pid="$(systemctl --user show --property=MainPID --value "${systemd_unit}" 2>/dev/null || true)"
        if [[ "${server_pid}" =~ ^[1-9][0-9]*$ ]]; then
            break
        fi
        sleep 0.1
    done
else
    backend="nohup_detached"
    nohup env PYTHONPATH="${semantic_deps}" \
        python3 semantic_validation/harness/spes_hardware_server.py \
        --no-console \
        --host 0.0.0.0 \
        --port "${port}" \
        --run-id "${run_id}" \
        --result-root "${result_root}" \
        >"${stdout_log}" 2>"${stderr_log}" </dev/null &
    server_pid=$!
fi

if [[ ! "${server_pid}" =~ ^[1-9][0-9]*$ ]]; then
    echo "Unable to resolve server PID" >&2
    exit 5
fi

printf '%s\n' "${server_pid}" >"${pid_file}"
printf '%s\n' "${run_id}" >"${state_dir}/run_id"
printf '%s\n' "${port}" >"${state_dir}/port"
printf '%s\n' "${run_dir}" >"${state_dir}/run_dir"
printf '%s\n' "${backend}" >"${state_dir}/backend"
printf '%s\n' "${systemd_unit}" >"${state_dir}/systemd_unit"

ready=false
for _attempt in $(seq 1 100); do
    if [[ "${backend}" == "systemd_user" ]]; then
        server_alive="$(systemctl --user is-active "${systemd_unit}" 2>/dev/null || true)"
    elif kill -0 "${server_pid}" 2>/dev/null; then
        server_alive="active"
    else
        server_alive="inactive"
    fi
    if [[ "${server_alive}" != "active" ]]; then
        echo "Server exited during startup. See ${stderr_log}" >&2
        exit 5
    fi
    if curl --silent --show-error --insecure --max-time 1 "https://127.0.0.1:${port}/" >/dev/null 2>&1; then
        ready=true
        break
    fi
    sleep 0.1
done
if [[ "${ready}" != true ]]; then
    echo "Server did not become HTTPS-ready. PID=${server_pid}" >&2
    exit 6
fi

lan_ip="${QUEST_HOST:-}"
if [[ -z "${lan_ip}" ]]; then
    lan_ip="$(python3 -c 'import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(("8.8.8.8",80)); print(s.getsockname()[0]); s.close()')"
fi
quest_url="https://${lan_ip}:${port}/"
printf '%s\n' "${quest_url}" >"${state_dir}/quest_url"

PYTHONPATH="${semantic_deps}" python3 semantic_validation/harness/probe_spes_server.py \
    --host 127.0.0.1 --port "${port}" >"${run_dir}/live_probe.json"
trap - ERR

echo "SERVER=RUNNING"
echo "PID=${server_pid}"
echo "RUN_ID=${run_id}"
echo "QUEST_URL=${quest_url}"
echo "RUN_DIR=${run_dir}"
echo "BACKEND=${backend}"
echo "STOP_COMMAND=${validation_root}/stop_quest_experiment.sh"
