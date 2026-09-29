#!/usr/bin/env python3
"""Local-only runtime probe for HORUS authorization continuity.

This is deliberately a protocol client, not a modified HORUS component.  It
connects two independent HorusLink sessions to the unmodified bridge and uses
ordinary ROS 2 observers/a dummy Nav2 action server to record what crosses the
bridge boundary.
"""

from __future__ import annotations

import json
import socket
import struct
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

import rclpy
from geometry_msgs.msg import PoseStamped, Twist
from horus_interfaces.srv import RegisterRobot
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionServer
from rclpy.action.server import CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.serialization import serialize_message
from std_msgs.msg import String


REALTIME_PORT = 11000
BULK_PORT = 11001
ROBOT = "robot1"
CMD_TOPIC = f"/{ROBOT}/cmd_vel"
GOAL_TOPIC = f"/{ROBOT}/goal_pose"
LEASE_TOPIC = "/horus/multi_operator/control_lease_request"
CATALOG_TOPIC = "/horus/multi_operator/control_topic_catalog"
STATE_TOPIC = "/horus/multi_operator/control_lease_state"

MSG_DATA = 1
MSG_CONTROL = 2
FLAG_RAW_OPAQUE = 1
LANE_REALTIME = 1
LANE_BULK = 2
DELIVERY_RELIABLE_FIFO = 1

TLV_KIND = 1
TLV_VERSION = 2
TLV_ROLE = 3
TLV_CHANNEL = 4
TLV_TOPIC = 5
TLV_TYPE = 6
TLV_LANE = 7
TLV_DELIVERY = 8
TLV_MAX_PAYLOAD = 9
TLV_KEEPALIVE = 10
TLV_STATUS = 11
TLV_ERROR = 12
TLV_SESSION = 13

KIND_HELLO = 1
KIND_PUBLISHER = 5
KIND_ACK = 3


def wait_for(predicate: Callable[[], bool], timeout: float, description: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.03)
    raise RuntimeError(f"timeout waiting for {description}")


def tlv(tlv_type: int, value: bytes) -> bytes:
    return struct.pack("<HH", tlv_type, len(value)) + value


def encode_tlvs(records: list[tuple[int, bytes]]) -> bytes:
    return b"".join(tlv(kind, value) for kind, value in records)


def decode_tlvs(payload: bytes) -> dict[int, bytes]:
    result: dict[int, bytes] = {}
    offset = 0
    while offset < len(payload):
        if offset + 4 > len(payload):
            raise RuntimeError("truncated TLV header")
        kind, length = struct.unpack_from("<HH", payload, offset)
        offset += 4
        if offset + length > len(payload):
            raise RuntimeError("truncated TLV value")
        result[kind] = payload[offset : offset + length]
        offset += length
    return result


def recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        data = sock.recv(remaining)
        if not data:
            raise ConnectionError("HorusLink socket closed")
        chunks.append(data)
        remaining -= len(data)
    return b"".join(chunks)


@dataclass
class Frame:
    channel: int
    msg_type: int
    flags: int
    sequence: int
    correlation: int
    payload: bytes


