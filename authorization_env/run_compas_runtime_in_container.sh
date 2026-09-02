#!/usr/bin/env bash
set -Eeuo pipefail

COMPAS_BROKER_LOG=/tmp/compas_authorization_mosquitto.log
COMPAS_BROKER_CONFIG=/tmp/compas_authorization_mosquitto.conf
COMPAS_BROKER_PASSWORD_FILE=/tmp/compas_authorization_passwords
COMPAS_BROKER_PID=""
COMPAS_PROBE_PATH="${COMPAS_PROBE_PATH:-/workspace/authorization_env/compas_runtime_probe.py}"
COMPAS_PROBE_ARGS="${COMPAS_PROBE_ARGS:-}"

cleanup_compas_runtime() {
  if [[ -n "${COMPAS_BROKER_PID}" ]]; then
    kill "${COMPAS_BROKER_PID}" 2>/dev/null || true
    wait "${COMPAS_BROKER_PID}" 2>/dev/null || true
  fi
}
trap cleanup_compas_runtime EXIT INT TERM

if [[ "${COMPAS_REQUIRE_AUTH:-0}" == 1 ]]; then
  : "${COMPAS_MQTT_USERNAME:=xr2act-primary}"
  : "${COMPAS_MQTT_PASSWORD:=xr2act-local-only-credential}"
  mosquitto_passwd -b -c "${COMPAS_BROKER_PASSWORD_FILE}" \
    "${COMPAS_MQTT_USERNAME}" "${COMPAS_MQTT_PASSWORD}"
  chown mosquitto:mosquitto "${COMPAS_BROKER_PASSWORD_FILE}"
  chmod 0640 "${COMPAS_BROKER_PASSWORD_FILE}"
  printf '%s\n' \
    'listener 1883 127.0.0.1' \
    'allow_anonymous false' \
    "password_file ${COMPAS_BROKER_PASSWORD_FILE}" \
    'persistence false' \
    'log_type error' \
    >"${COMPAS_BROKER_CONFIG}"
  export COMPAS_MQTT_USERNAME COMPAS_MQTT_PASSWORD
  echo "[COMPAS 1/2] Loopback-only credential-authenticated MQTT broker"
else
  printf '%s\n' \
    'listener 1883 127.0.0.1' \
    'allow_anonymous true' \
    'persistence false' \
    'log_type error' \
    >"${COMPAS_BROKER_CONFIG}"
  echo "[COMPAS 1/2] Loopback-only anonymous MQTT broker"
fi

mosquitto -c "${COMPAS_BROKER_CONFIG}" >"${COMPAS_BROKER_LOG}" 2>&1 &
COMPAS_BROKER_PID=$!
for _ in $(seq 1 50); do
  if nc -z 127.0.0.1 1883; then
    break
  fi
  sleep 0.1
done
if ! nc -z 127.0.0.1 1883; then
  cat "${COMPAS_BROKER_LOG}"
  exit 1
fi

echo "[COMPAS 2/2] Runtime probe: ${COMPAS_PROBE_PATH##*/} ${COMPAS_PROBE_ARGS}"
export PYTHONPATH=/workspace/frameworks/compas_xr/src
COMPAS_PROBE_ARGV=()
if [[ -n "${COMPAS_PROBE_ARGS}" ]]; then
  read -r -a COMPAS_PROBE_ARGV <<<"${COMPAS_PROBE_ARGS}"
fi
/opt/compas-venv/bin/python "${COMPAS_PROBE_PATH}" "${COMPAS_PROBE_ARGV[@]}"
echo "COMPAS_RUNTIME_PROBE_COMPLETE"
