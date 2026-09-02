#!/usr/bin/env python3

import argparse
import json
import os
from pathlib import Path
import sys
import time


def full_node_name(namespace, name):
    namespace = namespace or "/"
    if namespace == "/":
        return f"/{name}"
    return f"{namespace.rstrip('/')}/{name}"


def graph_state(node, topic_name="/cmd_vel"):
    enclave_by_node = {}
    nodes = []
    for name, namespace, enclave in node.get_node_names_and_namespaces_with_enclaves():
        enclave_by_node[(name, namespace)] = enclave
        nodes.append(f"{full_node_name(namespace, name)}@{enclave or '-'}")

    publishers = []
    for info in node.get_publishers_info_by_topic(topic_name):
        try:
            gid = bytes(info.endpoint_gid).hex()
        except (TypeError, ValueError):
            gid = "".join(f"{int(value):02x}" for value in info.endpoint_gid)
        enclave = enclave_by_node.get((info.node_name, info.node_namespace), "unknown")
        publishers.append(
            f"{full_node_name(info.node_namespace, info.node_name)}@{enclave}#{gid}"
        )

    return sorted(publishers), sorted(nodes)


def append_line(path, line):
    with path.open("a", encoding="utf-8") as output:
        output.write(line + "\n")


def requested_enclave():
    if "--enclave" in sys.argv:
        index = sys.argv.index("--enclave")
        if index + 1 < len(sys.argv):
            return sys.argv[index + 1]
    return os.environ.get("ROS_SECURITY_ENCLAVE_OVERRIDE", "-")


def run_robot(args):
    import rclpy
    from geometry_msgs.msg import Twist
    from rclpy.node import Node

    class DummyRobot(Node):
        def __init__(self):
            super().__init__(
                args.node_name,
                enable_rosout=False,
                start_parameter_services=False,
            )
            self.result_file = Path(args.result_file)
            self.last_graph_signature = None
            self.subscription = self.create_subscription(
                Twist,
                args.topic,
                self.on_command,
                10,
            )
            self.timer = self.create_timer(0.25, self.record_graph)

        def record_graph(self):
            publishers, nodes = graph_state(self, self.subscription.topic_name)
            line = (
                f"GRAPH publisher_count={len(publishers)} "
                f"publishers={','.join(publishers) if publishers else '-'} "
                f"nodes={','.join(nodes) if nodes else '-'}"
            )
            append_line(self.result_file, line)
            signature = (tuple(publishers), tuple(nodes))
            if signature != self.last_graph_signature:
                print(f"ROBOT_{line}", flush=True)
                self.last_graph_signature = signature

        def on_command(self, message):
            publishers, _ = graph_state(self, self.subscription.topic_name)
            line = (
                f"RECEIVED linear_x={message.linear.x:.3f} "
                f"angular_z={message.angular.z:.3f} "
                f"publisher_count={len(publishers)} "
                f"publishers={','.join(publishers) if publishers else '-'}"
            )
            append_line(self.result_file, line)
            print(f"ROBOT_{line}", flush=True)

    rclpy.init(args=sys.argv)
    node = DummyRobot()
    print(
        f"ROBOT_READY node=/{args.node_name} topic={args.topic} "
        f"enclave={requested_enclave()}",
        flush=True,
    )
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0


def run_publisher(args):
    import rclpy
    from geometry_msgs.msg import Twist
    from rclpy.node import Node

    rclpy.init(args=sys.argv)
    node = Node(
        args.node_name,
        enable_rosout=False,
        start_parameter_services=False,
    )
    enclave = requested_enclave()
    print(
        f"DIRECT_NODE_READY node=/{args.node_name} topic={args.topic} enclave={enclave}",
        flush=True,
    )

    try:
        if args.gate_file:
            gate = Path(args.gate_file)
            deadline = time.monotonic() + args.gate_timeout
            print(f"DIRECT_WAIT_GATE path={gate}", flush=True)
            while not gate.exists():
                if time.monotonic() >= deadline:
                    print("DIRECT_GATE_TIMEOUT", flush=True)
                    return 12
                rclpy.spin_once(node, timeout_sec=0.05)
            print("DIRECT_GATE_OPEN", flush=True)

        try:
            publisher = node.create_publisher(Twist, args.topic, 10)
        except Exception as error:
            print(f"DIRECT_CREATE_DENIED error={error!r}", flush=True)
            return 13

        discovery_deadline = time.monotonic() + args.discovery_wait
        while publisher.get_subscription_count() == 0 and time.monotonic() < discovery_deadline:
            rclpy.spin_once(node, timeout_sec=0.05)

        message = Twist()
        message.linear.x = args.linear_x
        message.angular.z = args.angular_z
        for sequence in range(1, args.count + 1):
            publisher.publish(message)
            print(
                f"DIRECT_SENT sequence={sequence} linear_x={args.linear_x:.3f} "
                f"angular_z={args.angular_z:.3f} matched={publisher.get_subscription_count()}",
                flush=True,
            )
            rclpy.spin_once(node, timeout_sec=0.05)
            time.sleep(args.interval)
        time.sleep(0.4)
        return 0
    finally:
        node.destroy_node()
        rclpy.shutdown()