class HorusLinkClient:
    def __init__(self, label: str, session_id: int) -> None:
        self.label = label
        self.session_id = session_id
        self.realtime: socket.socket | None = None
        self.bulk: socket.socket | None = None
        self.sequence = 1
        self.channels: dict[str, int] = {}

    def _frame(self, channel: int, msg_type: int, flags: int, payload: bytes) -> bytes:
        header = struct.pack(
            "<HBBIII",
            channel,
            msg_type,
            flags,
            self.sequence,
            0,
            len(payload),
        )
        self.sequence += 1
        return header + payload

    def _hello(self, lane: int) -> bytes:
        payload = encode_tlvs(
            [
                (TLV_KIND, bytes([KIND_HELLO])),
                (TLV_VERSION, struct.pack("<H", 1)),
                (TLV_ROLE, bytes([1])),  # UnityClient
                (TLV_MAX_PAYLOAD, struct.pack("<I", 8 * 1024 * 1024)),
                (TLV_KEEPALIVE, struct.pack("<I", 0)),
                (TLV_LANE, bytes([lane])),
                (TLV_SESSION, struct.pack("<Q", self.session_id)),
            ]
        )
        return self._frame(0, MSG_CONTROL, 0, payload)

    def connect(self) -> None:
        self.realtime = socket.create_connection(("127.0.0.1", REALTIME_PORT), timeout=3)
        self.realtime.settimeout(3)
        self.realtime.sendall(self._hello(LANE_REALTIME))
        self.bulk = socket.create_connection(("127.0.0.1", BULK_PORT), timeout=3)
        self.bulk.settimeout(3)
        self.bulk.sendall(self._hello(LANE_BULK))
        bridge_hello = self.recv_frame()
        records = decode_tlvs(bridge_hello.payload)
        if bridge_hello.msg_type != MSG_CONTROL or records.get(TLV_KIND) != bytes([KIND_HELLO]):
            raise RuntimeError(f"{self.label}: bridge hello not received")

    def recv_frame(self) -> Frame:
        if self.realtime is None:
            raise RuntimeError("client is not connected")
        header = recv_exact(self.realtime, 16)
        channel, msg_type, flags, seq, corr, length = struct.unpack("<HBBIII", header)
        return Frame(channel, msg_type, flags, seq, corr, recv_exact(self.realtime, length))

    def register_publisher(self, channel: int, topic: str, type_name: str) -> None:
        if self.realtime is None:
            raise RuntimeError("client is not connected")
        payload = encode_tlvs(
            [
                (TLV_KIND, bytes([KIND_PUBLISHER])),
                (TLV_VERSION, struct.pack("<H", 1)),
                (TLV_CHANNEL, struct.pack("<H", channel)),
                (TLV_TOPIC, topic.encode()),
                (TLV_TYPE, type_name.encode()),
                (TLV_LANE, bytes([LANE_REALTIME])),
                (TLV_DELIVERY, bytes([DELIVERY_RELIABLE_FIFO])),
            ]
        )
        self.realtime.sendall(self._frame(0, MSG_CONTROL, 0, payload))
        while True:
            response = self.recv_frame()
            if response.msg_type != MSG_CONTROL:
                continue
            records = decode_tlvs(response.payload)
            if records.get(TLV_KIND) != bytes([KIND_ACK]):
                continue
            ack_channel = struct.unpack("<H", records[TLV_CHANNEL])[0]
            if ack_channel != channel:
                continue
            status = records.get(TLV_STATUS, b"\x00")[0]
            error = records.get(TLV_ERROR, b"").decode(errors="replace")
            if status != 1:
                raise RuntimeError(f"{self.label}: publisher registration rejected: {error}")
            break
        self.channels[topic] = channel

    def publish_serialized(self, topic: str, serialized: bytes, include_cdr_header: bool) -> None:
        if self.realtime is None:
            raise RuntimeError("client is not connected")
        body = serialized if include_cdr_header else serialized[4:]
        self.realtime.sendall(
            self._frame(self.channels[topic], MSG_DATA, FLAG_RAW_OPAQUE, body)
        )

    def publish_json_string(self, topic: str, value: dict[str, Any]) -> None:
        message = String()
        message.data = json.dumps(value, separators=(",", ":"), sort_keys=True)
        self.publish_serialized(topic, bytes(serialize_message(message)), True)

    def publish_twist(self, x_value: float) -> None:
        message = Twist()
        message.linear.x = x_value
        self.publish_serialized(CMD_TOPIC, bytes(serialize_message(message)), False)

    def publish_goal(self, x_value: float) -> None:
        message = PoseStamped()
        message.header.frame_id = "map"
        message.header.stamp.sec = int(time.time())
        message.pose.position.x = x_value
        message.pose.orientation.w = 1.0
        self.publish_serialized(GOAL_TOPIC, bytes(serialize_message(message)), False)

    def acquire(
        self,
        request_id: str,
        app_id: str,
        role: str,
        session_id: str,
        *,
        active: bool = True,
    ) -> None:
        self.publish_json_string(
            LEASE_TOPIC,
            {
                "request_id": request_id,
                "robot_name": ROBOT,
                "app_id": app_id,
                "role": role,
                "session_id": session_id,
                "action": "acquire",
                "panel_open": active,
                "teleop_active": active,
                "task_active": active,
                "task_kind": "navigation" if active else "none",
            },
        )

    def release(self, request_id: str) -> None:
        self.publish_json_string(
            LEASE_TOPIC,
            {
                "request_id": request_id,
                "robot_name": ROBOT,
                "action": "release",
            },
        )

    def catalog(self, operation: str, role: str = "host") -> None:
        payload: dict[str, Any] = {
            "role": role,
            "op": operation,
            "session_id": "runtime-probe",
        }
        if operation != "clear":
            payload["robots"] = [
                {
                    "robot_name": ROBOT,
                    "protected_topics": [CMD_TOPIC, GOAL_TOPIC],
                }
            ]
        self.publish_json_string(CATALOG_TOPIC, payload)

    def close(self) -> None:
        for sock in (self.realtime, self.bulk):
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                sock.close()
        self.realtime = None
        self.bulk = None


