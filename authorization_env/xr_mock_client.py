#!/usr/bin/env python3
"""OpenXR-style authority lifecycle probe for the real HORUS -> Nav2 path.

This executable intentionally mocks only the XR application/runtime lifecycle.
It uses the actual HorusLink protocol client, the fixed HORUS bridge and backend,
the HORUS Nav2ActionAdapter, an actual Nav2 NavigateToPose server, and a simulated
robot which exposes ``cmd_vel`` and ``odom``.  It never creates an action server.

The mock states are test events based on OpenXR lifecycle semantics; they are not
events emitted by an OpenXR runtime and must not be reported as Quest evidence.
Likewise, odometry is simulator output rather than physical-robot ground truth.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import statistics
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable

import rclpy
from action_msgs.msg import GoalStatus, GoalStatusArray
from action_msgs.srv import CancelGoal
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, Twist
from horus_interfaces.srv import RegisterRobot, UnregisterRobot
from lifecycle_msgs.msg import State
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import NavigateToPose
from nav2_msgs.srv import ClearEntireCostmap
from nav_msgs.msg import OccupancyGrid, Odometry
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import (
    DurabilityPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_action_status_default,
)
from rclpy.serialization import serialize_message
from rclpy.time import Time
from rclpy.utilities import remove_ros_args
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener

from horus_runtime_probe import (
    CATALOG_TOPIC,
    GOAL_TOPIC,
    LEASE_TOPIC,
    ROBOT,
    STATE_TOPIC,
    HorusLinkClient,
)


FIXED_HORUS_REVISION = "eca75cbf559f09ff793d8993338b2f1ffed1adfd"
DEFAULT_NAV2_ACTION = "/navigate_to_pose"
DEFAULT_CMD_TOPIC = "/cmd_vel"
DEFAULT_ODOM_TOPIC = "/odom"
DEFAULT_INITIALPOSE_TOPIC = "/initialpose"
DEFAULT_MAP_TOPIC = "/map"

TERMINAL_STATUSES = {
    GoalStatus.STATUS_SUCCEEDED,
    GoalStatus.STATUS_CANCELED,
    GoalStatus.STATUS_ABORTED,
}
ACTIVE_STATUSES = {
    GoalStatus.STATUS_ACCEPTED,
    GoalStatus.STATUS_EXECUTING,
    GoalStatus.STATUS_CANCELING,
}
STATUS_NAMES = {
    GoalStatus.STATUS_UNKNOWN: "UNKNOWN",
    GoalStatus.STATUS_ACCEPTED: "ACCEPTED",
    GoalStatus.STATUS_EXECUTING: "EXECUTING",
    GoalStatus.STATUS_CANCELING: "CANCELING",
    GoalStatus.STATUS_SUCCEEDED: "SUCCEEDED",
    GoalStatus.STATUS_CANCELED: "CANCELED",
    GoalStatus.STATUS_ABORTED: "ABORTED",
}


def json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    return value


class TimelineRecorder:
    """Thread-safe JSONL recorder with a process-wide monotonic clock."""

    def __init__(self, path: str, run_id: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open("w", encoding="utf-8", buffering=1)
        self.run_id = run_id
        self.origin_ns = time.monotonic_ns()
        self.sequence = 0
        self.lock = threading.RLock()
        self.events: list[dict[str, Any]] = []

    def stamp(self, ros_time_ns: int | None = None) -> dict[str, Any]:
        monotonic_ns = time.monotonic_ns()
        wall = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        result: dict[str, Any] = {
            "monotonic_ns": monotonic_ns,
            "run_offset_ms": round((monotonic_ns - self.origin_ns) / 1_000_000.0, 6),
            "wall_utc": wall.replace("+00:00", "Z"),
        }
        if ros_time_ns is not None:
            result["ros_time_ns"] = int(ros_time_ns)
        return result

    def emit(
        self,
        source: str,
        event: str,
        *,
        case_id: str | None = None,
        trial_id: str | None = None,
        actor: str | None = None,
        data: dict[str, Any] | None = None,
        ros_time_ns: int | None = None,
    ) -> dict[str, Any]:
        with self.lock:
            self.sequence += 1
            record = {
                "schema": "xr-horus-nav2-timeline/v1",
                "run_id": self.run_id,
                "seq": self.sequence,
                "case_id": case_id,
                "trial_id": trial_id,
                **self.stamp(ros_time_ns),
                "source": source,
                "event": event,
                "actor": actor,
                "data": json_safe(data or {}),
            }
            self.events.append(record)
            self.stream.write(json.dumps(record, sort_keys=True) + "\n")
            return copy.deepcopy(record)

    def close(self) -> None:
        with self.lock:
            self.stream.flush()
            self.stream.close()


class XRSessionState(str, Enum):
    IDLE = "XR_SESSION_IDLE"
    READY = "XR_SESSION_READY"
    SYNCHRONIZED = "XR_SESSION_SYNCHRONIZED"
    VISIBLE = "XR_SESSION_VISIBLE"
    FOCUSED = "XR_SESSION_FOCUSED"
    STOPPING = "XR_SESSION_STOPPING"
    LOSS_PENDING = "XR_SESSION_LOSS_PENDING"
    EXITING = "XR_SESSION_EXITING"


class AppState(str, Enum):
    ACTIVE = "APP_ACTIVE"
    PAUSED = "APP_PAUSED"


class ControlState(str, Enum):
    INACTIVE = "CONTROL_INACTIVE"
    ACTIVE = "CONTROL_ACTIVE"
    RELEASED = "CONTROL_RELEASED"


class OpenXRStyleStateMachine:
    """A strict software model of relevant OpenXR-style lifecycle transitions."""

    _allowed: dict[XRSessionState, set[XRSessionState]] = {
        XRSessionState.IDLE: {XRSessionState.READY, XRSessionState.EXITING},
        XRSessionState.READY: {XRSessionState.SYNCHRONIZED, XRSessionState.STOPPING},
        XRSessionState.SYNCHRONIZED: {
            XRSessionState.VISIBLE,
            XRSessionState.STOPPING,
        },
        XRSessionState.VISIBLE: {
            XRSessionState.FOCUSED,
            XRSessionState.SYNCHRONIZED,
            XRSessionState.STOPPING,
        },
        XRSessionState.FOCUSED: {
            XRSessionState.VISIBLE,
            XRSessionState.STOPPING,
        },
        XRSessionState.STOPPING: {
            XRSessionState.IDLE,
            XRSessionState.LOSS_PENDING,
            XRSessionState.EXITING,
        },
        XRSessionState.LOSS_PENDING: {XRSessionState.IDLE},
        XRSessionState.EXITING: set(),
    }

    def __init__(
        self,
        recorder: TimelineRecorder,
        case_id: str,
        trial_id: str,
        actor: str,
    ) -> None:
        self.recorder = recorder
        self.case_id = case_id
        self.trial_id = trial_id
        self.actor = actor
        self.session = XRSessionState.IDLE
        self.app = AppState.PAUSED
        self.control = ControlState.INACTIVE

    @property
    def xr_input_active(self) -> bool:
        return self.session == XRSessionState.FOCUSED and self.app == AppState.ACTIVE

    def _emit(self, event: str, data: dict[str, Any]) -> dict[str, Any]:
        return self.recorder.emit(
            "mock_xr",
            event,
            case_id=self.case_id,
            trial_id=self.trial_id,
            actor=self.actor,
            data=data,
        )

    def transition(self, target: XRSessionState, reason: str) -> dict[str, Any]:
        if target not in self._allowed[self.session]:
            raise RuntimeError(f"invalid mock XR transition {self.session.value} -> {target.value}")
        previous = self.session
        before_input = self.xr_input_active
        self.session = target
        return self._emit(
            "XR_STATE_CHANGED",
            {
                "from": previous.value,
                "to": target.value,
                "reason": reason,
                "xr_input_active_before": before_input,
                "xr_input_active_after": self.xr_input_active,
                "mock_not_runtime_event": True,
            },
        )

    def set_app(self, target: AppState, reason: str) -> dict[str, Any]:
        previous = self.app
        before_input = self.xr_input_active
        self.app = target
        return self._emit(
            "APP_STATE_CHANGED",
            {
                "from": previous.value,
                "to": target.value,
                "reason": reason,
                "xr_input_active_before": before_input,
                "xr_input_active_after": self.xr_input_active,
            },
        )

    def set_control(self, target: ControlState, reason: str) -> dict[str, Any]:
        previous = self.control
        self.control = target
        return self._emit(
            "CONTROL_STATE_CHANGED",
            {
                "from": previous.value,
                "to": target.value,
                "reason": reason,
                "xr_input_active": self.xr_input_active,
                "control_policy_state": target.value,
            },
        )

    def boot_to_focused(self) -> list[dict[str, Any]]:
        events = [self.set_app(AppState.ACTIVE, "mock application foregrounded")]
        for target, reason in (
            (XRSessionState.READY, "runtime-style session ready"),
            (XRSessionState.SYNCHRONIZED, "frame loop synchronized"),
            (XRSessionState.VISIBLE, "frames visible"),
            (XRSessionState.FOCUSED, "eligible for XR input"),
        ):
            events.append(self.transition(target, reason))
        events.append(self.set_control(ControlState.ACTIVE, "application enables robot control"))
        return events

    def lose_focus(self, reason: str) -> dict[str, Any]:
        return self.transition(XRSessionState.VISIBLE, reason)

    def enter_stopping(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        if self.session == XRSessionState.FOCUSED:
            events.append(self.transition(XRSessionState.VISIBLE, "focus withdrawn before stop"))
        if self.session == XRSessionState.VISIBLE:
            events.append(
                self.transition(XRSessionState.SYNCHRONIZED, "session no longer visible")
            )
        events.append(
            self.transition(XRSessionState.STOPPING, "runtime-style stop requested")
        )
        return events


class XRMockHorusClient(HorusLinkClient):
    """Actual HorusLink transport with lifecycle-oriented helpers."""

    def heartbeat(
        self,
        request_id: str,
        app_id: str,
        role: str,
        logical_session_id: str,
    ) -> None:
        self.publish_json_string(
            LEASE_TOPIC,
            {
                "request_id": request_id,
                "robot_name": ROBOT,
                "app_id": app_id,
                "role": role,
                "session_id": logical_session_id,
                "action": "heartbeat",
                "panel_open": True,
                "teleop_active": True,
                "task_active": True,
                "task_kind": "navigation",
            },
        )

    def publish_cancel(self, value: str = "cancel") -> None:
        message = String()
        message.data = value
        self.publish_serialized(
            f"/{ROBOT}/goal_cancel",
            bytes(serialize_message(message)),
            include_cdr_header=False,
        )

    def publish_catalog(self) -> None:
        self.publish_json_string(
            CATALOG_TOPIC,
            {
                "role": "host",
                "op": "snapshot",
                "session_id": "xr-nav2-feasibility",
                "robots": [
                    {
                        "robot_name": ROBOT,
                        "protected_topics": [
                            GOAL_TOPIC,
                            f"/{ROBOT}/goal_cancel",
                        ],
                    }
                ],
            },
        )

    def publish_goal_pose(
        self,
        x: float,
        y: float,
        yaw: float,
        *,
        frame_id: str = "map",
    ) -> None:
        message = PoseStamped()
        message.header.frame_id = frame_id
        # A zero stamp asks TF consumers for the latest transform.  The older
        # probe's time.time() stamp is invalid against Nav2's simulated clock.
        message.header.stamp.sec = 0
        message.header.stamp.nanosec = 0
        message.pose.position.x = float(x)
        message.pose.position.y = float(y)
        message.pose.orientation.z = math.sin(float(yaw) / 2.0)
        message.pose.orientation.w = math.cos(float(yaw) / 2.0)
        self.publish_serialized(
            GOAL_TOPIC,
            bytes(serialize_message(message)),
            include_cdr_header=False,
        )

    @property
    def connected(self) -> bool:
        return self.realtime is not None and self.bulk is not None


@dataclass
class ClientRuntime:
    label: str
    client: XRMockHorusClient
    state: OpenXRStyleStateMachine
    wire_session_id: int
    logical_session_id: str
    heartbeat_enabled: bool = False
    heartbeat_count: int = 0
    next_heartbeat_ns: int = 0


class Nav2Observer(Node):
    """ROS observer and test-control node; never acts as an action server."""

    def __init__(self, args: argparse.Namespace, recorder: TimelineRecorder) -> None:
        super().__init__(
            "xr_mock_nav2_observer",
            parameter_overrides=[Parameter("use_sim_time", Parameter.Type.BOOL, True)],
        )
        self.args = args
        self.recorder = recorder
        self.callback_group = ReentrantCallbackGroup()
        self.lock = threading.RLock()
        self.current_case_id: str | None = None
        self.current_trial_id: str | None = None
        self.lease_events: list[dict[str, Any]] = []
        self.cancel_topic_events: list[dict[str, Any]] = []
        self.backend_status_events: list[dict[str, Any]] = []
        self.action_status_events: list[dict[str, Any]] = []
        self.action_status_latest: dict[str, int] = {}
        self.action_status_history: dict[str, list[dict[str, Any]]] = {}
        self.feedback_events: dict[str, list[dict[str, Any]]] = {}
        self.cmd_samples: list[dict[str, Any]] = []
        self.odom_samples: list[dict[str, Any]] = []
        self.latest_map: OccupancyGrid | None = None
        self.last_cmd_timeline_ns = 0
        self.last_cmd_moving: bool | None = None
        self.last_odom_timeline_ns = 0

        state_qos = QoSProfile(depth=100)
        state_qos.reliability = ReliabilityPolicy.RELIABLE
        state_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        map_qos = QoSProfile(depth=1)
        map_qos.reliability = ReliabilityPolicy.RELIABLE
        map_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        data_qos = QoSProfile(depth=200)
        data_qos.reliability = ReliabilityPolicy.RELIABLE
        data_qos.durability = DurabilityPolicy.VOLATILE

        self.create_subscription(String, STATE_TOPIC, self._on_lease_state, state_qos)
        self.create_subscription(
            String,
            f"/{args.robot}/goal_cancel",
            self._on_cancel_topic,
            data_qos,
        )
        self.create_subscription(
            String,
            f"/{args.robot}/goal_status",
            self._on_backend_status,
            data_qos,
        )
        self.create_subscription(
            GoalStatusArray,
            f"{args.nav2_action}/_action/status",
            self._on_action_status,
            qos_profile_action_status_default,
        )
        self.create_subscription(
            NavigateToPose.Impl.FeedbackMessage,
            f"{args.nav2_action}/_action/feedback",
            self._on_action_feedback,
            QoSProfile(depth=100),
        )
        self.create_subscription(Twist, args.cmd_topic, self._on_cmd, data_qos)
        self.create_subscription(Odometry, args.odom_topic, self._on_odom, data_qos)
        self.create_subscription(OccupancyGrid, args.map_topic, self._on_map, map_qos)

        self.initial_pose_pub = self.create_publisher(
            PoseWithCovarianceStamped,
            args.initialpose_topic,
            10,
        )
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.cleanup_cancel_client = self.create_client(
            CancelGoal,
            f"{args.nav2_action}/_action/cancel_goal",
            callback_group=self.callback_group,
        )
        self.nav2_action_client = ActionClient(
            self,
            NavigateToPose,
            args.nav2_action,
            callback_group=self.callback_group,
        )

    def set_trial(self, case_id: str | None, trial_id: str | None) -> None:
        with self.lock:
            self.current_case_id = case_id
            self.current_trial_id = trial_id

    @staticmethod
    def _ros_stamp_ns(stamp: Any) -> int:
        return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)

    @staticmethod
    def _uuid(value: Any) -> str:
        return bytes(value.uuid).hex()

    def _trial_context(self) -> tuple[str | None, str | None]:
        with self.lock:
            return self.current_case_id, self.current_trial_id

    def _on_lease_state(self, message: String) -> None:
        try:
            payload = json.loads(message.data)
        except json.JSONDecodeError:
            return
        case_id, trial_id = self._trial_context()
        event = self.recorder.emit(
            "horus_lease",
            "LEASE_EVENT_OBSERVED",
            case_id=case_id,
            trial_id=trial_id,
            data=payload,
        )
        with self.lock:
            self.lease_events.append({"at": event, "payload": payload})

    def _on_cancel_topic(self, message: String) -> None:
        case_id, trial_id = self._trial_context()
        event = self.recorder.emit(
            "horus_backend",
            "HORUS_CANCEL_TOPIC_OBSERVED",
            case_id=case_id,
            trial_id=trial_id,
            data={"payload": message.data},
        )
        with self.lock:
            self.cancel_topic_events.append({"at": event, "payload": message.data})

    def _on_backend_status(self, message: String) -> None:
        case_id, trial_id = self._trial_context()
        event = self.recorder.emit(
            "horus_backend",
            "HORUS_GOAL_STATUS",
            case_id=case_id,
            trial_id=trial_id,
            data={"status": message.data, "uuid_binding": "absent"},
        )
        with self.lock:
            self.backend_status_events.append({"at": event, "status": message.data})

    def _on_action_status(self, message: GoalStatusArray) -> None:
        case_id, trial_id = self._trial_context()
        observed_ids: set[str] = set()
        with self.lock:
            for item in message.status_list:
                identifier = self._uuid(item.goal_info.goal_id)
                observed_ids.add(identifier)
                status = int(item.status)
                previous = self.action_status_latest.get(identifier)
                self.action_status_latest[identifier] = status
                if previous == status:
                    continue
                event = self.recorder.emit(
                    "nav2",
                    "NAV2_GOAL_STATUS_CHANGED",
                    case_id=case_id,
                    trial_id=trial_id,
                    data={
                        "goal_uuid": identifier,
                        "from": None if previous is None else STATUS_NAMES.get(previous, str(previous)),
                        "to": STATUS_NAMES.get(status, str(status)),
                        "status_code": status,
                        "goal_info_ros_stamp_ns": self._ros_stamp_ns(item.goal_info.stamp),
                    },
                )
                record = {
                    "at": event,
                    "goal_uuid": identifier,
                    "status": status,
                    "status_name": STATUS_NAMES.get(status, str(status)),
                }
                self.action_status_events.append(record)
                self.action_status_history.setdefault(identifier, []).append(record)

    def _on_action_feedback(self, message: Any) -> None:
        identifier = self._uuid(message.goal_id)
        feedback = message.feedback
        ros_time_ns = self._ros_stamp_ns(feedback.current_pose.header.stamp)
        case_id, trial_id = self._trial_context()
        event = self.recorder.emit(
            "nav2",
            "NAV2_FEEDBACK_SAMPLE",
            case_id=case_id,
            trial_id=trial_id,
            data={
                "goal_uuid": identifier,
                "current_pose": {
                    "x": float(feedback.current_pose.pose.position.x),
                    "y": float(feedback.current_pose.pose.position.y),
                },
                "distance_remaining": float(feedback.distance_remaining),
                "number_of_recoveries": int(feedback.number_of_recoveries),
            },
            ros_time_ns=ros_time_ns,
        )
        with self.lock:
            self.feedback_events.setdefault(identifier, []).append({"at": event})

    def _on_cmd(self, message: Twist) -> None:
        stamp = self.recorder.stamp()
        linear_x = float(message.linear.x)
        linear_y = float(message.linear.y)
        angular_z = float(message.angular.z)
        magnitude = math.hypot(linear_x, linear_y) + abs(angular_z)
        moving = magnitude > self.args.cmd_stop_threshold
        sample = {
            "at": stamp,
            "linear_x": linear_x,
            "linear_y": linear_y,
            "angular_z": angular_z,
            "magnitude": magnitude,
            "moving": moving,
        }
        case_id, trial_id = self._trial_context()
        with self.lock:
            self.cmd_samples.append(sample)
            should_emit = (
                self.last_cmd_moving is None
                or moving != self.last_cmd_moving
                or stamp["monotonic_ns"] - self.last_cmd_timeline_ns >= 500_000_000
            )
            if should_emit:
                event_name = "CMD_VEL_STATE_CHANGED" if moving != self.last_cmd_moving else "CMD_VEL_SAMPLE"
                self.recorder.emit(
                    "loopback_sim",
                    event_name,
                    case_id=case_id,
                    trial_id=trial_id,
                    data={
                        "topic": self.args.cmd_topic,
                        "linear_x": linear_x,
                        "linear_y": linear_y,
                        "angular_z": angular_z,
                        "moving": moving,
                    },
                )
                self.last_cmd_timeline_ns = stamp["monotonic_ns"]
                self.last_cmd_moving = moving

    def _on_odom(self, message: Odometry) -> None:
        ros_time_ns = self._ros_stamp_ns(message.header.stamp)
        stamp = self.recorder.stamp(ros_time_ns)
        sample = {
            "at": stamp,
            "x": float(message.pose.pose.position.x),
            "y": float(message.pose.pose.position.y),
            "linear_x": float(message.twist.twist.linear.x),
            "angular_z": float(message.twist.twist.angular.z),
        }
        case_id, trial_id = self._trial_context()
        with self.lock:
            self.odom_samples.append(sample)
            if stamp["monotonic_ns"] - self.last_odom_timeline_ns >= 100_000_000:
                self.recorder.emit(
                    "loopback_sim",
                    "ODOM_SAMPLE",
                    case_id=case_id,
                    trial_id=trial_id,
                    data={
                        "topic": self.args.odom_topic,
                        "x": sample["x"],
                        "y": sample["y"],
                        "linear_x": sample["linear_x"],
                        "angular_z": sample["angular_z"],
                    },
                    ros_time_ns=ros_time_ns,
                )
                self.last_odom_timeline_ns = stamp["monotonic_ns"]

    def _on_map(self, message: OccupancyGrid) -> None:
        with self.lock:
            self.latest_map = message

    def lease_event_count(self) -> int:
        with self.lock:
            return len(self.lease_events)

    def cancel_event_count(self) -> int:
        with self.lock:
            return len(self.cancel_topic_events)

    def known_goal_ids(self) -> set[str]:
        with self.lock:
            return set(self.action_status_history)

    def active_goal_ids(self) -> list[str]:
        with self.lock:
            return sorted(
                identifier
                for identifier, status in self.action_status_latest.items()
                if status in ACTIVE_STATUSES
            )

    def latest_goal_status(self, identifier: str) -> int | None:
        with self.lock:
            return self.action_status_latest.get(identifier)

    def goal_record(self, identifier: str) -> dict[str, Any]:
        with self.lock:
            history = copy.deepcopy(self.action_status_history.get(identifier, []))
            feedback = copy.deepcopy(self.feedback_events.get(identifier, []))
            latest = self.action_status_latest.get(identifier)
        return {
            "goal_uuid": identifier,
            "latest_status": None if latest is None else STATUS_NAMES.get(latest, str(latest)),
            "latest_status_code": latest,
            "status_history": history,
            "feedback_count": len(feedback),
            "first_feedback_at": feedback[0]["at"] if feedback else None,
            "last_feedback_at": feedback[-1]["at"] if feedback else None,
        }

    def first_status_event(
        self,
        identifier: str,
        statuses: set[int],
        *,
        after_ns: int = 0,
    ) -> dict[str, Any] | None:
        with self.lock:
            for event in self.action_status_history.get(identifier, []):
                if event["status"] not in statuses:
                    continue
                if event["at"]["monotonic_ns"] < after_ns:
                    continue
                return copy.deepcopy(event)
        return None

    def new_goal_after(self, known_ids: set[str], after_ns: int) -> dict[str, Any] | None:
        with self.lock:
            candidates = [
                event
                for event in self.action_status_events
                if event["goal_uuid"] not in known_ids
                and event["at"]["monotonic_ns"] >= after_ns
                and event["status"] in {GoalStatus.STATUS_ACCEPTED, GoalStatus.STATUS_EXECUTING}
            ]
            if not candidates:
                return None
            return copy.deepcopy(min(candidates, key=lambda item: item["at"]["monotonic_ns"]))

    def find_lease_event(
        self,
        event_name: str,
        *,
        since: int,
        request_id: str | None = None,
    ) -> dict[str, Any] | None:
        with self.lock:
            for event in self.lease_events[since:]:
                payload = event["payload"]
                if payload.get("event") != event_name:
                    continue
                if request_id is not None and payload.get("request_id") != request_id:
                    continue
                return copy.deepcopy(event)
        return None

    def latest_lease_event(self) -> dict[str, Any] | None:
        with self.lock:
            return copy.deepcopy(self.lease_events[-1]) if self.lease_events else None

    def first_cancel_event(self, since: int) -> dict[str, Any] | None:
        with self.lock:
            if since >= len(self.cancel_topic_events):
                return None
            return copy.deepcopy(self.cancel_topic_events[since])

    def first_cancel_after(self, after_ns: int) -> dict[str, Any] | None:
        with self.lock:
            for event in self.cancel_topic_events:
                if event["at"]["monotonic_ns"] >= after_ns:
                    return copy.deepcopy(event)
        return None

    def backend_status_count(self) -> int:
        with self.lock:
            return len(self.backend_status_events)

    def first_backend_status(self, since: int, status: str) -> dict[str, Any] | None:
        with self.lock:
            for event in self.backend_status_events[since:]:
                if event["status"] == status:
                    return copy.deepcopy(event)
        return None

    def latest_odom(self) -> dict[str, Any] | None:
        with self.lock:
            return copy.deepcopy(self.odom_samples[-1]) if self.odom_samples else None

    def odom_metric(self, start_ns: int, end_ns: int) -> dict[str, Any]:
        with self.lock:
            before = [
                sample for sample in self.odom_samples
                if sample["at"]["monotonic_ns"] <= start_ns
            ]
            within = [
                sample for sample in self.odom_samples
                if start_ns < sample["at"]["monotonic_ns"] <= end_ns
            ]
            if before:
                selected = [before[-1], *within]
                baseline_basis = "latest_odom_at_or_before_event"
            elif within:
                selected = list(within)
                baseline_basis = "first_odom_after_event_no_prior_sample"
            else:
                selected = []
                baseline_basis = "no_odom_samples"
        path = 0.0
        for previous, current in zip(selected, selected[1:]):
            path += math.hypot(current["x"] - previous["x"], current["y"] - previous["y"])
        if len(selected) >= 2:
            net = math.hypot(selected[-1]["x"] - selected[0]["x"], selected[-1]["y"] - selected[0]["y"])
        else:
            net = 0.0
        return {
            "path_distance_m": round(path, 6),
            "net_displacement_m": round(net, 6),
            "sample_count": len(selected),
            "start_pose_odom": (
                None if not selected else {"x": selected[0]["x"], "y": selected[0]["y"]}
            ),
            "end_pose_odom": (
                None if not selected else {"x": selected[-1]["x"], "y": selected[-1]["y"]}
            ),
            "baseline_basis": baseline_basis,
            "distance_basis": "polyline integral of actual nav2_loopback_sim /odom output",
        }

    def motion_confirmation(self, since_ns: int) -> dict[str, Any] | None:
        with self.lock:
            moving_cmd = next(
                (
                    sample for sample in self.cmd_samples
                    if sample["at"]["monotonic_ns"] >= since_ns and sample["moving"]
                ),
                None,
            )
            latest_ns = time.monotonic_ns()
        if moving_cmd is None:
            return None
        metric = self.odom_metric(since_ns, latest_ns)
        if metric["path_distance_m"] < self.args.motion_confirm_distance_m:
            return None
        return {
            "first_nonzero_cmd_at": copy.deepcopy(moving_cmd["at"]),
            "confirmed_at": self.recorder.stamp(),
            "path_distance_since_goal_m": metric["path_distance_m"],
        }

    def robot_stop_candidate(self, after_ns: int) -> dict[str, Any] | None:
        now_ns = time.monotonic_ns()
        hold_ns = int(self.args.stop_hold_sec * 1_000_000_000)
        with self.lock:
            relevant = [
                sample for sample in self.cmd_samples
                if sample["at"]["monotonic_ns"] >= after_ns
            ]
            if not relevant or relevant[-1]["moving"]:
                return None
            zero_start_ns: int | None = None
            for sample in reversed(relevant):
                if sample["moving"]:
                    break
                zero_start_ns = sample["at"]["monotonic_ns"]
            if zero_start_ns is None or now_ns - zero_start_ns < hold_ns:
                return None
        stability = self.odom_metric(max(zero_start_ns, now_ns - hold_ns), now_ns)
        if stability["path_distance_m"] > self.args.stop_odom_epsilon_m:
            return None
        return {
            "detected_at": self.recorder.stamp(),
            "zero_cmd_since_monotonic_ns": zero_start_ns,
            "hold_sec": self.args.stop_hold_sec,
            "odom_path_during_hold_m": stability["path_distance_m"],
        }

    def map_pose(self) -> dict[str, float] | None:
        try:
            transform = self.tf_buffer.lookup_transform(
                self.args.map_frame,
                self.args.base_frame,
                Time(),
            )
        except Exception:
            return None
        return {
            "x": float(transform.transform.translation.x),
            "y": float(transform.transform.translation.y),
        }

    def target_is_free(self, x: float, y: float) -> dict[str, Any]:
        with self.lock:
            map_message = self.latest_map
        if map_message is None:
            return {"checked": False, "reason": "map_not_observed"}
        info = map_message.info
        mx = int((x - info.origin.position.x) / info.resolution)
        my = int((y - info.origin.position.y) / info.resolution)
        if mx < 0 or my < 0 or mx >= info.width or my >= info.height:
            return {"checked": True, "free": False, "reason": "outside_map", "mx": mx, "my": my}
        radius_cells = max(1, int(math.ceil(self.args.target_clearance_m / info.resolution)))
        values: list[int] = []
        for iy in range(max(0, my - radius_cells), min(info.height, my + radius_cells + 1)):
            for ix in range(max(0, mx - radius_cells), min(info.width, mx + radius_cells + 1)):
                values.append(int(map_message.data[iy * info.width + ix]))
        free = bool(values) and all(value >= 0 and value < 50 for value in values)
        return {
            "checked": True,
            "free": free,
            "mx": mx,
            "my": my,
            "max_occupancy_in_clearance": max(values) if values else None,
            "clearance_m": self.args.target_clearance_m,
        }

    def publish_initial_pose(self, x: float, y: float, yaw: float) -> dict[str, Any]:
        message = PoseWithCovarianceStamped()
        message.header.frame_id = self.args.map_frame
        message.header.stamp = self.get_clock().now().to_msg()
        message.pose.pose.position.x = x
        message.pose.pose.position.y = y
        message.pose.pose.orientation.z = math.sin(yaw / 2.0)
        message.pose.pose.orientation.w = math.cos(yaw / 2.0)
        message.pose.covariance[0] = 0.01
        message.pose.covariance[7] = 0.01
        message.pose.covariance[35] = 0.01
        event = self.recorder.emit(
            "probe",
            "INITIAL_POSE_PUBLISHED",
            case_id=self.current_case_id,
            trial_id=self.current_trial_id,
            data={"x": x, "y": y, "yaw": yaw, "frame_id": self.args.map_frame},
            ros_time_ns=self.get_clock().now().nanoseconds,
        )
        for _ in range(3):
            self.initial_pose_pub.publish(message)
            time.sleep(0.05)
        return event

    def action_server_ready(self) -> bool:
        return self.nav2_action_client.server_is_ready()

    def register_robot(self, wait: Callable[..., Any]) -> dict[str, Any]:
        client = self.create_client(
            RegisterRobot,
            "/horus/register_robot",
            callback_group=self.callback_group,
        )
        try:
            if not client.wait_for_service(timeout_sec=self.args.readiness_timeout_sec):
                raise RuntimeError("HORUS register_robot service unavailable")
            request = RegisterRobot.Request()
            request.robot_config.name = self.args.robot
            request.robot_config.robot_type = "wheeled"
            request.robot_config.control_topics = [
                f"/{self.args.robot}/goal_pose",
                f"/{self.args.robot}/goal_cancel",
            ]
            request.robot_config.status_topics = [f"/{self.args.robot}/goal_status"]
            request.robot_config.metadata_keys = [
                "horus.backend.nav2_action_topic",
                "horus.backend.goal_topic",
                "horus.backend.cancel_topic",
                "horus.backend.status_topic",
            ]
            request.robot_config.metadata_values = [
                self.args.nav2_action,
                f"/{self.args.robot}/goal_pose",
                f"/{self.args.robot}/goal_cancel",
                f"/{self.args.robot}/goal_status",
            ]
            sent = self.recorder.emit(
                "probe",
                "HORUS_ROBOT_REGISTRATION_SENT",
                data={"action_topic": self.args.nav2_action, "robot": self.args.robot},
            )
            future = client.call_async(request)
            wait(future.done, self.args.readiness_timeout_sec, "HORUS robot registration")
            response = future.result()
            if response is None or not response.success:
                detail = "no response" if response is None else response.error_message
                raise RuntimeError(f"HORUS robot registration failed: {detail}")
            return {
                "sent_at": sent,
                "completed_at": self.recorder.stamp(),
                "robot_id": response.robot_id,
                "action_topic": self.args.nav2_action,
            }
        finally:
            self.destroy_client(client)

    def unregister_robot(self, robot_id: str, wait: Callable[..., Any]) -> dict[str, Any]:
        client = self.create_client(
            UnregisterRobot,
            "/horus/unregister_robot",
            callback_group=self.callback_group,
        )
        try:
            if not client.wait_for_service(timeout_sec=3.0):
                raise RuntimeError("HORUS unregister_robot service unavailable")
            request = UnregisterRobot.Request()
            request.robot_id = robot_id
            future = client.call_async(request)
            wait(future.done, 5.0, "HORUS robot unregistration")
            response = future.result()
            if response is None or not response.success:
                detail = "no response" if response is None else response.error_message
                raise RuntimeError(f"HORUS robot unregistration failed: {detail}")
            return {"success": True, "robot_id": robot_id, "completed_at": self.recorder.stamp()}
        finally:
            self.destroy_client(client)

    def lifecycle_states(self, wait: Callable[..., Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for node_name in self.args.lifecycle_nodes:
            service = f"/{node_name}/get_state"
            client = self.create_client(GetState, service, callback_group=self.callback_group)
            try:
                if not client.wait_for_service(timeout_sec=2.0):
                    result[node_name] = {"available": False, "active": False}
                    continue
                future = client.call_async(GetState.Request())
                wait(future.done, 3.0, f"lifecycle state {node_name}")
                response = future.result()
                if response is None:
                    result[node_name] = {"available": True, "active": False, "error": "no response"}
                else:
                    result[node_name] = {
                        "available": True,
                        "id": int(response.current_state.id),
                        "label": response.current_state.label,
                        "active": int(response.current_state.id) == State.PRIMARY_STATE_ACTIVE,
                    }
            finally:
                self.destroy_client(client)
        return result

    def clear_costmaps(self, wait: Callable[..., Any]) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for service in (
            "/global_costmap/clear_entirely_global_costmap",
            "/local_costmap/clear_entirely_local_costmap",
        ):
            client = self.create_client(
                ClearEntireCostmap,
                service,
                callback_group=self.callback_group,
            )
            try:
                if not client.wait_for_service(timeout_sec=0.5):
                    results[service] = "UNAVAILABLE_OPTIONAL"
                    continue
                future = client.call_async(ClearEntireCostmap.Request())
                wait(future.done, 3.0, f"clear costmap {service}")
                results[service] = "CALLED" if future.result() is not None else "NO_RESPONSE"
            except Exception as exc:
                results[service] = f"ERROR: {type(exc).__name__}: {exc}"
            finally:
                self.destroy_client(client)
        return results

    def cancel_all_for_cleanup(self, wait: Callable[..., Any]) -> dict[str, Any]:
        if not self.cleanup_cancel_client.wait_for_service(timeout_sec=2.0):
            return {"success": False, "error": "cancel service unavailable"}
        request = CancelGoal.Request()
        # Zero UUID and zero stamp has the ROS Action protocol meaning "all goals".
        request.goal_info.goal_id.uuid = [0] * 16
        request.goal_info.stamp.sec = 0
        request.goal_info.stamp.nanosec = 0
        sent = self.recorder.emit(
            "probe",
            "TEST_CLEANUP_CANCEL_ALL_SENT",
            case_id=self.current_case_id,
            trial_id=self.current_trial_id,
            data={"measurement_event": False, "service": f"{self.args.nav2_action}/_action/cancel_goal"},
        )
        future = self.cleanup_cancel_client.call_async(request)
        try:
            wait(future.done, 5.0, "cleanup cancel-all response")
            response = future.result()
            if response is None:
                return {"success": False, "sent_at": sent, "error": "no response"}
            return {
                "success": True,
                "sent_at": sent,
                "return_code": int(response.return_code),
                "goal_ids_canceling": [self._uuid(item.goal_id) for item in response.goals_canceling],
            }
        except Exception as exc:
            return {"success": False, "sent_at": sent, "error": f"{type(exc).__name__}: {exc}"}

    def destroy_observer(self) -> None:
        self.nav2_action_client.destroy()
        self.destroy_node()


@dataclass
class TrialContext:
    case_id: str
    trial_number: int
    trial_id: str
    started_at: dict[str, Any]
    timeline_seq_start: int
    clients: dict[str, ClientRuntime] = field(default_factory=dict)
    goal_ids: dict[str, str] = field(default_factory=dict)
    goal_targets: dict[str, dict[str, float]] = field(default_factory=dict)
    logical_a_session: str = ""
    measurement_end_ns: int | None = None
    measurement_robot_stop: dict[str, Any] | None = None
    cleanup: dict[str, Any] = field(default_factory=dict)


class XRNav2TrialRunner:
    def __init__(
        self,
        node: Nav2Observer,
        recorder: TimelineRecorder,
        args: argparse.Namespace,
    ) -> None:
        self.node = node
        self.recorder = recorder
        self.args = args
        self.robot_id: str | None = None
        self.heartbeat_sequence = 0
        self.results: list[dict[str, Any]] = []
        self.revocation_stream = self._open_result_stream(args.revocation_log)
        self.handoff_stream = self._open_result_stream(args.handoff_log)

    @staticmethod
    def _open_result_stream(path: str) -> Any:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        return output.open("w", encoding="utf-8", buffering=1)

    def progress(self, message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    def wait(
        self,
        predicate: Callable[[], Any],
        timeout_s: float,
        description: str,
        *,
        ctx: TrialContext | None = None,
    ) -> Any:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if ctx is not None:
                self.tick_heartbeats(ctx)
            value = predicate()
            if value:
                return value
            time.sleep(0.025)
        if ctx is not None:
            self.tick_heartbeats(ctx)
        value = predicate()
        if value:
            return value
        raise RuntimeError(f"timeout waiting for {description}")

    def wait_until_ns(self, ctx: TrialContext, target_ns: int) -> None:
        while time.monotonic_ns() < target_ns:
            self.tick_heartbeats(ctx)
            remaining = (target_ns - time.monotonic_ns()) / 1_000_000_000.0
            if remaining > 0:
                time.sleep(min(0.025, remaining))

    def tick_heartbeats(self, ctx: TrialContext) -> None:
        now_ns = time.monotonic_ns()
        interval_ns = int(self.args.heartbeat_interval_sec * 1_000_000_000)
        for runtime in ctx.clients.values():
            if not runtime.heartbeat_enabled or not runtime.client.connected:
                continue
            if now_ns < runtime.next_heartbeat_ns:
                continue
            self.heartbeat_sequence += 1
            request_id = f"{ctx.trial_id}-{runtime.label}-hb-{self.heartbeat_sequence}"
            runtime.client.heartbeat(
                request_id,
                f"xr-mock-{runtime.label}",
                "operator",
                runtime.logical_session_id,
            )
            runtime.heartbeat_count += 1
            runtime.next_heartbeat_ns = now_ns + interval_ns
            self.recorder.emit(
                "horuslink",
                "LEASE_HEARTBEAT_SENT",
                case_id=ctx.case_id,
                trial_id=ctx.trial_id,
                actor=runtime.label,
                data={
                    "request_id": request_id,
                    "logical_session_id": runtime.logical_session_id,
                    "count": runtime.heartbeat_count,
                },
            )

    def set_heartbeat(self, ctx: TrialContext, label: str, enabled: bool) -> None:
        runtime = ctx.clients[label]
        runtime.heartbeat_enabled = enabled
        runtime.next_heartbeat_ns = time.monotonic_ns()
        self.recorder.emit(
            "probe",
            "HEARTBEAT_POLICY_CHANGED",
            case_id=ctx.case_id,
            trial_id=ctx.trial_id,
            actor=label,
            data={"enabled": enabled},
        )

    def _wire_session_id(self, case_id: str, trial_number: int, label: str) -> int:
        case_seed = sum(ord(char) for char in case_id) & 0xFFFF
        label_seed = sum(ord(char) for char in label) & 0xFF
        return (case_seed << 32) | (trial_number << 16) | (label_seed << 8) | 1

    def new_client(self, ctx: TrialContext, label: str, logical_session_id: str) -> ClientRuntime:
        wire_session = self._wire_session_id(ctx.case_id, ctx.trial_number, label)
        client = XRMockHorusClient(f"{ctx.trial_id}-{label}", wire_session)
        state = OpenXRStyleStateMachine(
            self.recorder,
            ctx.case_id,
            ctx.trial_id,
            label,
        )
        runtime = ClientRuntime(
            label=label,
            client=client,
            state=state,
            wire_session_id=wire_session,
            logical_session_id=logical_session_id,
        )
        ctx.clients[label] = runtime
        client.connect()
        publishers = [
            (1, CATALOG_TOPIC, "std_msgs/msg/String"),
            (2, LEASE_TOPIC, "std_msgs/msg/String"),
            (3, GOAL_TOPIC, "geometry_msgs/msg/PoseStamped"),
            (4, f"/{self.args.robot}/goal_cancel", "std_msgs/msg/String"),
        ]
        for channel, topic, type_name in publishers:
            client.register_publisher(channel, topic, type_name)
        self.recorder.emit(
            "horuslink",
            "HORUSLINK_CONNECTED",
            case_id=ctx.case_id,
            trial_id=ctx.trial_id,
            actor=label,
            data={
                "wire_session_id": wire_session,
                "logical_lease_session_id": logical_session_id,
                "lanes": ["realtime", "bulk"],
            },
        )
        return runtime

    def acquire(self, ctx: TrialContext, label: str, suffix: str = "acquire") -> dict[str, Any]:
        runtime = ctx.clients[label]
        request_id = f"{ctx.trial_id}-{label}-{suffix}"
        since = self.node.lease_event_count()
        sent = self.recorder.emit(
            "horuslink",
            "LEASE_REQUEST_SENT",
            case_id=ctx.case_id,
            trial_id=ctx.trial_id,
            actor=label,
            data={
                "action": "acquire",
                "request_id": request_id,
                "logical_session_id": runtime.logical_session_id,
            },
        )
        runtime.client.acquire(
            request_id,
            f"xr-mock-{label}",
            "operator",
            runtime.logical_session_id,
        )
        observed = self.wait(
            lambda: self.node.find_lease_event("lease_granted", since=since, request_id=request_id)
            or self.node.find_lease_event("lease_updated", since=since, request_id=request_id)
            or self.node.find_lease_event("lease_reassigned_inactive", since=since, request_id=request_id),
            4.0,
            f"{label} lease grant",
            ctx=ctx,
        )
        return {"request_id": request_id, "sent_at": sent, "observed": observed}

    def release(self, ctx: TrialContext, label: str, suffix: str = "release") -> dict[str, Any]:
        runtime = ctx.clients[label]
        # Disabling first is essential: a heartbeat after release implicitly reacquires.
        self.set_heartbeat(ctx, label, False)
        request_id = f"{ctx.trial_id}-{label}-{suffix}"
        since = self.node.lease_event_count()
        sent = self.recorder.emit(
            "horuslink",
            "LEASE_REQUEST_SENT",
            case_id=ctx.case_id,
            trial_id=ctx.trial_id,
            actor=label,
            data={"action": "release", "request_id": request_id},
        )
        runtime.client.release(request_id)
        observed = self.wait(
            lambda: self.node.find_lease_event(
                "lease_released", since=since, request_id=request_id
            ),
            4.0,
            f"{label} lease release",
            ctx=ctx,
        )
        return {"request_id": request_id, "sent_at": sent, "observed": observed}

    def send_goal(
        self,
        ctx: TrialContext,
        label: str,
        role: str,
        target: tuple[float, float, float],
        *,
        expect_accept: bool = True,
        allow_reject: bool = False,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        known_ids = self.node.known_goal_ids()
        backend_since = self.node.backend_status_count()
        runtime = ctx.clients[label]
        sent = self.recorder.emit(
            "horuslink",
            "GOAL_POSE_SENT",
            case_id=ctx.case_id,
            trial_id=ctx.trial_id,
            actor=label,
            data={
                "goal_role": role,
                "target": {"x": target[0], "y": target[1], "yaw": target[2]},
                "frame_id": self.args.map_frame,
                "pose_stamp_policy": "zero_latest_transform",
                "command_has_lease_epoch": False,
            },
        )
        runtime.client.publish_goal_pose(*target, frame_id=self.args.map_frame)
        timeout = self.args.goal_accept_timeout_sec if timeout_s is None else timeout_s
        if not expect_accept:
            deadline = time.monotonic_ns() + int(timeout * 1_000_000_000)
            self.wait_until_ns(ctx, deadline)
            new_goal = self.node.new_goal_after(known_ids, sent["monotonic_ns"])
            if new_goal is not None:
                identifier = new_goal["goal_uuid"]
                ctx.goal_ids[role] = identifier
                ctx.goal_targets[role] = {
                    "x": target[0],
                    "y": target[1],
                    "yaw": target[2],
                }
            return {"sent_at": sent, "accepted": new_goal is not None, "goal_event": new_goal}
        rejection_observed: dict[str, Any] | None = None

        def goal_outcome() -> dict[str, Any] | None:
            nonlocal rejection_observed
            new_goal = self.node.new_goal_after(known_ids, sent["monotonic_ns"])
            if new_goal is not None:
                return new_goal
            if not allow_reject:
                return None
            if rejection_observed is None:
                rejection_observed = self.node.first_backend_status(
                    backend_since, "goal_failed"
                )
            if rejection_observed is None:
                return None
            # The adapter's status topic has no Goal UUID.  During Nav2
            # preemption, A's late ABORTED result can publish `goal_failed`
            # milliseconds before B's new UUID appears.  Give the action status
            # stream a bounded grace interval before calling B rejected.
            rejection_age_ns = (
                time.monotonic_ns()
                - rejection_observed["at"]["monotonic_ns"]
            )
            if rejection_age_ns < 500_000_000:
                return None
            return {"rejected": True, "backend_event": rejection_observed}

        outcome = self.wait(
            goal_outcome,
            timeout,
            f"new Nav2 goal UUID or explicit rejection for {role}",
            ctx=ctx,
        )
        if outcome.get("rejected"):
            return {
                "sent_at": sent,
                "accepted": False,
                "rejection_observed": outcome["backend_event"],
                "uuid_mapping_basis": "HORUS backend goal_failed; rejected goals have no status UUID",
            }
        new_goal = outcome
        identifier = new_goal["goal_uuid"]
        ctx.goal_ids[role] = identifier
        ctx.goal_targets[role] = {"x": target[0], "y": target[1], "yaw": target[2]}
        return {
            "sent_at": sent,
            "accepted": True,
            "goal_uuid": identifier,
            "accepted_observed_at": new_goal["at"],
            "uuid_mapping_basis": "first new NavigateToPose status UUID after HorusLink goal publish",
        }

    def setup_trial(self, case_id: str, trial_number: int, *, need_b: bool) -> tuple[TrialContext, dict[str, Any]]:
        trial_id = f"{case_id}-T{trial_number:02d}"
        started = self.recorder.emit(
            "probe",
            "TRIAL_BEGIN",
            case_id=case_id,
            trial_id=trial_id,
            data={"trial_number": trial_number},
        )
        ctx = TrialContext(
            case_id=case_id,
            trial_number=trial_number,
            trial_id=trial_id,
            started_at=started,
            timeline_seq_start=started["seq"],
            logical_a_session=f"{trial_id}-logical-session-A",
        )
        self.node.set_trial(case_id, trial_id)
        try:
            if self.node.active_goal_ids():
                self.node.cancel_all_for_cleanup(self.wait)
                self.wait(
                    lambda: not self.node.active_goal_ids(),
                    8.0,
                    "no active Nav2 goals before trial",
                )
            a = self.new_client(ctx, "A", ctx.logical_a_session)
            if need_b:
                self.new_client(ctx, "B", f"{trial_id}-logical-session-B")

            catalog_since = self.node.lease_event_count()
            a.client.publish_catalog()
            catalog = self.wait(
                lambda: self.node.find_lease_event("snapshot", since=catalog_since),
                4.0,
                "protected catalog snapshot",
                ctx=ctx,
            )
            if catalog["payload"].get("leases"):
                raise RuntimeError(f"unclean lease state before trial: {catalog['payload']['leases']}")

            self.node.publish_initial_pose(
                self.args.start_x,
                self.args.start_y,
                self.args.start_yaw,
            )
            pose = self.wait(
                lambda: (
                    current
                    if (current := self.node.map_pose()) is not None
                    and math.hypot(
                        current["x"] - self.args.start_x,
                        current["y"] - self.args.start_y,
                    ) <= self.args.reset_pose_tolerance_m
                    else None
                ),
                self.args.readiness_timeout_sec,
                "loopback map pose reset",
                ctx=ctx,
            )
            costmaps = self.node.clear_costmaps(self.wait)
            a.state.boot_to_focused()
            acquire = self.acquire(ctx, "A")
            self.set_heartbeat(ctx, "A", True)
            target_a = (self.args.goal_a_x, self.args.goal_a_y, self.args.goal_a_yaw)
            goal = self.send_goal(ctx, "A", "A", target_a)
            goal_id = goal["goal_uuid"]
            motion = self.wait(
                lambda: self.node.motion_confirmation(goal["sent_at"]["monotonic_ns"]),
                self.args.motion_timeout_sec,
                "nonzero cmd_vel and odometry movement",
                ctx=ctx,
            )
            self.recorder.emit(
                "probe",
                "MOTION_CONFIRMED",
                case_id=case_id,
                trial_id=trial_id,
                actor="A",
                data={"goal_uuid": goal_id, **motion},
            )
            target_ns = motion["confirmed_at"]["monotonic_ns"] + int(
                self.args.revocation_delay_sec * 1_000_000_000
            )
            self.wait_until_ns(ctx, target_ns)
            clean_event = self.recorder.emit(
                "probe",
                "CLEAN_STATE_CONFIRMED",
                case_id=case_id,
                trial_id=trial_id,
                data={
                    "catalog_leases_before_acquire": catalog["payload"].get("leases", []),
                    "reset_map_pose": pose,
                    "costmap_clear": costmaps,
                    "goal_uuid": goal_id,
                },
            )
            return ctx, {
                "fresh_trial_state_verified": True,
                "catalog": catalog,
                "reset_map_pose": pose,
                "costmap_clear": costmaps,
                "lease_acquire": acquire,
                "goal_a": goal,
                "motion": motion,
                "revocation_delay_origin": "motion_confirmation",
                "clean_state_event": clean_event,
            }
        except Exception:
            self.cleanup_trial(ctx)
            raise

    def observe_window(
        self,
        ctx: TrialContext,
        origin: dict[str, Any],
        goal_ids: Iterable[str],
    ) -> dict[str, Any]:
        origin_ns = int(origin["monotonic_ns"])
        end_ns = origin_ns + int(self.args.observation_sec * 1_000_000_000)
        stop: dict[str, Any] | None = None
        checkpoints: list[dict[str, Any]] = []
        checkpoint_offsets = sorted(
            set(
                point
                for point in (0.5, 1.0, 2.0, 3.0, 5.0, self.args.observation_sec)
                if point <= self.args.observation_sec + 1e-9
            )
        )
        for offset in checkpoint_offsets:
            self.wait_until_ns(ctx, origin_ns + int(offset * 1_000_000_000))
            if stop is None:
                stop = self.node.robot_stop_candidate(origin_ns)
                if stop is not None:
                    self.recorder.emit(
                        "probe",
                        "ROBOT_STOP_DETECTED",
                        case_id=ctx.case_id,
                        trial_id=ctx.trial_id,
                        data=stop,
                    )
            latest_lease = self.node.latest_lease_event()
            checkpoints.append(
                {
                    "scheduled_offset_s": offset,
                    "observed_at": self.recorder.stamp(),
                    "lease_state": None if latest_lease is None else latest_lease["payload"],
                    "goals": {
                        identifier: self.node.goal_record(identifier)
                        for identifier in goal_ids
                    },
                    "odom": self.node.odom_metric(origin_ns, time.monotonic_ns()),
                }
            )
        if time.monotonic_ns() < end_ns:
            self.wait_until_ns(ctx, end_ns)
        if stop is None:
            stop = self.node.robot_stop_candidate(origin_ns)
        ctx.measurement_end_ns = time.monotonic_ns()
        ctx.measurement_robot_stop = copy.deepcopy(stop)
        metric_end_ns = (
            stop["detected_at"]["monotonic_ns"] if stop is not None else ctx.measurement_end_ns
        )
        motion = self.node.odom_metric(origin_ns, metric_end_ns)
        return {
            "origin": origin,
            "completed_at": self.recorder.stamp(),
            "checkpoints": checkpoints,
            "robot_stop": stop,
            "motion": motion,
            "distance_right_censored_at_observation_end": stop is None,
        }

    @staticmethod
    def elapsed_ms(later: dict[str, Any] | None, earlier: dict[str, Any] | None) -> float | None:
        if later is None or earlier is None:
            return None
        return round((later["monotonic_ns"] - earlier["monotonic_ns"]) / 1_000_000.0, 6)

    def common_result(
        self,
        ctx: TrialContext,
        setup: dict[str, Any],
        policy: str,
        expected: str,
    ) -> dict[str, Any]:
        return {
            "case_id": ctx.case_id,
            "trial_id": ctx.trial_id,
            "trial_number": ctx.trial_number,
            "policy": policy,
            "expected": expected,
            "started_at": ctx.started_at,
            "setup": setup,
            "architecture": [
                "Mock OpenXR-style lifecycle",
                "actual HorusLink",
                "actual HORUS bridge/backend Nav2ActionAdapter",
                "actual Nav2 NavigateToPose",
                "nav2_loopback_sim simulated robot",
            ],
            "mock_xr_is_not_runtime_event": True,
            "physical_robot": False,
        }

    def run_f0(self, trial_number: int) -> dict[str, Any]:
        ctx, setup = self.setup_trial("F0", trial_number, need_b=False)
        result = self.common_result(
            ctx,
            setup,
            "BASELINE",
            "official HORUS cancel reaches actual Nav2; Goal becomes CANCELED and simulated robot stops",
        )
        try:
            a = ctx.clients["A"]
            goal_id = ctx.goal_ids["A"]
            cancel_since = self.node.cancel_event_count()
            sent = self.recorder.emit(
                "horuslink",
                "EXPLICIT_CANCEL_SENT",
                case_id=ctx.case_id,
                trial_id=ctx.trial_id,
                actor="A",
                data={"goal_uuid": goal_id, "payload": "cancel"},
            )
            a.client.publish_cancel()
            cancel_topic = self.wait(
                lambda: self.node.first_cancel_event(cancel_since),
                3.0,
                "HORUS cancel topic observation",
                ctx=ctx,
            )
            terminal = self.wait(
                lambda: self.node.first_status_event(
                    goal_id,
                    TERMINAL_STATUSES,
                    after_ns=sent["monotonic_ns"],
                ),
                10.0,
                "F0 Goal terminal status",
                ctx=ctx,
            )
            stop = self.wait(
                lambda: self.node.robot_stop_candidate(sent["monotonic_ns"]),
                8.0,
                "F0 simulated robot stop",
                ctx=ctx,
            )
            self.recorder.emit(
                "probe",
                "ROBOT_STOP_DETECTED",
                case_id=ctx.case_id,
                trial_id=ctx.trial_id,
                data=stop,
            )
            ctx.measurement_robot_stop = copy.deepcopy(stop)
            ctx.measurement_end_ns = time.monotonic_ns()
            motion = self.node.odom_metric(
                sent["monotonic_ns"], stop["detected_at"]["monotonic_ns"]
            )
            passed = terminal["status"] == GoalStatus.STATUS_CANCELED
            result.update(
                {
                    "cancel_sent_at": sent,
                    "cancel_topic_observed": cancel_topic,
                    "goal_terminal_event": terminal,
                    "goal": self.node.goal_record(goal_id),
                    "robot_stop": stop,
                    "post_cancel_motion": motion,
                    "metrics_ms": {
                        "cancel_send_to_topic": self.elapsed_ms(cancel_topic["at"], sent),
                        "cancel_send_to_terminal": self.elapsed_ms(terminal["at"], sent),
                        "cancel_send_to_robot_stop": self.elapsed_ms(stop["detected_at"], sent),
                    },
                    "classification": (
                        "EXPLICIT_CANCEL_SAFE" if passed else "EXPLICIT_CANCEL_BASELINE_INVALID"
                    ),
                    "observed": terminal["status_name"],
                    "measurement_verdict": "PASS" if passed else "FAIL",
                }
            )
            return self.finish_result(ctx, result)
        except Exception:
            self.cleanup_trial(ctx)
            raise

    def run_f1(self, trial_number: int) -> dict[str, Any]:
        ctx, setup = self.setup_trial("F1", trial_number, need_b=False)
        result = self.common_result(
            ctx,
            setup,
            "P1_XR_EVENT_ONLY",
            "XR input focus becomes inactive while connection, heartbeat, and HORUS lease remain active",
        )
        try:
            a = ctx.clients["A"]
            focus = a.state.lose_focus("F1 policy P1 focus loss only")
            observation = self.observe_window(ctx, focus, [ctx.goal_ids["A"]])
            latest_lease = self.node.latest_lease_event()
            lease_present = bool(latest_lease and latest_lease["payload"].get("leases"))
            status = self.node.latest_goal_status(ctx.goal_ids["A"])
            result.update(
                {
                    "xr_event": focus,
                    "control_state_after_event": a.state.control.value,
                    "xr_input_active_after_event": a.state.xr_input_active,
                    "heartbeat_maintained": a.heartbeat_count > 0 and a.heartbeat_enabled,
                    "lease_present_at_observation_end": lease_present,
                    "goal": self.node.goal_record(ctx.goal_ids["A"]),
                    "observation": observation,
                    "classification": "P1_NO_AUTOMATIC_CROSS_DOMAIN_PROPAGATION",
                    "observed": {
                        "goal_status": None if status is None else STATUS_NAMES.get(status, str(status)),
                        "lease_present": lease_present,
                        "path_distance_after_focus_loss_m": observation["motion"]["path_distance_m"],
                    },
                    "interpretation_guardrail": (
                        "HORUS does not receive OpenXR events; persistence under P1 is supporting "
                        "behavior, not by itself a vulnerability"
                    ),
                    "measurement_verdict": "MEASURED",
                }
            )
            return self.finish_result(ctx, result)
        except Exception:
            self.cleanup_trial(ctx)
            raise

    def _revocation_result(
        self,
        ctx: TrialContext,
        setup: dict[str, Any],
        authority_event: dict[str, Any],
        revocation: dict[str, Any],
        policy: str,
    ) -> dict[str, Any]:
        goal_id = ctx.goal_ids["A"]
        revocation_at = revocation["observed"]["at"]
        observation = self.observe_window(ctx, revocation_at, [goal_id])
        # A revocation implementation could publish cancel before the lease-state
        # callback is observed, so search from the authority event rather than
        # taking an index after the revocation has already completed.
        cancel_topic = self.node.first_cancel_after(authority_event["monotonic_ns"])
        canceling = self.node.first_status_event(
            goal_id,
            {GoalStatus.STATUS_CANCELING},
            after_ns=revocation_at["monotonic_ns"],
        )
        terminal = self.node.first_status_event(
            goal_id,
            TERMINAL_STATUSES,
            after_ns=revocation_at["monotonic_ns"],
        )
        latest = self.node.latest_goal_status(goal_id)
        if canceling is not None or (terminal is not None and terminal["status"] == GoalStatus.STATUS_CANCELED):
            classification = "LEASE_REVOCATION_TERMINATED_NAV2_GOAL"
        elif latest in ACTIVE_STATUSES:
            classification = "REVOCATION_PROPAGATED_BUT_NAV2_GOAL_CONTINUED"
        elif terminal is not None and terminal["status"] == GoalStatus.STATUS_SUCCEEDED:
            classification = "GOAL_CONTINUED_TO_NATURAL_SUCCESS"
        else:
            classification = "GOAL_TERMINATED_WITHOUT_REVOCATION_CANCEL"
        result = self.common_result(
            ctx,
            setup,
            policy,
            "XR control revoke reaches HORUS lease lifecycle; measure actual Nav2 and simulated motion termination",
        )
        result.update(
            {
                "authority_event": authority_event,
                "lease_revocation": revocation,
                "goal": self.node.goal_record(goal_id),
                "cancel_topic_after_revocation": cancel_topic,
                "nav2_canceling_event": canceling,
                "goal_terminal_event_during_measurement": terminal,
                "observation": observation,
                "metrics_ms": {
                    "authority_to_lease_revocation": self.elapsed_ms(
                        revocation_at, authority_event
                    ),
                    "lease_revocation_to_cancel_topic": self.elapsed_ms(
                        None if cancel_topic is None else cancel_topic["at"], revocation_at
                    ),
                    "lease_revocation_to_nav2_canceling": self.elapsed_ms(
                        None if canceling is None else canceling["at"], revocation_at
                    ),
                    "lease_revocation_to_goal_terminal": self.elapsed_ms(
                        None if terminal is None else terminal["at"], revocation_at
                    ),
                    "lease_revocation_to_robot_stop": self.elapsed_ms(
                        None if observation["robot_stop"] is None else observation["robot_stop"]["detected_at"],
                        revocation_at,
                    ),
                },
                "classification": classification,
                "observed": {
                    "goal_status": None if latest is None else STATUS_NAMES.get(latest, str(latest)),
                    "post_revocation_path_distance_m": observation["motion"]["path_distance_m"],
                    "robot_stopped": observation["robot_stop"] is not None,
                    "right_censored": observation["distance_right_censored_at_observation_end"],
                },
                "measurement_verdict": "MEASURED",
            }
        )
        return result

    def run_f2(self, trial_number: int) -> dict[str, Any]:
        ctx, setup = self.setup_trial("F2", trial_number, need_b=False)
        try:
            a = ctx.clients["A"]
            self.set_heartbeat(ctx, "A", False)
            a.state.lose_focus("F2 focus loss")
            authority = a.state.set_control(ControlState.RELEASED, "P2 explicit authority revoke")
            revocation = self.release(ctx, "A")
            return self.finish_result(
                ctx,
                self._revocation_result(
                    ctx, setup, authority, revocation, "P2_FOCUS_LOSS_TO_LEASE_RELEASE"
                ),
            )
        except Exception:
            self.cleanup_trial(ctx)
            raise

    def run_f3(self, trial_number: int) -> dict[str, Any]:
        ctx, setup = self.setup_trial("F3", trial_number, need_b=False)
        try:
            a = ctx.clients["A"]
            self.set_heartbeat(ctx, "A", False)
            a.state.enter_stopping()
            authority = a.state.set_control(ControlState.RELEASED, "STOPPING policy releases control")
            a.state.set_app(AppState.PAUSED, "application pause accompanying STOPPING")
            since = self.node.lease_event_count()
            disconnect_sent = self.recorder.emit(
                "horuslink",
                "HORUSLINK_DISCONNECT_INITIATED",
                case_id=ctx.case_id,
                trial_id=ctx.trial_id,
                actor="A",
                data={"reason": "P2 STOPPING disconnect"},
            )
            a.client.close()
            self.recorder.emit(
                "horuslink",
                "HORUSLINK_DISCONNECTED",
                case_id=ctx.case_id,
                trial_id=ctx.trial_id,
                actor="A",
                data={"both_lanes_closed": True},
            )
            observed = self.wait(
                lambda: self.node.find_lease_event("client_disconnected_release", since=since),
                5.0,
                "disconnect lease cleanup",
                ctx=ctx,
            )
            revocation = {"sent_at": disconnect_sent, "observed": observed}
            return self.finish_result(
                ctx,
                self._revocation_result(
                    ctx, setup, authority, revocation, "P2_STOPPING_TO_DISCONNECT"
                ),
            )
        except Exception:
            self.cleanup_trial(ctx)
            raise

    def run_f4(self, trial_number: int) -> dict[str, Any]:
        ctx, setup = self.setup_trial("F4", trial_number, need_b=False)
        try:
            a = ctx.clients["A"]
            self.set_heartbeat(ctx, "A", False)
            a.state.lose_focus("F4 XR control inactive")
            authority = a.state.set_control(ControlState.RELEASED, "P2 heartbeat stops for TTL expiry")
            since = self.node.lease_event_count()
            heartbeat_stopped = self.recorder.emit(
                "horuslink",
                "LEASE_HEARTBEAT_STOPPED",
                case_id=ctx.case_id,
                trial_id=ctx.trial_id,
                actor="A",
                data={"lease_ttl_ms_expected": self.args.lease_ttl_ms},
            )
            # Do not send catalog/lease traffic here: internal HORUS traffic can
            # clean an expired lease without publishing the timer's expiry event.
            observed = self.wait(
                lambda: self.node.find_lease_event("lease_expired", since=since),
                self.args.lease_ttl_ms / 1000.0 + 4.0,
                "lease TTL expiry",
                ctx=ctx,
            )
            revocation = {"sent_at": heartbeat_stopped, "observed": observed}
            return self.finish_result(
                ctx,
                self._revocation_result(
                    ctx, setup, authority, revocation, "P2_CONTROL_INACTIVE_TO_TTL_EXPIRY"
                ),
            )
        except Exception:
            self.cleanup_trial(ctx)
            raise

    def run_f5(self, trial_number: int) -> dict[str, Any]:
        ctx, setup = self.setup_trial("F5", trial_number, need_b=True)
        result = self.common_result(
            ctx,
            setup,
            "P2_AUTHORITY_HANDOFF",
            "A releases authority; B acquires and sends a distinct actual Nav2 Goal; classify preemption",
        )
        try:
            a = ctx.clients["A"]
            b = ctx.clients["B"]
            self.set_heartbeat(ctx, "A", False)
            a.state.lose_focus("F5 A loses XR focus")
            authority = a.state.set_control(ControlState.RELEASED, "F5 A authority released")
            release = self.release(ctx, "A")
            revocation_at = release["observed"]["at"]
            a_state_at_b_acquire = self.node.goal_record(ctx.goal_ids["A"])

            b.state.boot_to_focused()
            b_acquire = self.acquire(ctx, "B")
            self.set_heartbeat(ctx, "B", True)
            a_status_at_b_grant = self.node.latest_goal_status(ctx.goal_ids["A"])
            target_b = (self.args.goal_b_x, self.args.goal_b_y, self.args.goal_b_yaw)
            b_goal = self.send_goal(ctx, "B", "B", target_b, allow_reject=True)
            a_status_at_b_accept = self.node.latest_goal_status(ctx.goal_ids["A"])
            observed_goal_ids = [ctx.goal_ids["A"]]
            if b_goal["accepted"]:
                observed_goal_ids.append(ctx.goal_ids["B"])
            observation = self.observe_window(
                ctx,
                revocation_at,
                observed_goal_ids,
            )
            a_terminal = self.node.first_status_event(
                ctx.goal_ids["A"],
                TERMINAL_STATUSES,
                after_ns=b_goal["sent_at"]["monotonic_ns"],
            )
            b_latest = (
                self.node.latest_goal_status(ctx.goal_ids["B"])
                if b_goal["accepted"]
                else None
            )
            if not b_goal["accepted"]:
                category = "A_OLD_CONTINUES_B_REJECTED"
            elif a_terminal is not None and a_terminal["status"] == GoalStatus.STATUS_ABORTED and b_latest in ACTIVE_STATUSES:
                category = "C_B_PREEMPTS_A"
            elif a_terminal is not None and a_terminal["status"] == GoalStatus.STATUS_CANCELED:
                category = "B_OLD_GOAL_AUTOMATICALLY_CANCELED"
            elif a_terminal is None and b_latest in ACTIVE_STATUSES:
                category = "D_UNEXPECTED_PERSISTENT_NONTERMINAL_OVERLAP"
            else:
                category = "D_OTHER_UNEXPECTED_TRANSITION"

            result.update(
                {
                    "authority_event": authority,
                    "a_lease_release": release,
                    "b_lease_acquire": b_acquire,
                    "b_goal": b_goal,
                    "a_goal_state_before_b_acquire": a_state_at_b_acquire,
                    "a_goal_status_at_b_grant": (
                        None if a_status_at_b_grant is None else STATUS_NAMES.get(a_status_at_b_grant, str(a_status_at_b_grant))
                    ),
                    "a_goal_status_at_b_accept": (
                        None if a_status_at_b_accept is None else STATUS_NAMES.get(a_status_at_b_accept, str(a_status_at_b_accept))
                    ),
                    "a_goal": self.node.goal_record(ctx.goal_ids["A"]),
                    "b_goal_record": (
                        self.node.goal_record(ctx.goal_ids["B"])
                        if b_goal["accepted"]
                        else None
                    ),
                    "a_terminal_after_b_goal": a_terminal,
                    "observation": observation,
                    "metrics_ms": {
                        "authority_to_a_lease_release": self.elapsed_ms(revocation_at, authority),
                        "a_release_to_b_lease_grant": self.elapsed_ms(
                            b_acquire["observed"]["at"], revocation_at
                        ),
                        "b_goal_send_to_accept": self.elapsed_ms(
                            b_goal.get("accepted_observed_at"), b_goal["sent_at"]
                        ),
                        "a_release_to_b_goal_accept": self.elapsed_ms(
                            b_goal.get("accepted_observed_at"), revocation_at
                        ),
                        "b_goal_send_to_a_terminal": self.elapsed_ms(
                            None if a_terminal is None else a_terminal["at"], b_goal["sent_at"]
                        ),
                    },
                    "classification": category,
                    "observed": {
                        "a_terminal": None if a_terminal is None else a_terminal["status_name"],
                        "b_status": None if b_latest is None else STATUS_NAMES.get(b_latest, str(b_latest)),
                        "path_distance_after_a_release_m": observation["motion"]["path_distance_m"],
                    },
                    "interpretation_guardrail": (
                        "brief status overlap can be Nav2 pending-goal transition; A ABORTED followed "
                        "by B EXECUTING is preemption, unlike dummy-server simultaneous execution"
                    ),
                    "measurement_verdict": "MEASURED",
                }
            )
            return self.finish_result(ctx, result)
        except Exception:
            self.cleanup_trial(ctx)
            raise

    def run_f6(self, trial_number: int) -> dict[str, Any]:
        ctx, setup = self.setup_trial("F6", trial_number, need_b=True)
        result = self.common_result(
            ctx,
            setup,
            "SESSION_EPOCH_CAPABILITY_PROBE",
            "measure whether stale logical session/epoch metadata is expressible and enforced",
        )
        try:
            a = ctx.clients["A"]
            b = ctx.clients["B"]
            self.set_heartbeat(ctx, "A", False)
            a.state.lose_focus("F6 old session focus loss")
            authority = a.state.set_control(ControlState.RELEASED, "F6 old control released")
            a_release = self.release(ctx, "A")
            b.state.boot_to_focused()
            b_acquire = self.acquire(ctx, "B")
            self.set_heartbeat(ctx, "B", True)

            stale_while_b = self.send_goal(
                ctx,
                "A",
                "STALE_WHILE_B_HOLDS",
                (self.args.goal_b_x, self.args.goal_b_y, self.args.goal_b_yaw),
                expect_accept=False,
                timeout_s=self.args.stale_probe_wait_sec,
            )

            b_release = self.release(ctx, "B")
            a.client.close()
            self.recorder.emit(
                "horuslink",
                "HORUSLINK_DISCONNECTED",
                case_id=ctx.case_id,
                trial_id=ctx.trial_id,
                actor="A",
                data={"old_wire_session_closed": True},
            )
            stale = self.new_client(ctx, "STALE", ctx.logical_a_session)
            stale.state.boot_to_focused()
            stale_acquire = self.acquire(ctx, "STALE", suffix="stale-session-acquire")
            self.set_heartbeat(ctx, "STALE", True)
            stale_after = self.send_goal(
                ctx,
                "STALE",
                "STALE_RECONNECTED",
                (self.args.goal_b_x, self.args.goal_b_y, self.args.goal_b_yaw),
            )
            stale_goal_id = stale_after["goal_uuid"]
            ctx.goal_ids["STALE_RECONNECTED"] = stale_goal_id
            observation_origin = stale_acquire["observed"]["at"]
            observation = self.observe_window(
                ctx,
                observation_origin,
                [ctx.goal_ids["A"], stale_goal_id],
            )
            result.update(
                {
                    "authority_event": authority,
                    "old_session_release": a_release,
                    "current_b_acquire": b_acquire,
                    "stale_goal_while_b_holds": stale_while_b,
                    "b_release": b_release,
                    "stale_logical_session_reacquire": stale_acquire,
                    "stale_reconnected_goal": stale_after,
                    "observation": observation,
                    "epoch_model": {
                        "goal_command_epoch_field": "ABSENT",
                        "lease_version_is_stable_epoch": False,
                        "lease_version_note": "global/version counter changes on heartbeat and is not bound to Goal commands",
                        "cryptographic_replay_test": "NOT_EXPRESSIBLE_IN_PUBLIC_COMMAND_SCHEMA",
                    },
                    "classification": "EPOCH_NOT_EXPRESSIBLE_STALE_LOGICAL_SESSION_REACCEPTED",
                    "observed": {
                        "stale_goal_blocked_while_b_holds": not stale_while_b["accepted"],
                        "blocking_basis": "HorusLink connection ownership, not epoch binding",
                        "stale_logical_session_reacquired_after_b_release": True,
                        "stale_reconnected_goal_accepted": stale_after["accepted"],
                    },
                    "interpretation_guardrail": (
                        "this is an epoch capability/admission probe, not proof of cryptographic "
                        "session replay or a real XR session resurrection attack"
                    ),
                    "measurement_verdict": "MEASURED",
                }
            )
            return self.finish_result(ctx, result)
        except Exception:
            self.cleanup_trial(ctx)
            raise

    def finish_result(self, ctx: TrialContext, result: dict[str, Any]) -> dict[str, Any]:
        result["measurement_completed_at"] = self.recorder.stamp()
        result["timeline_seq_end_measurement"] = self.recorder.sequence
        result["cleanup"] = self.cleanup_trial(ctx)
        result["timeline_seq_end"] = self.recorder.sequence
        result["trial_complete"] = bool(result["cleanup"].get("clean"))
        result["heartbeat_counts"] = {
            label: runtime.heartbeat_count for label, runtime in ctx.clients.items()
        }
        return result

    def cleanup_trial(self, ctx: TrialContext) -> dict[str, Any]:
        if ctx.cleanup:
            return ctx.cleanup
        started = self.recorder.emit(
            "probe",
            "TEST_CLEANUP_BEGIN",
            case_id=ctx.case_id,
            trial_id=ctx.trial_id,
            data={"measurement_event": False},
        )
        errors: list[str] = []
        official_b_cancel: dict[str, Any] | None = None
        for runtime in ctx.clients.values():
            runtime.heartbeat_enabled = False

        # In F5, try B's ordinary path after primary measurement.  This is
        # cleanup evidence for the adapter's latest-handle integrity, not part
        # of the handoff classification.  Direct cancel-all remains fallback.
        if ctx.case_id == "F5" and "B" in ctx.clients and ctx.clients["B"].client.connected:
            try:
                sent = self.recorder.emit(
                    "horuslink",
                    "POST_MEASUREMENT_B_CANCEL_SENT",
                    case_id=ctx.case_id,
                    trial_id=ctx.trial_id,
                    actor="B",
                    data={"measurement_event": False},
                )
                ctx.clients["B"].client.publish_cancel()
                b_id = ctx.goal_ids.get("B")
                terminal = None
                if b_id is not None:
                    try:
                        terminal = self.wait(
                            lambda: self.node.first_status_event(
                                b_id,
                                TERMINAL_STATUSES,
                                after_ns=sent["monotonic_ns"],
                            ),
                            2.0,
                            "post-measurement B official cancel",
                        )
                    except Exception:
                        terminal = None
                official_b_cancel = {
                    "sent_at": sent,
                    "terminal": terminal,
                    "worked": bool(
                        terminal is not None
                        and terminal["status"] == GoalStatus.STATUS_CANCELED
                    ),
                }
            except Exception as exc:
                official_b_cancel = {"worked": False, "error": f"{type(exc).__name__}: {exc}"}

        direct_cancel = self.node.cancel_all_for_cleanup(self.wait)
        try:
            self.wait(
                lambda: not any(
                    self.node.latest_goal_status(identifier) in ACTIVE_STATUSES
                    for identifier in set(ctx.goal_ids.values())
                ),
                10.0,
                "all trial goals terminal after cleanup",
            )
        except Exception as exc:
            errors.append(f"goal cleanup: {type(exc).__name__}: {exc}")

        for label, runtime in list(ctx.clients.items()):
            if not runtime.client.connected:
                continue
            try:
                runtime.client.release(f"{ctx.trial_id}-{label}-cleanup-release")
            except Exception as exc:
                errors.append(f"{label} release: {type(exc).__name__}: {exc}")
        time.sleep(0.1)
        for label, runtime in list(ctx.clients.items()):
            try:
                runtime.client.close()
            except Exception as exc:
                errors.append(f"{label} close: {type(exc).__name__}: {exc}")

        stop: dict[str, Any] | None = None
        goals_active_before_stop_check = any(
            self.node.latest_goal_status(identifier) in ACTIVE_STATUSES
            for identifier in set(ctx.goal_ids.values())
        )
        if ctx.measurement_robot_stop is not None and not goals_active_before_stop_check:
            stop = {
                **copy.deepcopy(ctx.measurement_robot_stop),
                "basis": "robot stop already established during measurement",
                "already_stopped_before_cleanup": True,
            }
        else:
            try:
                stop = self.wait(
                    lambda: self.node.robot_stop_candidate(started["monotonic_ns"]),
                    8.0,
                    "simulated robot stopped after cleanup",
                )
            except Exception as exc:
                errors.append(f"robot stop: {type(exc).__name__}: {exc}")
        active_after = [
            identifier
            for identifier in set(ctx.goal_ids.values())
            if self.node.latest_goal_status(identifier) in ACTIVE_STATUSES
        ]
        if active_after:
            errors.append(f"active goals after cleanup: {active_after}")
        completed = self.recorder.emit(
            "probe",
            "TEST_CLEANUP_END",
            case_id=ctx.case_id,
            trial_id=ctx.trial_id,
            data={"errors": errors, "active_goal_ids": active_after},
        )
        ctx.cleanup = {
            "started_at": started,
            "completed_at": completed,
            "post_measurement_b_official_cancel": official_b_cancel,
            "direct_action_cancel_all": direct_cancel,
            "robot_stop": stop,
            "active_goal_ids_after": active_after,
            "errors": errors,
            "clean": not errors and not active_after,
        }
        self.node.set_trial(None, None)
        return ctx.cleanup

    def run_case(self, case_id: str, trial_number: int) -> dict[str, Any]:
        self.progress(f"[XR Nav2 probe] {case_id} trial {trial_number}/{self.args.trials}")
        try:
            method = getattr(self, f"run_{case_id.lower()}")
            result = method(trial_number)
        except Exception as exc:
            result = {
                "case_id": case_id,
                "trial_id": f"{case_id}-T{trial_number:02d}",
                "trial_number": trial_number,
                "trial_complete": False,
                "measurement_verdict": "ERROR",
                "classification": "HARNESS_ERROR",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            }
        self.results.append(result)
        target = self.handoff_stream if case_id == "F5" else self.revocation_stream
        target.write(json.dumps(json_safe(result), sort_keys=True) + "\n")
        return result

    def preflight(self) -> dict[str, Any]:
        self.progress("[XR Nav2 probe] actual Nav2/HORUS preflight")
        self.wait(
            self.node.action_server_ready,
            self.args.readiness_timeout_sec,
            "actual Nav2 NavigateToPose server",
        )

        # The action endpoint can appear before lifecycle activation completes.
        # Wait for every named server rather than treating that startup race as
        # an experiment failure.  Missing services are also not silently
        # accepted: the returned snapshot must contain available+active for all.
        latest_lifecycle: dict[str, Any] = {}

        def all_lifecycle_nodes_active() -> dict[str, Any] | None:
            nonlocal latest_lifecycle
            try:
                latest_lifecycle = self.node.lifecycle_states(self.wait)
            except Exception:
                return None
            if all(
                latest_lifecycle.get(name, {}).get("available")
                and latest_lifecycle.get(name, {}).get("active")
                for name in self.args.lifecycle_nodes
            ):
                return latest_lifecycle
            return None

        try:
            lifecycle = self.wait(
                all_lifecycle_nodes_active,
                self.args.readiness_timeout_sec,
                "all required Nav2 lifecycle nodes active",
            )
        except Exception as exc:
            raise RuntimeError(
                f"Nav2 lifecycle nodes did not all become active: {latest_lifecycle}"
            ) from exc
        registration = self.node.register_robot(self.wait)
        self.robot_id = registration["robot_id"]
        self.node.publish_initial_pose(
            self.args.start_x,
            self.args.start_y,
            self.args.start_yaw,
        )
        pose = self.wait(
            lambda: self.node.map_pose(),
            self.args.readiness_timeout_sec,
            "map to simulated robot TF",
        )
        goal_a_free = self.node.target_is_free(self.args.goal_a_x, self.args.goal_a_y)
        goal_b_free = self.node.target_is_free(self.args.goal_b_x, self.args.goal_b_y)
        for label, check in (("A", goal_a_free), ("B", goal_b_free)):
            if check.get("checked") and not check.get("free"):
                raise RuntimeError(f"Goal {label} target is not free in map: {check}")
        graph = {
            "node_names": sorted(
                f"{namespace.rstrip('/')}/{name}" if namespace != "/" else f"/{name}"
                for name, namespace in self.node.get_node_names_and_namespaces()
            ),
            "nav2_action": self.args.nav2_action,
            "cmd_topic": self.args.cmd_topic,
            "odom_topic": self.args.odom_topic,
        }
        event = self.recorder.emit(
            "probe",
            "PREFLIGHT_COMPLETE",
            data={
                "lifecycle": lifecycle,
                "registration": registration,
                "map_pose": pose,
                "goal_a_free": goal_a_free,
                "goal_b_free": goal_b_free,
                "graph": graph,
            },
        )
        return {
            "completed_at": event,
            "lifecycle": lifecycle,
            "robot_registration": registration,
            "map_pose": pose,
            "goal_a_free": goal_a_free,
            "goal_b_free": goal_b_free,
            "graph": graph,
            "actual_nav2_action_server_ready": True,
            "probe_creates_action_server": False,
        }

    def close(self) -> None:
        self.revocation_stream.flush()
        self.handoff_stream.flush()
        self.revocation_stream.close()
        self.handoff_stream.close()


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    aggregate: dict[str, Any] = {}
    for case_id in sorted({str(result["case_id"]) for result in results}):
        selected = [result for result in results if result["case_id"] == case_id]
        complete = [result for result in selected if result.get("trial_complete")]
        outcomes: dict[str, int] = {}
        distances: list[float] = []
        for result in complete:
            classification = str(result.get("classification", "UNKNOWN"))
            outcomes[classification] = outcomes.get(classification, 0) + 1
            observation = result.get("observation")
            if isinstance(observation, dict):
                motion = observation.get("motion", {})
                if isinstance(motion.get("path_distance_m"), (int, float)):
                    distances.append(float(motion["path_distance_m"]))
            elif case_id == "F0":
                motion = result.get("post_cancel_motion", {})
                if isinstance(motion.get("path_distance_m"), (int, float)):
                    distances.append(float(motion["path_distance_m"]))
        aggregate[case_id] = {
            "trials_requested": len(selected),
            "trials_complete": len(complete),
            "trials_error": len(selected) - len(complete),
            "outcomes": outcomes,
            "path_distance_m": (
                None
                if not distances
                else {
                    "min": round(min(distances), 6),
                    "median": round(statistics.median(distances), 6),
                    "max": round(max(distances), 6),
                }
            ),
        }
    return aggregate


def write_summary(path: str, report: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# XR Mock to HORUS to Nav2 Evidence Summary",
        "",
        f"- Run ID: `{report['run_id']}`",
        f"- HORUS revision: `{report['environment']['horus_revision']}`",
        "- Architecture: Mock OpenXR-style lifecycle -> actual HorusLink -> actual HORUS -> actual Nav2 -> nav2_loopback_sim",
        "- Physical XR hardware: `false`",
        "- Physical robot: `false`",
        "- Distance basis: actual simulator `/odom` polyline, not a constant-speed estimate",
        "",
        "| Case | Complete | Outcomes | Distance min/median/max (m) |",
        "|---|---:|---|---|",
    ]
    for case_id, item in report.get("aggregate", {}).items():
        outcomes = ", ".join(f"`{key}`={value}" for key, value in item["outcomes"].items())
        distance = item.get("path_distance_m")
        if distance is None:
            rendered_distance = "-"
        else:
            rendered_distance = f"{distance['min']:.6f} / {distance['median']:.6f} / {distance['max']:.6f}"
        lines.append(
            f"| `{case_id}` | `{item['trials_complete']}/{item['trials_requested']}` | {outcomes or '-'} | {rendered_distance} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation guardrails",
            "",
            "- Mock transitions reproduce OpenXR-style semantics; they are not real OpenXR or Quest events.",
            "- Nav2 is real software, but loopback odometry is simulated and does not establish physical-robot motion.",
            "- F1 is an event-only policy and is not by itself a vulnerability result.",
            "- F6 is an epoch-capability probe because public Goal commands carry no session/lease epoch.",
            "",
            "## Evidence",
            "",
            f"- Timeline: `{report['evidence']['timeline_log']}`",
            f"- Revocation: `{report['evidence']['revocation_log']}`",
            f"- Handoff: `{report['evidence']['handoff_log']}`",
            "",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")


def parse_cases(value: str) -> list[str]:
    cases = [item.strip().upper() for item in value.split(",") if item.strip()]
    valid = {f"F{index}" for index in range(7)}
    unknown = [item for item in cases if item not in valid]
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown cases: {','.join(unknown)}")
    if not cases:
        raise argparse.ArgumentTypeError("at least one case is required")
    return cases


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mock XR authority lifecycle over actual HorusLink/HORUS/Nav2 simulation"
    )
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--cases", type=parse_cases, default=parse_cases("F0,F1,F2,F3,F4,F5,F6"))
    parser.add_argument("--revocation-delay-sec", type=float, default=2.0)
    parser.add_argument("--observation-sec", type=float, default=5.0)
    parser.add_argument("--lease-ttl-ms", type=int, default=1200)
    parser.add_argument("--heartbeat-interval-sec", type=float, default=0.30)
    parser.add_argument("--readiness-timeout-sec", type=float, default=45.0)
    parser.add_argument("--goal-accept-timeout-sec", type=float, default=12.0)
    parser.add_argument("--motion-timeout-sec", type=float, default=25.0)
    parser.add_argument("--stale-probe-wait-sec", type=float, default=1.0)
    parser.add_argument("--robot", default=ROBOT)
    parser.add_argument("--nav2-action", default=DEFAULT_NAV2_ACTION)
    parser.add_argument("--cmd-topic", default=DEFAULT_CMD_TOPIC)
    parser.add_argument("--odom-topic", default=DEFAULT_ODOM_TOPIC)
    parser.add_argument("--initialpose-topic", default=DEFAULT_INITIALPOSE_TOPIC)
    parser.add_argument("--map-topic", default=DEFAULT_MAP_TOPIC)
    parser.add_argument("--map-frame", default="map")
    parser.add_argument("--base-frame", default="base_footprint")
    parser.add_argument("--start-x", type=float, default=-2.0)
    parser.add_argument("--start-y", type=float, default=-0.5)
    parser.add_argument("--start-yaw", type=float, default=0.0)
    parser.add_argument("--goal-a-x", type=float, default=1.5)
    parser.add_argument("--goal-a-y", type=float, default=-0.5)
    parser.add_argument("--goal-a-yaw", type=float, default=0.0)
    parser.add_argument("--goal-b-x", type=float, default=-1.5)
    parser.add_argument("--goal-b-y", type=float, default=1.0)
    parser.add_argument("--goal-b-yaw", type=float, default=math.pi)
    parser.add_argument("--target-clearance-m", type=float, default=0.15)
    parser.add_argument("--reset-pose-tolerance-m", type=float, default=0.20)
    parser.add_argument("--motion-confirm-distance-m", type=float, default=0.03)
    parser.add_argument("--cmd-stop-threshold", type=float, default=0.01)
    parser.add_argument("--stop-hold-sec", type=float, default=0.50)
    parser.add_argument("--stop-odom-epsilon-m", type=float, default=0.005)
    parser.add_argument(
        "--lifecycle-nodes",
        type=lambda value: [item for item in value.split(",") if item],
        default=["controller_server", "planner_server", "behavior_server", "bt_navigator"],
    )
    parser.add_argument("--timeline-log", default="/tmp/xr_mock_timeline.log")
    parser.add_argument("--revocation-log", default="/tmp/nav2_revocation_runtime.log")
    parser.add_argument("--handoff-log", default="/tmp/nav2_handoff_runtime.log")
    parser.add_argument("--summary-md", default="/tmp/xr_nav2_feasibility_summary.md")
    parser.add_argument("--horus-revision", default=FIXED_HORUS_REVISION)
    args = parser.parse_args(argv)
    if args.trials < 1:
        parser.error("--trials must be at least 1")
    if args.revocation_delay_sec <= 0 or args.observation_sec < 0.5:
        parser.error("revocation delay must be positive and observation must be >= 0.5")
    if args.lease_ttl_ms < 500:
        parser.error("--lease-ttl-ms must be >= HORUS minimum 500 ms")
    if args.heartbeat_interval_sec * 1000 >= args.lease_ttl_ms:
        parser.error("heartbeat interval must be shorter than lease TTL")
    return args


def emit_report(report: dict[str, Any]) -> None:
    print("XR_NAV2_FEASIBILITY_JSON_BEGIN")
    print(
        json.dumps(
            json_safe(
                {
                    "run_id": report.get("run_id"),
                    "measurement_valid": report.get("measurement_valid"),
                    "baseline_valid": report.get("baseline_valid"),
                    "fatal_error": report.get("fatal_error"),
                    "aggregate": report.get("aggregate", {}),
                }
            ),
            indent=2,
            sort_keys=True,
        )
    )
    print("XR_NAV2_FEASIBILITY_JSON_END")


def main() -> int:
    rosless_argv = remove_ros_args(args=sys.argv)[1:]
    args = parse_args(rosless_argv)
    run_id = datetime.now(timezone.utc).strftime("xr-nav2-%Y%m%dT%H%M%SZ")
    recorder = TimelineRecorder(args.timeline_log, run_id)
    started = recorder.emit(
        "probe",
        "RUN_BEGIN",
        data={"cases": args.cases, "trials": args.trials},
    )
    report: dict[str, Any] = {
        "schema": "xr-horus-nav2-feasibility/v1",
        "run_id": run_id,
        "started_at": started,
        "environment": {
            "horus_revision": args.horus_revision,
            "mock_xr": True,
            "actual_openxr_runtime": False,
            "actual_horuslink": True,
            "actual_horus_bridge_backend": True,
            "actual_nav2": True,
            "simulation": "nav2_loopback_sim",
            "simulation_characterization": "frictionless differential-drive odometry from consumed cmd_vel",
            "physical_robot": False,
            "physical_xr_hardware": False,
        },
        "openxr_semantics": {
            "FOCUSED": "visible and eligible to receive XR input",
            "VISIBLE": "visible but not eligible to receive XR input",
            "STOPPING": "application should stop frame loop and call xrEndSession",
            "EXITING": "application should end XR experience",
            "LOSS_PENDING": "session should be destroyed and may be recreated",
            "mock_not_runtime_event": True,
            "policy_p1": "XR input state changes; heartbeat/lease/connection intentionally remain",
            "policy_p2": "XR authority transition explicitly propagates through release, disconnect, or TTL",
        },
        "configuration": {
            "cases": args.cases,
            "trials_per_case": args.trials,
            "revocation_delay_sec_after_motion_confirmation": args.revocation_delay_sec,
            "observation_sec": args.observation_sec,
            "lease_ttl_ms": args.lease_ttl_ms,
            "start_pose": {"x": args.start_x, "y": args.start_y, "yaw": args.start_yaw},
            "goal_a": {"x": args.goal_a_x, "y": args.goal_a_y, "yaw": args.goal_a_yaw},
            "goal_b": {"x": args.goal_b_x, "y": args.goal_b_y, "yaw": args.goal_b_yaw},
        },
        "evidence": {
            "timeline_log": str(Path(args.timeline_log).resolve()),
            "revocation_log": str(Path(args.revocation_log).resolve()),
            "handoff_log": str(Path(args.handoff_log).resolve()),
            "summary_md": str(Path(args.summary_md).resolve()),
        },
        "trials": [],
    }

    rclpy.init(args=sys.argv)
    node = Nav2Observer(args, recorder)
    executor = MultiThreadedExecutor(num_threads=12)
    executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    runner = XRNav2TrialRunner(node, recorder, args)
    unregistered = False
    exit_code = 1
    try:
        report["preflight"] = runner.preflight()
        for case_id in args.cases:
            for trial_number in range(1, args.trials + 1):
                report["trials"].append(runner.run_case(case_id, trial_number))
        report["aggregate"] = aggregate_results(report["trials"])
        errors = [trial for trial in report["trials"] if not trial.get("trial_complete")]
        f0 = [trial for trial in report["trials"] if trial["case_id"] == "F0"]
        baseline_valid: bool | None
        if "F0" not in args.cases:
            baseline_valid = None
        else:
            baseline_valid = bool(f0) and all(
                trial.get("classification") == "EXPLICIT_CANCEL_SAFE"
                and trial.get("trial_complete")
                for trial in f0
            )
        report["baseline_valid"] = baseline_valid
        report["measurement_valid"] = not errors and baseline_valid is not False
        if runner.robot_id is not None:
            report["robot_unregistration"] = node.unregister_robot(runner.robot_id, runner.wait)
            unregistered = True
        report["completed_at"] = recorder.emit(
            "probe",
            "RUN_COMPLETE",
            data={
                "measurement_valid": report["measurement_valid"],
                "trial_errors": len(errors),
            },
        )
        write_summary(args.summary_md, report)
        emit_report(report)
        if errors:
            exit_code = 1
        elif baseline_valid is False:
            exit_code = 2
        else:
            exit_code = 0
    except Exception as exc:
        report["fatal_error"] = f"{type(exc).__name__}: {exc}"
        report["fatal_traceback"] = traceback.format_exc()
        report["measurement_valid"] = False
        report["completed_at"] = recorder.emit(
            "probe",
            "RUN_FATAL_ERROR",
            data={"error": report["fatal_error"]},
        )
        report["aggregate"] = aggregate_results(report.get("trials", []))
        write_summary(args.summary_md, report)
        emit_report(report)
        exit_code = 1
    finally:
        if runner.robot_id is not None and not unregistered:
            try:
                node.unregister_robot(runner.robot_id, runner.wait)
            except Exception:
                pass
        runner.close()
        executor.shutdown(timeout_sec=4.0)
        node.destroy_observer()
        rclpy.shutdown()
        spin_thread.join(timeout=4.0)
        recorder.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
