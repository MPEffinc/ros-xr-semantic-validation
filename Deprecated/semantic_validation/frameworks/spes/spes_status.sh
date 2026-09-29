#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
test $# -eq 1 || { echo "usage: $0 <run-id>" >&2; exit 2; }
source "$root/semantic_validation/logs/$1/state.env"
ssh rosxr bash -s -- "$remote_dir" <<'REMOTE'
marker="$1"
python3 - "$marker" <<'PY'
import pathlib, sys
marker = sys.argv[1]
for proc in pathlib.Path('/proc').glob('[0-9]*'):
    try:
        command = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode()
    except OSError:
        continue
    if 'semantic_robot_sink' in command and f'log_dir:={marker}' in command:
        print('PI_SINK_RUNNING')
        raise SystemExit(0)
print('PI_SINK_STOPPED')
PY
REMOTE
test -f "$result_dir/summary.json" && cat "$result_dir/summary.json" || true