def run_external_client(args):
    import websocket

    websocket.enableTrace(False)
    connection = None
    advertised = False
    deadline = time.monotonic() + args.connect_timeout
    while connection is None:
        try:
            connection = websocket.create_connection(args.url, timeout=2)
        except Exception as error:
            if time.monotonic() >= deadline:
                print(f"EXTERNAL_CONNECT_FAILED client={args.client_id} error={error!r}", flush=True)
                return 20
            time.sleep(0.2)

    advertise = {
        "op": "advertise",
        "id": f"{args.client_id}:advertise",
        "topic": "/cmd_vel",
        "type": "geometry_msgs/msg/Twist",
        "qos": {
            "history": "keep_last",
            "depth": 10,
            "reliability": "reliable",
            "durability": "volatile",
        },
    }
    message = {
        "linear": {"x": args.linear_x, "y": 0.0, "z": 0.0},
        "angular": {"x": 0.0, "y": 0.0, "z": args.angular_z},
    }

    try:
        connection.send(json.dumps(advertise))
        advertised = True
        print(f"EXTERNAL_ADVERTISED client={args.client_id}", flush=True)
        time.sleep(args.discovery_wait)
        for sequence in range(1, args.count + 1):
            connection.send(
                json.dumps(
                    {
                        "op": "publish",
                        "id": f"{args.client_id}:publish:{sequence}",
                        "topic": "/cmd_vel",
                        "msg": message,
                    }
                )
            )
            time.sleep(args.interval)
        print(
            f"EXTERNAL_SENT client={args.client_id} linear_x={args.linear_x:.3f} "
            f"count={args.count}",
            flush=True,
        )
        time.sleep(args.hold_seconds)
        return 0
    except Exception as error:
        print(f"EXTERNAL_FAILED client={args.client_id} error={error!r}", flush=True)
        return 21
    finally:
        if connection is not None:
            if advertised:
                try:
                    connection.send(
                        json.dumps(
                            {
                                "op": "unadvertise",
                                "id": f"{args.client_id}:advertise",
                                "topic": "/cmd_vel",
                            }
                        )
                    )
                except Exception:
                    pass
            connection.close()
        print(f"EXTERNAL_CLOSED client={args.client_id}", flush=True)


def build_parser():
    parser = argparse.ArgumentParser(description="Minimal ROS origin identity test")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    robot = subparsers.add_parser("robot")
    robot.add_argument("--result-file", required=True)
    robot.add_argument("--topic", default="/cmd_vel")
    robot.add_argument("--node-name", default="dummy_robot")

    publisher = subparsers.add_parser("publish")
    publisher.add_argument("--topic", default="/cmd_vel")
    publisher.add_argument("--node-name", default="direct_publisher")
    publisher.add_argument("--linear-x", type=float, required=True)
    publisher.add_argument("--angular-z", type=float, default=0.0)
    publisher.add_argument("--count", type=int, default=4)
    publisher.add_argument("--interval", type=float, default=0.2)
    publisher.add_argument("--discovery-wait", type=float, default=2.0)
    publisher.add_argument("--gate-file")
    publisher.add_argument("--gate-timeout", type=float, default=20.0)

    external = subparsers.add_parser("external-client")
    external.add_argument("--client-id", required=True)
    external.add_argument("--linear-x", type=float, required=True)
    external.add_argument("--angular-z", type=float, default=0.0)
    external.add_argument("--url", default="ws://127.0.0.1:9090")
    external.add_argument("--count", type=int, default=4)
    external.add_argument("--interval", type=float, default=0.2)
    external.add_argument("--discovery-wait", type=float, default=1.0)
    external.add_argument("--hold-seconds", type=float, default=8.0)
    external.add_argument("--connect-timeout", type=float, default=10.0)
    return parser


def main():
    from rclpy.utilities import remove_ros_args

    application_args = remove_ros_args(args=sys.argv)[1:]
    args = build_parser().parse_args(application_args)
    if args.mode == "robot":
        return run_robot(args)
    if args.mode == "publish":
        return run_publisher(args)
    if args.mode == "external-client":
        return run_external_client(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