class ProbeNode(Node):
    def __init__(self) -> None:
        super().__init__("horus_authorization_runtime_probe")
        self.lock = threading.Lock()
        self.cmd_values: list[float] = []
        self.lease_states: list[dict[str, Any]] = []
        self.goal_started = 0
        self.goal_cancel_requested = 0
        self.active_goals = 0
        self.stop_actions = threading.Event()
        self.callback_group = ReentrantCallbackGroup()
        self.create_subscription(Twist, CMD_TOPIC, self._on_cmd, 20)
        state_qos = QoSProfile(depth=20)
        state_qos.reliability = ReliabilityPolicy.RELIABLE
        state_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.create_subscription(String, STATE_TOPIC, self._on_state, state_qos)
        self.action_server = ActionServer(
            self,
            NavigateToPose,
            f"/{ROBOT}/navigate_to_pose",
            execute_callback=self._execute_goal,
            goal_callback=self._accept_goal,
            cancel_callback=self._accept_cancel,
            callback_group=self.callback_group,
        )

    def _on_cmd(self, message: Twist) -> None:
        with self.lock:
            self.cmd_values.append(round(float(message.linear.x), 3))

    def _on_state(self, message: String) -> None:
        try:
            state = json.loads(message.data)
        except json.JSONDecodeError:
            return
        with self.lock:
            self.lease_states.append(state)

    def _accept_goal(self, _request: NavigateToPose.Goal) -> GoalResponse:
        return GoalResponse.ACCEPT

    def _accept_cancel(self, _goal_handle: Any) -> CancelResponse:
        with self.lock:
            self.goal_cancel_requested += 1
        return CancelResponse.ACCEPT

    def _execute_goal(self, goal_handle: Any) -> NavigateToPose.Result:
        with self.lock:
            self.goal_started += 1
            self.active_goals += 1
        while not self.stop_actions.is_set():
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                with self.lock:
                    self.active_goals -= 1
                return NavigateToPose.Result()
            time.sleep(0.05)
        goal_handle.succeed()
        with self.lock:
            self.active_goals -= 1
        return NavigateToPose.Result()

    def command_count(self, value: float) -> int:
        rounded = round(value, 3)
        with self.lock:
            return self.cmd_values.count(rounded)

    def state_matches(self, predicate: Callable[[dict[str, Any]], bool]) -> bool:
        with self.lock:
            return any(predicate(state) for state in self.lease_states)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "cmd_values": list(self.cmd_values),
                "lease_states": list(self.lease_states),
                "goal_started": self.goal_started,
                "goal_cancel_requested": self.goal_cancel_requested,
                "active_goals": self.active_goals,
            }


