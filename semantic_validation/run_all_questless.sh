#!/usr/bin/env bash
# Re-runnable, observation-only orchestration.  It intentionally does not
# attach Quest/ADB and never launches a robot driver.
set -u -o pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
run_id="questless_all_$(date -u +%Y%m%dT%H%M%SZ)"
summary="$root/semantic_validation/logs/$run_id/summary.tsv"
mkdir -p "$(dirname "$summary")"
printf 'component\tstatus\tnote\n' > "$summary"
step() { local name="$1"; shift; if "$@"; then printf '%s\tPASS\t%s\n' "$name" "$*" >> "$summary"; else printf '%s\tBLOCKED_OR_FAIL\t%s\n' "$name" "$*" >> "$summary"; fi; }
step docker_pi_preflight "$root/semantic_validation/frameworks/spes/spes_preflight.sh"
step picknik_endpoint sg docker -c "docker run --rm --network host -v '$root:/workspace' -w /workspace ros-xr-humble:local bash -lc 'source /opt/ros/humble/setup.bash; source ros_env/ros2_ws/install/setup.bash; ros2 pkg executables ros_tcp_endpoint | grep -qx \"ros_tcp_endpoint default_server_endpoint\"'"
spes_run_id="spes_${run_id}"
if "$root/semantic_validation/frameworks/spes/spes_start_all.sh" "$spes_run_id"; then
  step spes_collect "$root/semantic_validation/frameworks/spes/spes_collect.sh" "$spes_run_id"
else
  printf 'spes_runtime\tBLOCKED_OR_FAIL\tsee %s\n' "$spes_run_id" >> "$summary"
fi
"$root/semantic_validation/frameworks/spes/spes_stop_all.sh" "$spes_run_id" >/dev/null 2>&1 || true
printf 'SUMMARY=%s\n' "$summary"
cat "$summary"
