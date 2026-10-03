#!/usr/bin/env bash
# Build once per campaign (docker-teleop-humble:local, ROS 2 Humble): pinned Docker_Teleop @64cbdde receiver +
# teleop_bridge_msgs (read-only mount /dt) + m12r_prov_msgs (snapshot /m12r); the B1 receiver is the patched COPY.
set -e; source /opt/ros/humble/setup.bash
rm -rf /build/src /build/install /build/b1; mkdir -p /build/src /build/b1
cp -r /dt/ros_backend1.1/src/receiver /dt/ros_backend1.1/src/teleop_bridge_msgs /m12r/src/m12r_prov_msgs /build/src/
cd /build && colcon build --packages-select teleop_bridge_msgs m12r_prov_msgs receiver > /build/colcon.log 2>&1; tail -3 /build/colcon.log
python3 /m12r/patch/apply_receiver_provenance.py /build/src/receiver/receiver/quest_controller_receiver.py /build/b1/quest_controller_receiver_b1.py
sha256sum /dt/ros_backend1.1/src/receiver/receiver/quest_controller_receiver.py /build/b1/quest_controller_receiver_b1.py > /build/BUILD_SHA256.txt