def lease_event(node: ProbeNode, event: str, request_id: str | None = None) -> bool:
    return node.state_matches(
        lambda state: state.get("event") == event
        and (request_id is None or state.get("request_id") == request_id)
    )


def lease_holder(node: ProbeNode, app_id: str, role: str | None = None, session: str | None = None) -> bool:
    def matches(state: dict[str, Any]) -> bool:
        for lease in state.get("leases", []):
            if lease.get("holder_app_id") != app_id:
                continue
            if role is not None and lease.get("holder_role") != role:
                continue
            if session is not None and lease.get("session_id") != session:
                continue
            return True
        return False

    return node.state_matches(matches)


def register_robot(node: ProbeNode) -> str:
    client = node.create_client(RegisterRobot, "/horus/register_robot", callback_group=node.callback_group)
    if not client.wait_for_service(timeout_sec=8.0):
        raise RuntimeError("HORUS backend register_robot service unavailable")
    request = RegisterRobot.Request()
    request.robot_config.name = ROBOT
    request.robot_config.robot_type = "wheeled"
    request.robot_config.control_topics = [CMD_TOPIC, GOAL_TOPIC]
    request.robot_config.metadata_keys = [
        "horus.backend.nav2_action_topic",
        "horus.backend.goal_topic",
        "horus.backend.cancel_topic",
        "horus.backend.status_topic",
    ]
    request.robot_config.metadata_values = [
        f"/{ROBOT}/navigate_to_pose",
        GOAL_TOPIC,
        f"/{ROBOT}/goal_cancel",
        f"/{ROBOT}/goal_status",
    ]
    future = client.call_async(request)
    wait_for(future.done, 8.0, "register_robot response")
    response = future.result()
    if response is None or not response.success:
        detail = "no response" if response is None else response.error_message
        raise RuntimeError(f"robot registration failed: {detail}")
    return response.robot_id


