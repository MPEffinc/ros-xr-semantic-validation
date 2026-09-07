#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
test $# -eq 1 || { echo "usage: $0 <run-id>" >&2; exit 2; }
source "$root/semantic_validation/logs/$1/state.env"
ssh rosxr bash -s -- "$remote_dir" <<'REMOTE'
marker="$1"
python3 - "$marker" <<'PY'
import os, pathlib, signal, sys
marker = sys.argv[1]
stopped = []
for proc in pathlib.Path('/proc').glob('[0-9]*'):
    try:
        pid = int(proc.name)
        command = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode()
    except (OSError, ValueError):
        continue
    if 'semantic_robot_sink' in command and f'log_dir:={marker}' in command:
        os.kill(pid, signal.SIGTERM)
        stopped.append(pid)
print('stopped=' + ','.join(map(str, stopped)))
PY
REMOTE
echo "Stopped observation-only Pi sink for run=$run_id (launcher pid was $pi_pid). No driver or actuator was started."
