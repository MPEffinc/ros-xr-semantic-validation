#!/usr/bin/env bash
# Host-side runner for PHASE 6 (see experiments/PROTOCOL.md). Usage: scripts/run_phase6.sh [run_id]
set -Eeuo pipefail
AC=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
REPO=$(cd "$AC/.." && pwd)
RUN_ID=${1:-ac6_$(date -u +%Y%m%dT%H%M%SZ)}
OUT="$AC/results/raw/$RUN_ID"; mkdir -p "$OUT"
HORUS="$AC/references/upstream/horus_ros2"; DEP="$REPO/Deprecated/authorization_env"
IMAGE=ros-xr-horus-nav2-jazzy:local
[[ $(git -C "$HORUS" rev-parse HEAD) == eca75cbf559f09ff793d8993338b2f1ffed1adfd ]]
[[ -z $(git -C "$HORUS" status --porcelain) ]]
{
  echo "run_id=$RUN_ID"; echo "started_utc=$(date -u +%FT%TZ)"
  echo "repo_head=$(git -C "$REPO" rev-parse HEAD)"; echo "repo_dirty_paths=$(git -C "$REPO" status --porcelain | wc -l)"
  echo "horus_ros2=$(git -C "$HORUS" rev-parse HEAD)"
  echo "image=$IMAGE $(docker image inspect --format '{{.Id}}' $IMAGE)"
  echo "env: AC_TRIALS=${AC_TRIALS:-5} AC_CASES=${AC_CASES:-all} AC_BASELINES=${AC_BASELINES:-all}"
} >"$OUT/manifest.txt"
sha256sum "$AC/experiments/harness/"*.py "$AC/experiments/harness/"*.sh "$AC/experiments/baselines/"*.patch "$AC/experiments/PROTOCOL.md" \
  "$DEP/horus_runtime_probe.py" | sed "s#$REPO/##" >"$OUT/inputs.sha256"
docker run --rm --network none --name "ac6-$RUN_ID" \
  -e AC_TRIALS -e AC_CASES -e AC_BASELINES -e AC_UID="$(id -u)" \
  -v "$HORUS:/src/horus_ros2:ro" -v "$AC/experiments:/ac:ro" -v "$DEP:/deprecated_env:ro" \
  -v "$OUT:/out:rw" "$IMAGE" bash /ac/harness/run_in_container.sh 2>&1 | tee "$OUT/console.log"
echo "finished_utc=$(date -u +%FT%TZ)" >>"$OUT/manifest.txt"
echo "$OUT"
