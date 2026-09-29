#!/usr/bin/env python3
"""Quest2ROS2 publisher-disconnect/reconnect synthetic runtime experiment."""

from __future__ import annotations

import shutil
import shlex
import subprocess
import tempfile
import os
from pathlib import Path


CONTAINER_SCRIPT = r'''
set -e
source /opt/ros/humble/setup.bash
cd /ws
colcon build --packages-select quest2ros q2r2_bringup --cmake-args -DBUILD_TESTING=OFF >/tmp/build.log
source /ws/install/setup.bash
ros2 run tf2_ros static_transform_publisher 0.4 -0.1 0.3 0 0 0 bh_robot_base right_arm_link_ee >/tmp/tf.log 2>&1 &
tf_pid=$!
ros2 run q2r2_bringup right_arm_controller --ros-args -p filter_window_size:=3 >/tmp/controller.log 2>&1 &
ctrl_pid=$!
sleep 3

run_publisher() {
  phase="$1" x_value="$2" lower="$3" count="$4" python3 - <<'PY'
import os, time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from quest2ros.msg import OVR2ROSInputs
rclpy.init()
n=Node('reconnect_source_' + os.environ['phase'].lower())
p=n.create_publisher(PoseStamped,'/q2r_right_hand_pose',10)
i=n.create_publisher(OVR2ROSInputs,'/q2r_right_hand_inputs',10)
time.sleep(0.6)
for _ in range(int(os.environ['count'])):
    im=OVR2ROSInputs(); im.button_lower=os.environ['lower']=='true'; i.publish(im)
    m=PoseStamped(); m.header.stamp=n.get_clock().now().to_msg(); m.header.frame_id='world'
    m.pose.position.x=float(os.environ['x_value']); m.pose.position.y=-0.2; m.pose.position.z=0.5; m.pose.orientation.w=1.0
    p.publish(m); rclpy.spin_once(n,timeout_sec=0.03); time.sleep(0.04)
n.destroy_node(); rclpy.shutdown()
PY
}

run_publisher BASELINE 0.50 false 8
run_publisher MOVE_BEFORE_DISCONNECT 0.60 false 8
sleep 2.5
run_publisher RECONNECT_WITHOUT_RESET 0.70 false 8
run_publisher LATCH_DISABLE 0.70 true 3
sleep 1.0
run_publisher RECONNECT_WHILE_LATCHED 0.80 true 8
run_publisher RELEASE 0.80 false 3
run_publisher REENABLE 0.80 true 3
run_publisher AFTER_REENABLE 0.90 false 8
sleep 1
kill "$ctrl_pid" "$tf_pid" 2>/dev/null || true
cat /tmp/controller.log
'''


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    target = root / "semantic_validation/targets/quest2ros2"
    with tempfile.TemporaryDirectory(prefix="q2r2_reconnect_") as tmp:
        ws = Path(tmp) / "ws"
        (ws / "src").mkdir(parents=True)
        Path(tmp).chmod(0o755)
        ws.chmod(0o777)
        shutil.copytree(target, ws / "src/q2r2_bringup", ignore=shutil.ignore_patterns(".git", "__pycache__", "Files_for_msg_pkg"))
        shutil.copytree(target / "Files_for_msg_pkg", ws / "src/quest2ros")
        result = subprocess.run([
            "sg", "docker", "-c",
            "docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges "
            "--user " + str(os.getuid()) + ":" + str(os.getgid()) + " "
            "-e ROS_DOMAIN_ID=211 -e HOME=/tmp/home -v " + str(ws) + ":/ws "
            "ros-xr-humble:local bash -lc " + shlex.quote(CONTAINER_SCRIPT),
        ], text=True, capture_output=True, timeout=480)
        print(result.stdout)
        print(result.stderr)
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
