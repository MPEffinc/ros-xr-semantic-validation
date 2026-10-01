#!/usr/bin/env bash
# Re-create the git-ignored upstream checkouts at the pinned SHAs used in systems/SOURCE_AUDIT.md.
# Usage: scripts/fetch_upstreams.sh [dest]   (default: references/upstream)
set -euo pipefail
dest="${1:-$(dirname "$0")/../references/upstream}"
mkdir -p "$dest"
while read -r name url sha; do
  [ -z "$name" ] && continue
  if [ ! -d "$dest/$name/.git" ]; then git clone -q --filter=blob:none "$url" "$dest/$name"; fi
  git -C "$dest/$name" fetch -q origin "$sha" 2>/dev/null || true
  git -C "$dest/$name" checkout -q --detach "$sha"
  echo "$name $(git -C "$dest/$name" rev-parse HEAD)"
done <<'PINS'
isaac_ros_teleop https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_teleop e80602863a0c4c94360a22b02248164c2dad6fa4
IsaacTeleop https://github.com/NVIDIA/IsaacTeleop 47f33af3cc50d01bc3d60f51d17ef0a480fa0969
IsaacLab https://github.com/isaac-sim/IsaacLab 5eef1d70f3c7f3af1e1c99eae85192b61cda52ac
XRoboToolkit-Teleop-Sample-Python https://github.com/XR-Robotics/XRoboToolkit-Teleop-Sample-Python 79e5cb8a56e3455515ce1b476e993c764ec58739
lerobot https://github.com/huggingface/lerobot e0d50211ef236143ae867228662b7dfaba554f02
tidybot_ros https://github.com/roahmlab/tidybot_ros e32cb459514abe556a9a9a954d9131d0bb50c210
PINS
