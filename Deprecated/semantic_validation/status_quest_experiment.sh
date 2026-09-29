#!/usr/bin/env bash
set -euo pipefail

validation_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
state_dir="${validation_root}/run/spes_quest_hw"
pid_file="${state_dir}/server.pid"
backend=""
systemd_unit=""
[[ -f "${state_dir}/backend" ]] && backend="$(<"${state_dir}/backend")"
[[ -f "${state_dir}/systemd_unit" ]] && systemd_unit="$(<"${state_dir}/systemd_unit")"

if [[ ! -f "${pid_file}" ]]; then
    echo "SERVER=NOT_RUNNING"
    exit 1
fi
server_pid="$(<"${pid_file}")"
if [[ "${backend}" == "systemd_user" ]]; then
    if [[ -z "${systemd_unit}" ]] || ! systemctl --user is-active --quiet "${systemd_unit}"; then
        echo "SERVER=NOT_RUNNING"
        echo "SYSTEMD_UNIT=${systemd_unit:-UNKNOWN}"
        exit 1
    fi
    server_pid="$(systemctl --user show --property=MainPID --value "${systemd_unit}")"
fi
if [[ ! "${server_pid}" =~ ^[0-9]+$ ]] || ! kill -0 "${server_pid}" 2>/dev/null; then
    echo "SERVER=NOT_RUNNING"
    echo "STALE_PID=${server_pid}"
    exit 1
fi
cmdline="$(tr '\0' ' ' <"/proc/${server_pid}/cmdline")"
if [[ "${cmdline}" != *"semantic_validation/harness/spes_hardware_server.py"* ]]; then
    echo "SERVER=NOT_RUNNING"
    echo "PID_IDENTITY_MISMATCH=${server_pid}"
    exit 2
fi

echo "SERVER=RUNNING"
echo "PID=${server_pid}"
echo "RUN_ID=$(<"${state_dir}/run_id")"
echo "QUEST_URL=$(<"${state_dir}/quest_url")"
echo "RUN_DIR=$(<"${state_dir}/run_dir")"
echo "MODE=${backend:-nohup_detached}"
if [[ "${backend}" == "systemd_user" ]]; then
    echo "SYSTEMD_UNIT=${systemd_unit}"
fi