def main() -> int:
    rclpy.init()
    node = ProbeNode()
    executor = MultiThreadedExecutor(num_threads=8)
    executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    client_a = HorusLinkClient("A", 0xA001)
    client_b = HorusLinkClient("B", 0xB002)
    results: dict[str, Any] = {}
    try:
        robot_id = register_robot(node)
        results["robot_registration"] = {"success": True, "robot_id": robot_id}

        client_a.connect()
        client_b.connect()
        publishers = [
            (1, CATALOG_TOPIC, "std_msgs/msg/String"),
            (2, LEASE_TOPIC, "std_msgs/msg/String"),
            (3, CMD_TOPIC, "geometry_msgs/msg/Twist"),
            (4, GOAL_TOPIC, "geometry_msgs/msg/PoseStamped"),
        ]
        for client in (client_a, client_b):
            for channel, topic, type_name in publishers:
                client.register_publisher(channel, topic, type_name)
        time.sleep(1.0)

        publisher_info = node.get_publishers_info_by_topic(CMD_TOPIC)
        results["bridge_publisher_identity"] = [
            {
                "node_name": info.node_name,
                "node_namespace": info.node_namespace,
                "endpoint_gid": bytes(info.endpoint_gid).hex(),
            }
            for info in publisher_info
        ]

        # Protected catalog with no lease is deliberately tested before any acquire.
        client_a.catalog("snapshot")
        time.sleep(0.25)
        before = node.command_count(0.31)
        client_b.publish_twist(0.31)
        wait_for(lambda: node.command_count(0.31) > before, 2.0, "no-lease command delivery")
        results["no_lease_on_protected_topic"] = "ALLOW"

        # Normal two-client lease arbitration.
        client_a.acquire("normal-a", "app-A", "operator", "session-A")
        wait_for(lambda: lease_event(node, "lease_granted", "normal-a"), 2.0, "A lease grant")
        a_before = node.command_count(0.11)
        client_a.publish_twist(0.11)
        wait_for(lambda: node.command_count(0.11) > a_before, 2.0, "A command")
        b_before = node.command_count(0.22)
        client_b.publish_twist(0.22)
        time.sleep(0.6)
        b_blocked = node.command_count(0.22) == b_before
        client_b.acquire("normal-b-denied", "app-B", "operator", "session-B")
        wait_for(
            lambda: lease_event(node, "lease_denied", "normal-b-denied"),
            2.0,
            "B lease denial",
        )
        client_a.release("normal-a-release")
        wait_for(lambda: lease_event(node, "lease_released", "normal-a-release"), 2.0, "A release")
        client_b.acquire("normal-b", "app-B", "operator", "session-B")
        wait_for(lambda: lease_event(node, "lease_granted", "normal-b"), 2.0, "B lease grant")
        client_b.publish_twist(0.22)
        wait_for(lambda: node.command_count(0.22) > b_before, 2.0, "B command after grant")
        client_b.release("normal-b-release")
        wait_for(lambda: lease_event(node, "lease_released", "normal-b-release"), 2.0, "B release")
        results["normal_lease"] = {
            "A_command": "ALLOW",
            "B_during_A_lease": "BLOCK" if b_blocked else "ALLOW",
            "B_after_A_release": "ALLOW",
        }

        # Client-asserted metadata is accepted and reflected without authentication.
        client_a.acquire("identity-a", "self-asserted-app", "self-asserted-admin", "fake-session")
        wait_for(
            lambda: lease_holder(node, "self-asserted-app", "self-asserted-admin", "fake-session"),
            2.0,
            "self-asserted lease metadata",
        )
        results["identity_metadata"] = {
            "accepted_app_id": "self-asserted-app",
            "accepted_role": "self-asserted-admin",
            "accepted_session_id": "fake-session",
            "authorization_key_observed": "HorusLink connection ownership",
        }
        client_a.release("identity-release")
        wait_for(lambda: lease_event(node, "lease_released", "identity-release"), 2.0, "identity release")

        # A second client can self-assert host and clear the protection catalog.
        client_a.catalog("snapshot")
        client_a.acquire("catalog-a", "catalog-holder-A", "operator", "catalog-session")
        wait_for(lambda: lease_event(node, "lease_granted", "catalog-a"), 2.0, "catalog test lease")
        clear_before = node.command_count(0.44)
        client_b.publish_twist(0.44)
        time.sleep(0.6)
        pre_clear_blocked = node.command_count(0.44) == clear_before
        client_b.catalog("clear", role="host")
        time.sleep(0.25)
        client_b.publish_twist(0.44)
        wait_for(lambda: node.command_count(0.44) > clear_before, 2.0, "command after catalog clear")
        results["catalog_control_plane"] = {
            "B_before_self_asserted_host_clear": "BLOCK" if pre_clear_blocked else "ALLOW",
            "B_after_self_asserted_host_clear": "ALLOW",
        }
        client_a.catalog("snapshot")
        client_a.release("catalog-release")
        wait_for(lambda: lease_event(node, "lease_released", "catalog-release"), 2.0, "catalog release")

        # Explicit release does not propagate to an already accepted Nav2 goal.
        initial_goals = node.snapshot()["goal_started"]
        initial_cancels = node.snapshot()["goal_cancel_requested"]
        client_a.acquire("goal-release-a", "goal-A", "operator", "goal-session")
        wait_for(lambda: lease_event(node, "lease_granted", "goal-release-a"), 2.0, "goal lease")
        client_a.publish_goal(1.0)
        wait_for(lambda: node.snapshot()["goal_started"] > initial_goals, 5.0, "release test goal")
        client_a.release("goal-release")
        wait_for(lambda: lease_event(node, "lease_released", "goal-release"), 2.0, "goal lease release")
        time.sleep(1.0)
        release_cancelled = node.snapshot()["goal_cancel_requested"] > initial_cancels

        # TTL expiry likewise releases only the bridge lease.
        before_expiry_goals = node.snapshot()["goal_started"]
        before_expiry_cancels = node.snapshot()["goal_cancel_requested"]
        client_a.acquire("goal-expiry-a", "goal-expiry-A", "operator", "expiry-session")
        wait_for(lambda: lease_event(node, "lease_granted", "goal-expiry-a"), 2.0, "expiry lease")
        client_a.publish_goal(2.0)
        wait_for(lambda: node.snapshot()["goal_started"] > before_expiry_goals, 5.0, "expiry test goal")
        wait_for(lambda: lease_event(node, "lease_expired"), 4.0, "lease expiry")
        time.sleep(0.7)
        expiry_cancelled = node.snapshot()["goal_cancel_requested"] > before_expiry_cancels

        # Disconnect releases lease state but does not cancel the accepted goal.
        before_disconnect_goals = node.snapshot()["goal_started"]
        before_disconnect_cancels = node.snapshot()["goal_cancel_requested"]
        client_a.acquire("goal-disconnect-a", "goal-disconnect-A", "operator", "disconnect-session")
        wait_for(lambda: lease_event(node, "lease_granted", "goal-disconnect-a"), 2.0, "disconnect lease")
        client_a.publish_goal(3.0)
        wait_for(
            lambda: node.snapshot()["goal_started"] > before_disconnect_goals,
            5.0,
            "disconnect test goal",
        )
        client_a.close()
        wait_for(lambda: lease_event(node, "client_disconnected_release"), 3.0, "disconnect release")
        time.sleep(1.0)
        disconnect_cancelled = node.snapshot()["goal_cancel_requested"] > before_disconnect_cancels
        client_b.acquire("after-disconnect-b", "goal-B", "operator", "after-disconnect")
        wait_for(
            lambda: lease_event(node, "lease_granted", "after-disconnect-b"),
            2.0,
            "B lease after disconnect",
        )
        results["ongoing_action_lifecycle"] = {
            "explicit_release": "CANCELLED" if release_cancelled else "CONTINUED",
            "lease_expiry": "CANCELLED" if expiry_cancelled else "CONTINUED",
            "client_disconnect": "CANCELLED" if disconnect_cancelled else "CONTINUED",
            "B_acquire_after_disconnect": "ALLOW",
            "accepted_goals": node.snapshot()["goal_started"],
            "cancel_requests_seen_by_action_server": node.snapshot()["goal_cancel_requested"],
        }

        snapshot = node.snapshot()
        results["observations"] = {
            "cmd_values": snapshot["cmd_values"],
            "lease_event_sequence": [state.get("event") for state in snapshot["lease_states"]],
            "active_goals_at_observation_end": snapshot["active_goals"],
        }

        required = [
            results["no_lease_on_protected_topic"] == "ALLOW",
            results["normal_lease"]["A_command"] == "ALLOW",
            results["normal_lease"]["B_during_A_lease"] == "BLOCK",
            results["normal_lease"]["B_after_A_release"] == "ALLOW",
            results["catalog_control_plane"]["B_before_self_asserted_host_clear"] == "BLOCK",
            results["catalog_control_plane"]["B_after_self_asserted_host_clear"] == "ALLOW",
            all(value == "CONTINUED" for key, value in results["ongoing_action_lifecycle"].items() if key in {"explicit_release", "lease_expiry", "client_disconnect"}),
        ]
        results["probe_pass"] = all(required)
        print(json.dumps(results, indent=2, sort_keys=True))
        return 0 if results["probe_pass"] else 2
    except Exception as exc:
        results["probe_pass"] = False
        results["error"] = f"{type(exc).__name__}: {exc}"
        results["partial_observations"] = node.snapshot()
        print(json.dumps(results, indent=2, sort_keys=True))
        return 1
    finally:
        client_a.close()
        client_b.close()
        node.stop_actions.set()
        time.sleep(0.2)
        executor.shutdown(timeout_sec=2.0)
        node.action_server.destroy()
        node.destroy_node()
        rclpy.shutdown()
        spin_thread.join(timeout=2.0)


if __name__ == "__main__":
    sys.exit(main())
