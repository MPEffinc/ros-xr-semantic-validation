#!/usr/bin/env bash
# Apply only to PIDs recorded by this S2 launch instance.
set -euo pipefail
log_root="$1"
echo 'S2_OWNED_TEARDOWN_BEGIN'
while read -r pid label; do
  if [ "$label" = bag_record ]; then
    kill -INT "$pid" 2>/dev/null || true
  fi
done <"${log_root}/summaries/owned_pids.txt"
sleep 3
while read -r pid label; do
  if [ "$label" != bag_record ]; then
    kill -INT "$pid" 2>/dev/null || true
  fi
done <"${log_root}/summaries/owned_pids.txt"
sleep 3
echo 'S2_OWNED_TEARDOWN_END'
