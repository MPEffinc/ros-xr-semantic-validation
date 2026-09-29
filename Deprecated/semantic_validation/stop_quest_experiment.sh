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
    exit 0
fi
server_pid="$(<"${pid_file}")"
if [[ "${backend}" == "systemd_user" ]]; then
    if [[ -z "${systemd_unit}" ]] || ! systemctl --user is-active --quiet "${systemd_unit}"; then
        echo "SERVER=NOT_RUNNING"
        exit 0
    fi
    server_pid="$(systemctl --user show --property=MainPID --value "${systemd_unit}")"
fi
if [[ ! "${server_pid}" =~ ^[0-9]+$ ]] || ! kill -0 "${server_pid}" 2>/dev/null; then
    echo "SERVER=NOT_RUNNING"
    exit 0
fi
cmdline="$(tr '\0' ' ' <"/proc/${server_pid}/cmdline")"
if [[ "${cmdline}" != *"semantic_validation/harness/spes_hardware_server.py"* ]]; then
    echo "Refusing to stop PID ${server_pid}: process identity mismatch" >&2
    exit 2
fi

if [[ "${backend}" == "systemd_user" ]]; then
    systemctl --user stop "${systemd_unit}"
else
    kill -TERM "${server_pid}"
fi
for _attempt in $(seq 1 50); do
    if ! kill -0 "${server_pid}" 2>/dev/null; then
        echo "SERVER=STOPPED"
        echo "PID=${server_pid}"
        exit 0
    fi
    sleep 0.1
done
echo "Server did not stop within 5 seconds: PID=${server_pid}" >&2
exit 3
