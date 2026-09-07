"""Robot-side dummy ROS 2 endpoint for the ROS-XR semantic testbed.

This node subscribes to incoming pose/odometry/tf topics and records every
received message to a JSONL log. It does not drive any actuator and performs
no semantic validation, tracking-state gating, or fail-close logic -- its
`accept_decision` field always reads ACCEPTED_NO_SEMANTIC_GATING. Treat its
output as infrastructure/reception evidence only, never as a semantic-boundary
finding.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage


def _stamp_to_dict(stamp):
    return {'sec': stamp.sec, 'nanosec': stamp.nanosec}


def _point_to_dict(p):
    return {'x': p.x, 'y': p.y, 'z': p.z}


def _quat_to_dict(q):
    return {'x': q.x, 'y': q.y, 'z': q.z, 'w': q.w}


class SemanticRobotSink(Node):

    def __init__(self):
        super().__init__('semantic_robot_sink')

        self.declare_parameter('pose_topic', '/robot_target_pose')
        self.declare_parameter(
            'odom_topics', ['/left_controller_odom', '/right_controller_odom']
        )
        self.declare_parameter('tf_topic', '/tf')
        self.declare_parameter(
            'log_dir', str(Path.home() / 'semantic_robot_endpoint_logs')
        )

        pose_topic = self.get_parameter('pose_topic').value
        odom_topics = self.get_parameter('odom_topics').value
        tf_topic = self.get_parameter('tf_topic').value
        log_dir = Path(self.get_parameter('log_dir').value)
        log_dir.mkdir(parents=True, exist_ok=True)

        run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        self._log_path = log_dir / f'semantic_robot_sink_{run_id}.jsonl'
        self._log_file = open(self._log_path, 'a', buffering=1)
        self._counts = {}

        self.get_logger().info(f'logging to {self._log_path}')
        self.get_logger().info(
            'NOTE: no actuator, no semantic validation, no fail-close gating. '
            'accept_decision is always ACCEPTED_NO_SEMANTIC_GATING -- do not '
            'cite reception here as a safety or semantic-boundary finding.'
        )

        self.create_subscription(
            PoseStamped, pose_topic,
            self._make_cb(pose_topic, 'geometry_msgs/msg/PoseStamped'), 10,
        )
        for topic in odom_topics:
            self.create_subscription(
                Odometry, topic,
                self._make_cb(topic, 'nav_msgs/msg/Odometry'), 10,
            )
        self.create_subscription(
            TFMessage, tf_topic,
            self._make_cb(tf_topic, 'tf2_msgs/msg/TFMessage'), 50,
        )

    def _make_cb(self, topic, msg_type):
        def cb(msg):
            self._handle(topic, msg_type, msg)
        return cb

    def _handle(self, topic, msg_type, msg):
        self._counts[topic] = self._counts.get(topic, 0) + 1

        record = {
            'receive_wall_time': datetime.now(timezone.utc).isoformat(),
            'receive_monotonic_time': time.monotonic(),
            'topic': topic,
            'msg_type': msg_type,
            'receive_count_for_topic': self._counts[topic],
            'header_stamp': None,
            'frame_id': None,
            'child_frame_id': None,
            'position': None,
            'orientation': None,
            'transforms': None,
            # Standard PoseStamped/Odometry/TFMessage carry no
            # sequence/correlation id; left null unless a future producer's
            # message type adds one.
            'sequence_or_correlation_id': None,
            'semantic_metadata': None,
            'accept_decision': 'ACCEPTED_NO_SEMANTIC_GATING',
        }

        if msg_type == 'geometry_msgs/msg/PoseStamped':
            record['header_stamp'] = _stamp_to_dict(msg.header.stamp)
            record['frame_id'] = msg.header.frame_id
            record['position'] = _point_to_dict(msg.pose.position)
            record['orientation'] = _quat_to_dict(msg.pose.orientation)
        elif msg_type == 'nav_msgs/msg/Odometry':
            record['header_stamp'] = _stamp_to_dict(msg.header.stamp)
            record['frame_id'] = msg.header.frame_id
            record['child_frame_id'] = msg.child_frame_id
            record['position'] = _point_to_dict(msg.pose.pose.position)
            record['orientation'] = _quat_to_dict(msg.pose.pose.orientation)
        elif msg_type == 'tf2_msgs/msg/TFMessage':
            record['transforms'] = [
                {
                    'header_stamp': _stamp_to_dict(t.header.stamp),
                    'frame_id': t.header.frame_id,
                    'child_frame_id': t.child_frame_id,
                    'position': _point_to_dict(t.transform.translation),
                    'orientation': _quat_to_dict(t.transform.rotation),
                }
                for t in msg.transforms
            ]

        self._log_file.write(json.dumps(record) + '\n')

    def destroy_node(self):
        self._log_file.close()
        super().destroy_node()


def main():
    rclpy.init()
    node = SemanticRobotSink()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        # SIGINT/SIGTERM during a timed observation run is the normal exit path.
        pass
    finally:
        node.destroy_node()
        # rclpy may already have shut the context down when spin() was
        # interrupted by a signal; shutting down twice raises RCLError.
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
