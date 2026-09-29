#!/usr/bin/env bash
# Run the official Unity-Technologies ros_tcp_endpoint plus the PickNik synthetic
# ROS-TCP client and the PickNik ROS observer, all inside one isolated
# `--network none` ROS 2 Humble container.
#
# HONESTY BOUNDARY: this exercises the TRANSPORT BACKEND only. PickNik's own C#
# `RosPublishers` is NOT executed. See picknik_rostcp_synthetic_client.py header.
#
# Usage: run_picknik_rostcp_backend.sh <run_output_dir> <ws_dir> <trial_id>
set -euo pipefail

OUTDIR="$1"
WSDIR="$2"
TRIAL="$3"
SCENARIO="${4:-occlusion}"
HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$OUTDIR"

sg docker -c "docker run --rm --network none \
  -e ROS_DOMAIN_ID=71 \
  -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  -v ${WSDIR}:/ws \
  -v ${HARNESS}:/harness:ro \
  -v ${OUTDIR}:/out \
  -w /ws ros-xr-humble:local bash -lc '
set -e
source /opt/ros/humble/setup.bash
source /ws/install/setup.bash
echo \"[env] ROS_DISTRO=\$ROS_DISTRO ROS_DOMAIN_ID=\$ROS_DOMAIN_ID RMW=\$RMW_IMPLEMENTATION\"
ros2 pkg prefix ros_tcp_endpoint
python3 -c \"import ros_tcp_endpoint,sys;print(\\\"ros_tcp_endpoint module:\\\",ros_tcp_endpoint.__file__)\"

ros2 run ros_tcp_endpoint default_server_endpoint --ros-args -p ROS_IP:=127.0.0.1 -p ROS_TCP_PORT:=10000 > /out/${TRIAL}_endpoint.log 2>&1 &
EP=\$!
sleep 5
python3 /harness/picknik_ros_observer.py --output /out/${TRIAL}_ros_observer.jsonl > /out/${TRIAL}_observer.log 2>&1 &
OB=\$!
sleep 3
ros2 topic list > /out/${TRIAL}_topic_list_before.txt 2>&1 || true

python3 /harness/picknik_rostcp_synthetic_client.py --host 127.0.0.1 --port 10000 \
    --scenario ${SCENARIO} --output /out/${TRIAL}_rostcp_client.jsonl > /out/${TRIAL}_client.log 2>&1
echo \"[client] exit=\$?\"

sleep 2
ros2 topic list > /out/${TRIAL}_topic_list_after.txt 2>&1 || true
ros2 node list > /out/${TRIAL}_node_list.txt 2>&1 || true
kill -TERM \$OB || true
wait \$OB || true
kill -TERM \$EP || true
echo DONE
'" 2>&1 | tee "${OUTDIR}/${TRIAL}_driver.log"
