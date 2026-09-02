#!/usr/bin/env python3
"""Long-running HORUS action/revocation probe.

The probe keeps the real fixed HORUS path under test::

    HorusLink client -> horus_unity_bridge -> horus_backend/Nav2 adapter
    -> local dummy NavigateToPose action server

Only the final action server is synthetic.  It models motion at a constant
``0.1 m/s`` by default; reported distances are simulated and must not be
described as physical robot movement.

The existing ``horus_runtime_probe`` module supplies the already-tested
HorusLink framing/client implementation.  This file adds a long-running action
server, explicit cancel baseline, independent repeated revocation trials, and
the A/B handoff measurement.  It does not patch a HORUS repository.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionServer
from rclpy.action.server import CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.serialization import serialize_message
from std_msgs.msg import String
from horus_interfaces.srv import UnregisterRobot

from horus_runtime_probe import (
    CATALOG_TOPIC,
    GOAL_TOPIC,
    LEASE_TOPIC,
    ROBOT,
    STATE_TOPIC,
    HorusLinkClient,
    register_robot,
)


FIXED_HORUS_REVISION = "eca75cbf559f09ff793d8993338b2f1ffed1adfd"
CANCEL_TOPIC = f"/{ROBOT}/goal_cancel"
ACTION_TOPIC = f"/{ROBOT}/navigate_to_pose"
DEFAULT_CHECKPOINTS = (0.5, 1.0, 3.0, 5.0, 10.0)
TERMINAL_STATES = {
    "CANCELED",
    "SUCCEEDED_NATURAL",
    "ABORTED_BY_TEST_CLEANUP",
    "ABORTED_BY_SHUTDOWN",
    "EXECUTION_EXCEPTION",
}


def timestamp() -> dict[str, Any]:
    """Return paired UTC wall-clock and process-monotonic timestamps."""

    monotonic_s = time.monotonic()
    wall = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    return {
        "wall_utc": wall.replace("+00:00", "Z"),
        "monotonic_s": round(monotonic_s, 6),
    }


def elapsed(later: dict[str, Any] | None, earlier: dict[str, Any] | None) -> float | None:
    if later is None or earlier is None:
        return None
    return round(float(later["monotonic_s"]) - float(earlier["monotonic_s"]), 6)


def wait_until(
    predicate: Callable[[], Any],
    timeout_s: float,
    description: str,
    *,
    tick: Callable[[], None] | None = None,
) -> Any:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        if tick is not None:
            tick()
        time.sleep(0.025)
    value = predicate()
    if value:
        return value
    raise RuntimeError(f"timeout waiting for {description}")


def goal_uuid(goal_handle: Any) -> str:
    return bytes(goal_handle.goal_id.uuid).hex()


def is_active_state(state: str | None) -> bool:
    return state is not None and state not in TERMINAL_STATES


def unregister_robot(node: "LongActionProbeNode", robot_id: str) -> dict[str, Any]:
    """Remove the backend adapter so sequential suite invocations stay isolated."""

    client = node.create_client(
        UnregisterRobot,
        "/horus/unregister_robot",
        callback_group=node.callback_group,
    )
    try:
        if not client.wait_for_service(timeout_sec=5.0):
            raise RuntimeError("HORUS backend unregister_robot service unavailable")
        request = UnregisterRobot.Request()
        request.robot_id = robot_id
        sent_at = timestamp()
        future = client.call_async(request)
        wait_until(future.done, 5.0, "unregister_robot response")
        response = future.result()
        if response is None or not response.success:
            detail = "no response" if response is None else response.error_message
            raise RuntimeError(f"robot unregistration failed: {detail}")
        return {"success": True, "robot_id": robot_id, "sent_at": sent_at, "completed_at": timestamp()}
    finally:
        node.destroy_client(client)


class LongActionHorusClient(HorusLinkClient):
    """Small extension of the previously validated HorusLink test client."""

    def heartbeat(
        self,
        request_id: str,
        app_id: str,
        role: str,
        session_id: str,
    ) -> None:
        self.publish_json_string(
            LEASE_TOPIC,
            {
                "request_id": request_id,
                "robot_name": ROBOT,
                "app_id": app_id,
                "role": role,
                "session_id": session_id,
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
        # This is an ordinary ROS topic through TopicManager, unlike the
        # bridge-internal lease JSON topics, so strip the CDR encapsulation.
        self.publish_serialized(
            CANCEL_TOPIC,
            bytes(serialize_message(message)),
            include_cdr_header=False,
        )

    def publish_protected_catalog(self) -> None:
        self.publish_json_string(
            CATALOG_TOPIC,
            {
                "role": "host",
                "op": "snapshot",
                "session_id": "horus-long-action-probe",
                "robots": [
                    {
                        "robot_name": ROBOT,
                        "protected_topics": [GOAL_TOPIC, CANCEL_TOPIC],
                    }
                ],
            },
        )

    @property
    def connected(self) -> bool:
        return self.realtime is not None and self.bulk is not None


class LongActionProbeNode(Node):
    """Dummy long-running Nav2 server plus timestamped ROS observations."""

    def __init__(
        self,
        *,
        goal_duration_s: float,
        feedback_period_s: float,
        simulated_speed_mps: float,
    ) -> None:
        super().__init__("horus_long_action_probe")
        self.goal_duration_s = goal_duration_s
        self.feedback_period_s = feedback_period_s
        self.simulated_speed_mps = simulated_speed_mps
        self.callback_group = ReentrantCallbackGroup()
        self.lock = threading.RLock()
        self.stop_all = threading.Event()
        self.goal_records: dict[str, dict[str, Any]] = {}
        self.cleanup_events: dict[str, threading.Event] = {}
        self.lease_events: list[dict[str, Any]] = []
        self.concurrency_events: list[dict[str, Any]] = []

        state_qos = QoSProfile(depth=100)
        state_qos.reliability = ReliabilityPolicy.RELIABLE
        state_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.create_subscription(String, STATE_TOPIC, self._on_lease_state, state_qos)
        self.direct_goal_publisher = self.create_publisher(PoseStamped, GOAL_TOPIC, 10)

        self.action_server = ActionServer(
            self,
            NavigateToPose,
            ACTION_TOPIC,
            execute_callback=self._execute_goal,
            goal_callback=self._accept_goal,
            handle_accepted_callback=self._handle_accepted_goal,
            cancel_callback=self._accept_cancel,
            callback_group=self.callback_group,
        )

    def _on_lease_state(self, message: String) -> None:
        try:
            payload = json.loads(message.data)
        except json.JSONDecodeError:
            return
        with self.lock:
            self.lease_events.append({"received_at": timestamp(), "payload": payload})

    def _accept_goal(self, _request: NavigateToPose.Goal) -> GoalResponse:
        return GoalResponse.ACCEPT

    def _record_concurrency_locked(self, reason: str) -> None:
        active_ids = sorted(
            goal_id
            for goal_id, record in self.goal_records.items()
            if is_active_state(record.get("state"))
        )
        self.concurrency_events.append(
            {
                "at": timestamp(),
                "reason": reason,
                "active_goal_count": len(active_ids),
                "active_goal_ids": active_ids,
            }
        )

    def _handle_accepted_goal(self, goal_handle: Any) -> None:
        accepted_at = timestamp()
        identifier = goal_uuid(goal_handle)
        target_x = float(goal_handle.request.pose.pose.position.x)
        with self.lock:
            self.cleanup_events[identifier] = threading.Event()
            self.goal_records[identifier] = {
                "goal_id": identifier,
                "target_marker_x": round(target_x, 6),
                "accepted_at": accepted_at,
                "execute_started_at": None,
                "terminal_at": None,
                "state": "ACCEPTED",
                "terminal_reason": None,
                "state_history": [{"state": "ACCEPTED", "at": accepted_at}],
                "cancel_callbacks": [],
                "feedback_count": 0,
                "first_feedback_at": None,
                "last_feedback_at": None,
                "last_feedback_navigation_s": 0.0,
                "last_feedback_simulated_progress_m": 0.0,
                "feedback_errors": [],
                "test_cleanup_requested_at": None,
            }
            self._record_concurrency_locked("goal_accepted")
        goal_handle.execute()

    def _accept_cancel(self, goal_handle: Any) -> CancelResponse:
        callback_at = timestamp()
        identifier = goal_uuid(goal_handle)
        with self.lock:
            record = self.goal_records.get(identifier)
            if record is not None:
                record["cancel_callbacks"].append(
                    {
                        "callback_at": callback_at,
                        "cancel_goal_id": identifier,
                    }
                )
                if is_active_state(record.get("state")):
                    record["state"] = "CANCEL_REQUEST_ACCEPTED"
                    record["state_history"].append(
                        {"state": "CANCEL_REQUEST_ACCEPTED", "at": callback_at}
                    )
                self._record_concurrency_locked("cancel_callback")
        return CancelResponse.ACCEPT

    def _set_execute_started(self, identifier: str) -> dict[str, Any]:
        started_at = timestamp()
        with self.lock:
            record = self.goal_records[identifier]
            record["execute_started_at"] = started_at
            record["state"] = "EXECUTING"
            record["state_history"].append({"state": "EXECUTING", "at": started_at})
            self._record_concurrency_locked("execute_started")
            return started_at

    def _set_terminal(
        self,
        identifier: str,
        state: str,
        reason: str,
        execute_started_at: dict[str, Any],
    ) -> None:
        terminal_at = timestamp()
        active_duration_s = elapsed(terminal_at, execute_started_at)
        with self.lock:
            record = self.goal_records[identifier]
            record["terminal_at"] = terminal_at
            record["state"] = state
            record["terminal_reason"] = reason
            record["active_duration_s"] = active_duration_s
            record["simulated_distance_at_terminal_m"] = round(
                self.simulated_speed_mps * max(0.0, active_duration_s or 0.0), 6
            )
            record["state_history"].append(
                {"state": state, "reason": reason, "at": terminal_at}
            )
            self._record_concurrency_locked("goal_terminal")

    def _publish_feedback(
        self,
        goal_handle: Any,
        identifier: str,
        navigation_s: float,
    ) -> None:
        feedback = NavigateToPose.Feedback()
        feedback.current_pose.header.frame_id = "map"
        feedback.current_pose.header.stamp = self.get_clock().now().to_msg()
        progress_m = self.simulated_speed_mps * navigation_s
        feedback.current_pose.pose.position.x = progress_m
        feedback.current_pose.pose.orientation.w = 1.0
        total_distance_m = self.simulated_speed_mps * self.goal_duration_s
        feedback.distance_remaining = max(0.0, total_distance_m - progress_m)
        feedback.number_of_recoveries = 0
        navigation_sec = int(navigation_s)
        feedback.navigation_time.sec = navigation_sec
        feedback.navigation_time.nanosec = int((navigation_s - navigation_sec) * 1_000_000_000)
        remaining_s = max(0.0, self.goal_duration_s - navigation_s)
        remaining_sec = int(remaining_s)
        feedback.estimated_time_remaining.sec = remaining_sec
        feedback.estimated_time_remaining.nanosec = int(
            (remaining_s - remaining_sec) * 1_000_000_000
        )
        try:
            goal_handle.publish_feedback(feedback)
        except Exception as exc:  # pragma: no cover - retained in runtime evidence
            with self.lock:
                self.goal_records[identifier]["feedback_errors"].append(
                    {"at": timestamp(), "error": f"{type(exc).__name__}: {exc}"}
                )
            return

        feedback_at = timestamp()
        with self.lock:
            record = self.goal_records[identifier]
            record["feedback_count"] += 1
            if record["first_feedback_at"] is None:
                record["first_feedback_at"] = feedback_at
            record["last_feedback_at"] = feedback_at
            record["last_feedback_navigation_s"] = round(navigation_s, 6)
            record["last_feedback_simulated_progress_m"] = round(progress_m, 6)

    def _execute_goal(self, goal_handle: Any) -> NavigateToPose.Result:
        identifier = goal_uuid(goal_handle)
        execute_started_at = self._set_execute_started(identifier)
        start_monotonic = float(execute_started_at["monotonic_s"])
        next_feedback_at = start_monotonic
        cleanup_event = self.cleanup_events[identifier]
        try:
            while True:
                now = time.monotonic()
                navigation_s = now - start_monotonic
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    self._set_terminal(
                        identifier,
                        "CANCELED",
                        "action_server_observed_cancel_request",
                        execute_started_at,
                    )
                    return NavigateToPose.Result()
                if cleanup_event.is_set():
                    goal_handle.abort()
                    self._set_terminal(
                        identifier,
                        "ABORTED_BY_TEST_CLEANUP",
                        "forced_cleanup_after_measurement",
                        execute_started_at,
                    )
                    return NavigateToPose.Result()
                if self.stop_all.is_set():
                    goal_handle.abort()
                    self._set_terminal(
                        identifier,
                        "ABORTED_BY_SHUTDOWN",
                        "probe_shutdown",
                        execute_started_at,
                    )
                    return NavigateToPose.Result()
                if navigation_s >= self.goal_duration_s:
                    goal_handle.succeed()
                    self._set_terminal(
                        identifier,
                        "SUCCEEDED_NATURAL",
                        "configured_dummy_duration_elapsed",
                        execute_started_at,
                    )
                    return NavigateToPose.Result()
                if now >= next_feedback_at:
                    self._publish_feedback(goal_handle, identifier, navigation_s)
                    next_feedback_at = now + self.feedback_period_s
                cleanup_event.wait(timeout=min(0.04, self.feedback_period_s))
        except Exception as exc:  # pragma: no cover - captured for runtime diagnosis
            try:
                goal_handle.abort()
            except Exception:
                pass
            self._set_terminal(
                identifier,
                "EXECUTION_EXCEPTION",
                f"{type(exc).__name__}: {exc}",
                execute_started_at,
            )
            return NavigateToPose.Result()

    def publish_direct_ros_goal(self, target_x: float) -> dict[str, Any]:
        message = PoseStamped()
        message.header.frame_id = "map"
        message.header.stamp = self.get_clock().now().to_msg()
        message.pose.position.x = target_x
        message.pose.orientation.w = 1.0
        sent_at = timestamp()
        self.direct_goal_publisher.publish(message)
        return sent_at

    def lease_event_count(self) -> int:
        with self.lock:
            return len(self.lease_events)

    def wait_lease_event(
        self,
        event_name: str,
        *,
        request_id: str | None = None,
        since: int = 0,
        timeout_s: float = 4.0,
    ) -> dict[str, Any]:
        def match() -> dict[str, Any] | None:
            with self.lock:
                for event in self.lease_events[since:]:
                    payload = event["payload"]
                    if payload.get("event") != event_name:
                        continue
                    if request_id is not None and payload.get("request_id") != request_id:
                        continue
                    return copy.deepcopy(event)
            return None

        return wait_until(match, timeout_s, f"lease event {event_name}/{request_id}")

    def latest_lease_event(self) -> dict[str, Any] | None:
        with self.lock:
            if not self.lease_events:
                return None
            return copy.deepcopy(self.lease_events[-1])

    def find_goal(self, target_x: float, since_monotonic_s: float) -> dict[str, Any] | None:
        with self.lock:
            matches = [
                record
                for record in self.goal_records.values()
                if abs(float(record["target_marker_x"]) - target_x) < 1e-5
                and float(record["accepted_at"]["monotonic_s"]) >= since_monotonic_s
            ]
            if not matches:
                return None
            return copy.deepcopy(sorted(matches, key=lambda item: item["accepted_at"]["monotonic_s"])[-1])

    def goal_snapshot(self, identifier: str) -> dict[str, Any]:
        with self.lock:
            return copy.deepcopy(self.goal_records[identifier])

    def goal_snapshots(self, identifiers: Iterable[str]) -> dict[str, dict[str, Any]]:
        with self.lock:
            return {
                identifier: copy.deepcopy(self.goal_records[identifier])
                for identifier in identifiers
                if identifier in self.goal_records
            }

    def action_snapshot(self, identifiers: Iterable[str]) -> dict[str, Any]:
        with self.lock:
            selected = {
                identifier: self.goal_records[identifier]
                for identifier in identifiers
                if identifier in self.goal_records
            }
            active_ids = sorted(
                identifier
                for identifier, record in selected.items()
                if is_active_state(record.get("state"))
            )
            return {
                "active_goal_count": len(active_ids),
                "active_goal_ids": active_ids,
                "goals": {
                    identifier: {
                        "goal_id": identifier,
                        "target_marker_x": record["target_marker_x"],
                        "state": record["state"],
                        "cancel_request_count": len(record["cancel_callbacks"]),
                        "feedback_count": record["feedback_count"],
                        "last_feedback_navigation_s": record["last_feedback_navigation_s"],
                        "last_feedback_simulated_progress_m": record[
                            "last_feedback_simulated_progress_m"
                        ],
                        "terminal_at": copy.deepcopy(record["terminal_at"]),
                    }
                    for identifier, record in selected.items()
                },
            }

    def active_goal_ids(self) -> list[str]:
        with self.lock:
            return sorted(
                identifier
                for identifier, record in self.goal_records.items()
                if is_active_state(record.get("state"))
            )

    def force_cleanup(self, identifiers: Iterable[str]) -> list[str]:
        requested: list[str] = []
        with self.lock:
            for identifier in identifiers:
                record = self.goal_records.get(identifier)
                event = self.cleanup_events.get(identifier)
                if record is None or event is None or not is_active_state(record.get("state")):
                    continue
                record["test_cleanup_requested_at"] = timestamp()
                event.set()
                requested.append(identifier)
        return requested

    def force_cleanup_all(self) -> list[str]:
        return self.force_cleanup(self.active_goal_ids())

    def concurrency_slice(self, since_monotonic_s: float) -> list[dict[str, Any]]:
        with self.lock:
            return copy.deepcopy(
                [
                    event
                    for event in self.concurrency_events
                    if float(event["at"]["monotonic_s"]) >= since_monotonic_s
                ]
            )


class TrialContext:
    def __init__(self, test_id: str, trial_number: int) -> None:
        self.test_id = test_id
        self.trial_number = trial_number
        self.trial_id = f"{test_id}-T{trial_number:02d}"
        self.started_at = timestamp()
        self.started_monotonic_s = float(self.started_at["monotonic_s"])
        self.clients: list[LongActionHorusClient] = []
        self.client_a: LongActionHorusClient | None = None
        self.client_b: LongActionHorusClient | None = None
        self.goal_ids: list[str] = []
        self.heartbeat_counts: dict[str, int] = {"A": 0, "B": 0}
        self.heartbeat_sequence = 0
        self.cleanup: dict[str, Any] = {}


class LongActionTrialRunner:
    def __init__(self, node: LongActionProbeNode, args: argparse.Namespace) -> None:
        self.node = node
        self.args = args
        self.checkpoints = self._make_checkpoints(args.observation_sec)

    @staticmethod
    def _make_checkpoints(observation_s: float) -> list[float]:
        checkpoints = [point for point in DEFAULT_CHECKPOINTS if point <= observation_s + 1e-9]
        if not checkpoints or abs(checkpoints[-1] - observation_s) > 1e-9:
            checkpoints.append(observation_s)
        return sorted(set(round(point, 3) for point in checkpoints))

    def _progress(self, message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    def _new_client(self, ctx: TrialContext, label: str) -> LongActionHorusClient:
        case_seed = sum(ord(char) for char in ctx.test_id) & 0xFFFF
        label_seed = 0xA if label == "A" else 0xB
        session_id = (
            (case_seed << 32)
            | (ctx.trial_number << 16)
            | (label_seed << 8)
            | 0x01
        )
        client = LongActionHorusClient(f"{ctx.trial_id}-{label}", session_id)
        # Track the socket before connect/register so a partially initialized
        # trial is still recoverable by _cleanup_context().
        ctx.clients.append(client)
        if label == "A":
            ctx.client_a = client
        else:
            ctx.client_b = client
        client.connect()
        publishers = [
            (1, CATALOG_TOPIC, "std_msgs/msg/String"),
            (2, LEASE_TOPIC, "std_msgs/msg/String"),
            (3, GOAL_TOPIC, "geometry_msgs/msg/PoseStamped"),
            (4, CANCEL_TOPIC, "std_msgs/msg/String"),
        ]
        for channel, topic, type_name in publishers:
            client.register_publisher(channel, topic, type_name)
        return client

    def _heartbeat(self, ctx: TrialContext, client: LongActionHorusClient, label: str) -> None:
        if not client.connected:
            return
        ctx.heartbeat_sequence += 1
        client.heartbeat(
            f"{ctx.trial_id}-{label}-hb-{ctx.heartbeat_sequence}",
            f"long-probe-{label}",
            "operator",
            f"{ctx.trial_id}-session-{label}",
        )
        ctx.heartbeat_counts[label] += 1

    def _wait_with_heartbeats(
        self,
        ctx: TrialContext,
        deadline_monotonic_s: float,
        heartbeat_clients: list[tuple[LongActionHorusClient, str]],
    ) -> None:
        interval = min(
            self.args.heartbeat_interval_sec,
            max(0.1, self.args.lease_ttl_ms / 3000.0),
        )
        next_heartbeat = time.monotonic()
        while time.monotonic() < deadline_monotonic_s:
            now = time.monotonic()
            if heartbeat_clients and now >= next_heartbeat:
                for client, label in heartbeat_clients:
                    self._heartbeat(ctx, client, label)
                next_heartbeat = now + interval
            remaining = deadline_monotonic_s - time.monotonic()
            if remaining > 0:
                time.sleep(min(0.04, remaining))

    def _wait_goal_with_heartbeats(
        self,
        ctx: TrialContext,
        target_x: float,
        since_monotonic_s: float,
        heartbeat_clients: list[tuple[LongActionHorusClient, str]],
        timeout_s: float = 6.0,
    ) -> dict[str, Any]:
        interval = min(
            self.args.heartbeat_interval_sec,
            max(0.1, self.args.lease_ttl_ms / 3000.0),
        )
        next_heartbeat = time.monotonic()

        def tick() -> None:
            nonlocal next_heartbeat
            now = time.monotonic()
            if heartbeat_clients and now >= next_heartbeat:
                for client, label in heartbeat_clients:
                    self._heartbeat(ctx, client, label)
                next_heartbeat = now + interval

        return wait_until(
            lambda: self.node.find_goal(target_x, since_monotonic_s),
            timeout_s,
            f"goal marker {target_x}",
            tick=tick,
        )

    def _wait_goal_terminal(
        self,
        ctx: TrialContext,
        identifier: str,
        *,
        heartbeat_clients: list[tuple[LongActionHorusClient, str]] | None = None,
        timeout_s: float = 6.0,
    ) -> dict[str, Any]:
        heartbeat_clients = heartbeat_clients or []
        interval = min(
            self.args.heartbeat_interval_sec,
            max(0.1, self.args.lease_ttl_ms / 3000.0),
        )
        next_heartbeat = time.monotonic()

        def tick() -> None:
            nonlocal next_heartbeat
            now = time.monotonic()
            if heartbeat_clients and now >= next_heartbeat:
                for client, label in heartbeat_clients:
                    self._heartbeat(ctx, client, label)
                next_heartbeat = now + interval

        return wait_until(
            lambda: (
                snapshot
                if (snapshot := self.node.goal_snapshot(identifier))["state"] in TERMINAL_STATES
                else None
            ),
            timeout_s,
            f"goal {identifier} terminal state",
            tick=tick,
        )

    def _marker(self, test_id: str, trial_number: int, role: str = "A") -> float:
        bases = {
            "A1_EXPLICIT_CANCEL": 10.0,
            "R1_RELEASE": 20.0,
            "R2_TTL_EXPIRY": 30.0,
            "R3_DISCONNECT": 40.0,
            "R4_HANDOFF": 50.0 if role == "A" else 60.0,
            "F1_SELECTIVITY": 70.0 if role == "A" else 80.0,
        }
        return round(bases[test_id] + trial_number / 100.0, 6)

    def _setup_trial(
        self,
        test_id: str,
        trial_number: int,
        *,
        need_b: bool,
    ) -> tuple[TrialContext, dict[str, Any]]:
        ctx = TrialContext(test_id, trial_number)
        try:
            if self.node.active_goal_ids():
                raise RuntimeError(f"unclean action state before {ctx.trial_id}")

            client_a = self._new_client(ctx, "A")
            if need_b:
                self._new_client(ctx, "B")

            catalog_since = self.node.lease_event_count()
            client_a.publish_protected_catalog()
            catalog_event = self.node.wait_lease_event(
                "snapshot", since=catalog_since, timeout_s=3.0
            )
            if catalog_event["payload"].get("leases"):
                raise RuntimeError(
                    f"unclean lease state before {ctx.trial_id}: "
                    f"{catalog_event['payload'].get('leases')}"
                )

            acquire_request_id = f"{ctx.trial_id}-A-acquire"
            acquire_since = self.node.lease_event_count()
            client_a.acquire(
                acquire_request_id,
                "long-probe-A",
                "operator",
                f"{ctx.trial_id}-session-A",
            )
            acquire_event = self.node.wait_lease_event(
                "lease_granted",
                request_id=acquire_request_id,
                since=acquire_since,
                timeout_s=3.0,
            )

            marker_x = self._marker(test_id, trial_number, "A")
            sent_at = timestamp()
            client_a.publish_goal(marker_x)
            goal = self._wait_goal_with_heartbeats(
                ctx,
                marker_x,
                ctx.started_monotonic_s,
                [(client_a, "A")],
            )
            ctx.goal_ids.append(goal["goal_id"])
            active_until = (
                float(goal["accepted_at"]["monotonic_s"])
                + self.args.revocation_delay_sec
            )
            self._wait_with_heartbeats(ctx, active_until, [(client_a, "A")])

            setup = {
                "fresh_trial_state_verified": True,
                "catalog_event": catalog_event,
                "lease_acquire_event": acquire_event,
                "goal_publish_sent_at": sent_at,
                "goal_id": goal["goal_id"],
                "goal_accepted_at": goal["accepted_at"],
                "goal_marker_x": marker_x,
                "lease_holder": "A",
                "lease_state_after_acquire": acquire_event["payload"].get("leases", []),
            }
            return ctx, setup
        except Exception:
            self._cleanup_context(ctx)
            raise

    def _observe_checkpoints(
        self,
        ctx: TrialContext,
        revocation_at: dict[str, Any],
        goal_ids: list[str],
        *,
        heartbeat_clients: list[tuple[LongActionHorusClient, str]] | None = None,
    ) -> list[dict[str, Any]]:
        heartbeat_clients = heartbeat_clients or []
        origin = float(revocation_at["monotonic_s"])
        observations: list[dict[str, Any]] = []
        for checkpoint_s in self.checkpoints:
            target = origin + checkpoint_s
            self._wait_with_heartbeats(ctx, target, heartbeat_clients)
            observed_at = timestamp()
            snapshot = self.node.action_snapshot(goal_ids)
            latest_lease = self.node.latest_lease_event()
            observations.append(
                {
                    "scheduled_offset_s": checkpoint_s,
                    "observed_offset_s": round(
                        float(observed_at["monotonic_s"]) - origin, 6
                    ),
                    "observed_at": observed_at,
                    "lease_state": None if latest_lease is None else latest_lease["payload"],
                    **snapshot,
                }
            )
        return observations

    def _post_revocation_measurement(
        self,
        identifier: str,
        revocation_at: dict[str, Any],
        observation_end_at: dict[str, Any],
    ) -> dict[str, Any]:
        goal = self.node.goal_snapshot(identifier)
        if goal["terminal_at"] is None:
            duration_s = max(0.0, elapsed(observation_end_at, revocation_at) or 0.0)
            censored = True
            basis = "active_at_observation_end_lower_bound"
        else:
            duration_s = max(0.0, elapsed(goal["terminal_at"], revocation_at) or 0.0)
            censored = False
            basis = "revocation_to_terminal"
        return {
            "post_revocation_active_duration_s": round(duration_s, 6),
            "duration_is_right_censored_lower_bound": censored,
            "duration_basis": basis,
            "simulated_additional_distance_m": round(
                duration_s * self.args.simulated_speed_mps, 6
            ),
            "distance_model": f"constant {self.args.simulated_speed_mps} m/s; not physical motion",
        }

    def _cleanup_context(self, ctx: TrialContext) -> dict[str, Any]:
        cleanup_started_at = timestamp()
        forced_goal_ids = self.node.force_cleanup(ctx.goal_ids)
        terminal_wait_errors: list[str] = []
        for identifier in forced_goal_ids:
            try:
                self._wait_goal_terminal(ctx, identifier, timeout_s=3.0)
            except Exception as exc:
                terminal_wait_errors.append(f"{identifier}: {type(exc).__name__}: {exc}")

        # Goals are terminal before lease/socket cleanup.  This prevents cleanup
        # traffic (especially when evaluating a test-only fix) from polluting
        # the measured cancel callbacks.
        release_errors: list[str] = []
        for label, client in (("A", ctx.client_a), ("B", ctx.client_b)):
            if client is None or not client.connected:
                continue
            try:
                client.release(f"{ctx.trial_id}-{label}-cleanup-release")
            except Exception as exc:
                release_errors.append(f"{label}: {type(exc).__name__}: {exc}")
        time.sleep(0.08)
        for client in ctx.clients:
            try:
                client.close()
            except Exception as exc:
                release_errors.append(f"close {client.label}: {type(exc).__name__}: {exc}")

        try:
            wait_until(
                lambda: not self.node.active_goal_ids(),
                3.0,
                f"clean action state after {ctx.trial_id}",
            )
        except Exception as exc:
            terminal_wait_errors.append(f"active-state: {type(exc).__name__}: {exc}")

        cleanup = {
            "started_at": cleanup_started_at,
            "completed_at": timestamp(),
            "forced_goal_ids": forced_goal_ids,
            "terminal_wait_errors": terminal_wait_errors,
            "release_or_close_errors": release_errors,
            "active_goal_ids_after_cleanup": self.node.active_goal_ids(),
            "clean": not terminal_wait_errors
            and not release_errors
            and not self.node.active_goal_ids(),
        }
        ctx.cleanup = cleanup
        return cleanup

    def _base_result(
        self,
        ctx: TrialContext,
        setup: dict[str, Any],
        expected: str,
    ) -> dict[str, Any]:
        return {
            "test_id": ctx.test_id,
            "trial_id": ctx.trial_id,
            "trial_number": ctx.trial_number,
            "revision": self.args.revision,
            "runtime_label": self.args.runtime_label,
            "started_at": ctx.started_at,
            "path": [
                "HorusLink client",
                "horus_unity_bridge",
                "ROS goal/cancel topic",
                "horus_backend Nav2ActionAdapter",
                "dummy NavigateToPose action server",
            ],
            "lease_holder": "A",
            "expected": expected,
            "setup": setup,
        }

    def _finish_result(self, result: dict[str, Any], ctx: TrialContext) -> dict[str, Any]:
        measurement_goals = self.node.goal_snapshots(ctx.goal_ids)
        result["goal_records_at_measurement_end"] = measurement_goals
        result["cancel_request_count_at_measurement_end"] = sum(
            len(goal["cancel_callbacks"]) for goal in measurement_goals.values()
        )
        result["heartbeat_counts"] = dict(ctx.heartbeat_counts)
        concurrency = self.node.concurrency_slice(ctx.started_monotonic_s)
        result["max_simultaneous_active_goals"] = max(
            (event["active_goal_count"] for event in concurrency), default=0
        )
        result["concurrency_events"] = concurrency
        result["measurement_completed_at"] = timestamp()
        cleanup = self._cleanup_context(ctx)
        result["cleanup"] = cleanup
        final_goals = self.node.goal_snapshots(ctx.goal_ids)
        result["goal_records_final"] = final_goals
        result["trial_complete"] = cleanup["clean"]
        primary_goal_id = result["setup"]["goal_id"]
        primary_at_measurement = measurement_goals[primary_goal_id]
        primary_final = final_goals[primary_goal_id]
        b_goal_id = result.get("b_goal_id")
        b_at_measurement = (
            measurement_goals.get(b_goal_id) if isinstance(b_goal_id, str) else None
        )
        result["evidence_fields"] = {
            "test_id": result["test_id"],
            "trial_id": result["trial_id"],
            "revision": result["revision"],
            "lease_holder": result["lease_holder"],
            "goal_id": primary_goal_id,
            "goal_accepted_time": primary_final["accepted_at"],
            "revocation_time": result.get("revocation_event_timestamp"),
            "cancel_request_times": [
                callback["callback_at"]
                for callback in primary_at_measurement["cancel_callbacks"]
            ],
            "cancel_goal_ids": [
                callback["cancel_goal_id"]
                for goal in measurement_goals.values()
                for callback in goal["cancel_callbacks"]
            ],
            "terminal_time": primary_final["terminal_at"],
            "goal_state_at_observation_end": primary_at_measurement["state"],
            "goal_terminal_state": primary_final["state"],
            "feedback_count_at_observation_end": primary_at_measurement[
                "feedback_count"
            ],
            "first_feedback_time": primary_at_measurement["first_feedback_at"],
            "last_feedback_time_at_observation_end": primary_at_measurement[
                "last_feedback_at"
            ],
            "last_simulated_progress_m_at_observation_end": primary_at_measurement[
                "last_feedback_simulated_progress_m"
            ],
            "b_goal_id": b_goal_id,
            "b_goal_status_at_observation_end": (
                "NOT_APPLICABLE" if b_at_measurement is None else b_at_measurement["state"]
            ),
            "active_goal_count_at_observation_end": sum(
                1
                for goal in measurement_goals.values()
                if is_active_state(goal.get("state"))
            ),
            "max_simultaneous_active_goals": result["max_simultaneous_active_goals"],
            "post_revocation_duration_s": result.get(
                "post_revocation_active_duration_s"
            ),
            "simulated_additional_distance_m": result.get(
                "simulated_additional_distance_m"
            ),
            "expected": result.get("expected"),
            "observed": result.get("observed"),
            "verdict": result.get("verdict"),
            "cleanup_clean": cleanup["clean"],
        }
        return result

    def run_explicit_cancel(self, trial_number: int) -> dict[str, Any]:
        ctx, setup = self._setup_trial("A1_EXPLICIT_CANCEL", trial_number, need_b=False)
        result = self._base_result(
            ctx,
            setup,
            "official HORUS cancel topic reaches Nav2 adapter; server cancel callback fires and goal terminates CANCELED",
        )
        try:
            assert ctx.client_a is not None
            goal_id = setup["goal_id"]
            cancel_sent_at = timestamp()
            ctx.client_a.publish_cancel("cancel")
            terminal = self._wait_goal_terminal(
                ctx,
                goal_id,
                heartbeat_clients=[(ctx.client_a, "A")],
                timeout_s=6.0,
            )
            cancel_callbacks = terminal["cancel_callbacks"]
            callback_at = cancel_callbacks[0]["callback_at"] if cancel_callbacks else None
            result["cancel_sent_at"] = cancel_sent_at
            result["cancel_callback_at"] = callback_at
            result["cancel_goal_ids"] = [
                callback["cancel_goal_id"] for callback in cancel_callbacks
            ]
            result["goal_terminal_at"] = terminal["terminal_at"]
            result["cancel_callback_latency_s"] = elapsed(callback_at, cancel_sent_at)
            result["cancel_to_terminal_latency_s"] = elapsed(
                terminal["terminal_at"], cancel_sent_at
            )
            result["final_goal_state"] = terminal["state"]
            passed = bool(cancel_callbacks) and terminal["state"] == "CANCELED"
            result["observed"] = (
                "official cancel callback and CANCELED terminal state observed"
                if passed
                else "official cancel baseline did not produce the required callback/terminal state"
            )
            result["verdict"] = "PASS" if passed else "FAIL"
            result["outcome_class"] = (
                "EXPLICIT_CANCEL_WORKS" if passed else "EXPLICIT_CANCEL_PATH_INVALID"
            )
            return self._finish_result(result, ctx)
        except Exception:
            self._cleanup_context(ctx)
            raise

    def _run_single_revocation(
        self,
        test_id: str,
        trial_number: int,
    ) -> dict[str, Any]:
        need_b = test_id == "R3_DISCONNECT"
        ctx, setup = self._setup_trial(test_id, trial_number, need_b=need_b)
        descriptions = {
            "R1_RELEASE": "A lease release is observed; measure whether the accepted goal is canceled or remains active",
            "R2_TTL_EXPIRY": "A heartbeat stops and lease expiry is observed; measure accepted-goal lifecycle",
            "R3_DISCONNECT": "A HorusLink connection closes and lease cleanup is observed; measure accepted-goal lifecycle",
        }
        result = self._base_result(ctx, setup, descriptions[test_id])
        try:
            assert ctx.client_a is not None
            state_since = self.node.lease_event_count()
            revocation_initiated_at: dict[str, Any]
            if test_id == "R1_RELEASE":
                request_id = f"{ctx.trial_id}-release"
                revocation_initiated_at = timestamp()
                ctx.client_a.release(request_id)
                revocation_event = self.node.wait_lease_event(
                    "lease_released",
                    request_id=request_id,
                    since=state_since,
                    timeout_s=3.0,
                )
            elif test_id == "R2_TTL_EXPIRY":
                # _setup_trial kept the lease alive through the requested
                # two-second active period.  No further heartbeat is sent.
                revocation_initiated_at = timestamp()
                revocation_event = self.node.wait_lease_event(
                    "lease_expired",
                    since=state_since,
                    timeout_s=self.args.lease_ttl_ms / 1000.0 + 3.0,
                )
            else:
                revocation_initiated_at = timestamp()
                ctx.client_a.close()
                revocation_event = self.node.wait_lease_event(
                    "client_disconnected_release",
                    since=state_since,
                    timeout_s=4.0,
                )

            revocation_at = revocation_event["received_at"]
            observations = self._observe_checkpoints(
                ctx,
                revocation_at,
                [setup["goal_id"]],
            )
            observation_end_at = observations[-1]["observed_at"]
            goal = self.node.goal_snapshot(setup["goal_id"])
            cancel_callbacks = list(goal["cancel_callbacks"])
            post = self._post_revocation_measurement(
                setup["goal_id"], revocation_at, observation_end_at
            )

            if cancel_callbacks:
                cancel_delay = elapsed(cancel_callbacks[0]["callback_at"], revocation_at)
                outcome = (
                    "REVOCATION_CANCEL_IMMEDIATE"
                    if cancel_delay is not None and cancel_delay <= 0.5
                    else "REVOCATION_CANCEL_DELAYED"
                )
            elif is_active_state(goal["state"]):
                outcome = "GOAL_CONTINUED_THROUGH_OBSERVATION"
            elif goal["state"] == "SUCCEEDED_NATURAL":
                outcome = "GOAL_CONTINUED_TO_NATURAL_COMPLETION"
            else:
                outcome = "GOAL_TERMINATED_WITHOUT_RECORDED_CANCEL"

            result.update(
                {
                    "revocation_initiated_at": revocation_initiated_at,
                    "revocation_event": revocation_event,
                    "revocation_event_timestamp": revocation_at,
                    "lease_state_after_revocation": revocation_event["payload"].get(
                        "leases", []
                    ),
                    "checkpoints": observations,
                    "cancel_request_count": len(cancel_callbacks),
                    "first_cancel_callback_at": (
                        cancel_callbacks[0]["callback_at"] if cancel_callbacks else None
                    ),
                    "cancel_callback_latency_from_revocation_initiation_s": (
                        elapsed(
                            cancel_callbacks[0]["callback_at"],
                            revocation_initiated_at,
                        )
                        if cancel_callbacks
                        else None
                    ),
                    "cancel_callback_latency_from_lease_state_observation_s": (
                        elapsed(cancel_callbacks[0]["callback_at"], revocation_at)
                        if cancel_callbacks
                        else None
                    ),
                    "cancel_goal_ids": [
                        callback["cancel_goal_id"] for callback in cancel_callbacks
                    ],
                    "goal_state_at_observation_end": goal["state"],
                    **post,
                    "observed": outcome,
                    "outcome_class": outcome,
                    # This is a measurement verdict, not a requirement that a
                    # vulnerability be present.  Safe cancellation remains a
                    # valid PASS observation for the experiment harness.
                    "verdict": "MEASURED",
                }
            )
            return self._finish_result(result, ctx)
        except Exception:
            self._cleanup_context(ctx)
            raise

    def run_handoff(self, trial_number: int) -> dict[str, Any]:
        ctx, setup = self._setup_trial("R4_HANDOFF", trial_number, need_b=True)
        result = self._base_result(
            ctx,
            setup,
            "after A release, B acquires the lease and starts a distinct goal; measure A/B acceptance, overlap, preemption, and cancel IDs",
        )
        try:
            assert ctx.client_a is not None and ctx.client_b is not None
            release_request_id = f"{ctx.trial_id}-A-release"
            state_since = self.node.lease_event_count()
            revocation_initiated_at = timestamp()
            ctx.client_a.release(release_request_id)
            release_event = self.node.wait_lease_event(
                "lease_released",
                request_id=release_request_id,
                since=state_since,
                timeout_s=3.0,
            )
            revocation_at = release_event["received_at"]

            b_acquire_id = f"{ctx.trial_id}-B-acquire"
            b_since = self.node.lease_event_count()
            b_acquire_sent_at = timestamp()
            ctx.client_b.acquire(
                b_acquire_id,
                "long-probe-B",
                "operator",
                f"{ctx.trial_id}-session-B",
            )
            b_acquire_event = self.node.wait_lease_event(
                "lease_granted",
                request_id=b_acquire_id,
                since=b_since,
                timeout_s=3.0,
            )
            b_marker_x = self._marker("R4_HANDOFF", trial_number, "B")
            b_goal_sent_at = timestamp()
            ctx.client_b.publish_goal(b_marker_x)
            b_goal = self._wait_goal_with_heartbeats(
                ctx,
                b_marker_x,
                ctx.started_monotonic_s,
                [(ctx.client_b, "B")],
            )
            ctx.goal_ids.append(b_goal["goal_id"])

            observations = self._observe_checkpoints(
                ctx,
                revocation_at,
                list(ctx.goal_ids),
                heartbeat_clients=[(ctx.client_b, "B")],
            )
            observation_end_at = observations[-1]["observed_at"]
            a_goal = self.node.goal_snapshot(setup["goal_id"])
            b_goal_final = self.node.goal_snapshot(b_goal["goal_id"])
            concurrency = self.node.concurrency_slice(ctx.started_monotonic_s)
            max_active = max(
                (event["active_goal_count"] for event in concurrency), default=0
            )
            b_accepted = b_goal_final["accepted_at"] is not None
            a_active_at_b_accept = any(
                event["active_goal_count"] >= 2 for event in concurrency
            )

            if not b_accepted:
                outcome = "BACKEND_OR_SERVER_REJECTED_B"
            elif a_active_at_b_accept:
                outcome = "A_AND_B_SIMULTANEOUSLY_ACTIVE"
            elif a_goal["state"] == "CANCELED":
                outcome = "B_PREEMPTED_A_WITH_CANCEL"
            elif not is_active_state(a_goal["state"]):
                outcome = "A_TERMINATED_BEFORE_OR_DURING_B_GOAL"
            else:
                outcome = "B_ACCEPTED_NO_OVERLAP_OBSERVED"

            result.update(
                {
                    "revocation_initiated_at": revocation_initiated_at,
                    "revocation_event": release_event,
                    "revocation_event_timestamp": revocation_at,
                    "b_lease_acquire_sent_at": b_acquire_sent_at,
                    "b_lease_acquire_event": b_acquire_event,
                    "b_goal_publish_sent_at": b_goal_sent_at,
                    "b_goal_id": b_goal["goal_id"],
                    "b_goal_accepted_at": b_goal["accepted_at"],
                    "b_goal_accepted": b_accepted,
                    "checkpoints": observations,
                    "a_cancel_request_count": len(a_goal["cancel_callbacks"]),
                    "b_cancel_request_count": len(b_goal_final["cancel_callbacks"]),
                    "cancel_goal_ids": [
                        callback["cancel_goal_id"]
                        for goal in (a_goal, b_goal_final)
                        for callback in goal["cancel_callbacks"]
                    ],
                    "a_goal_state_at_observation_end": a_goal["state"],
                    "b_goal_state_at_observation_end": b_goal_final["state"],
                    "a_goal_preempted": a_goal["state"] == "CANCELED",
                    "max_simultaneous_active_goals": max_active,
                    **self._post_revocation_measurement(
                        setup["goal_id"], revocation_at, observation_end_at
                    ),
                    "observed": outcome,
                    "outcome_class": outcome,
                    "verdict": "MEASURED",
                    "interpretation_guardrail": (
                        "concurrency is in a non-physical dummy action server configured to accept "
                        "multiple goals; it is not evidence of a physical collision or stock Nav2 "
                        "controller preemption behavior"
                    ),
                }
            )
            return self._finish_result(result, ctx)
        except Exception:
            self._cleanup_context(ctx)
            raise

    def run_fix_selectivity(self, trial_number: int) -> dict[str, Any]:
        """Challenge a test-only revocation fix with an unrelated latest goal.

        The independent ROS-side goal deliberately bypasses HorusLink admission.
        This is a fix-correctness/selectivity experiment, not an attack result
        against the fixed upstream revision.
        """

        ctx, setup = self._setup_trial("F1_SELECTIVITY", trial_number, need_b=False)
        result = self._base_result(
            ctx,
            setup,
            "a test-only fix should cancel A's owned goal without canceling a later unrelated ROS-side goal",
        )
        result["test_scope"] = "test_only_minimal_fix_selectivity_challenge"
        result["security_interpretation"] = "not_an_attack_runtime"
        try:
            assert ctx.client_a is not None
            unrelated_marker_x = self._marker("F1_SELECTIVITY", trial_number, "B")
            unrelated_sent_at = self.node.publish_direct_ros_goal(unrelated_marker_x)
            unrelated_goal = self._wait_goal_with_heartbeats(
                ctx,
                unrelated_marker_x,
                ctx.started_monotonic_s,
                [(ctx.client_a, "A")],
            )
            ctx.goal_ids.append(unrelated_goal["goal_id"])
            # Give the unmodified adapter's goal response callback enough time
            # to make the unrelated goal its latest active_goal_handle.
            self._wait_with_heartbeats(
                ctx,
                time.monotonic() + 0.25,
                [(ctx.client_a, "A")],
            )

            release_request_id = f"{ctx.trial_id}-A-release"
            state_since = self.node.lease_event_count()
            release_sent_at = timestamp()
            ctx.client_a.release(release_request_id)
            release_event = self.node.wait_lease_event(
                "lease_released",
                request_id=release_request_id,
                since=state_since,
                timeout_s=3.0,
            )
            revocation_at = release_event["received_at"]
            observations = self._observe_checkpoints(
                ctx,
                revocation_at,
                list(ctx.goal_ids),
            )
            observation_end_at = observations[-1]["observed_at"]
            a_goal = self.node.goal_snapshot(setup["goal_id"])
            unrelated = self.node.goal_snapshot(unrelated_goal["goal_id"])
            a_cancelled = bool(a_goal["cancel_callbacks"])
            unrelated_cancelled = bool(unrelated["cancel_callbacks"])
            if a_cancelled and not unrelated_cancelled:
                selectivity = "PRECISE_OWNER_CANCEL"
            elif not a_cancelled and unrelated_cancelled:
                selectivity = "WRONG_LATEST_GOAL_CANCELLED"
            elif a_cancelled and unrelated_cancelled:
                selectivity = "OVERBROAD_CANCEL"
            else:
                selectivity = "NO_CANCEL_COVERAGE"

            result.update(
                {
                    "independent_ros_goal": {
                        "origin": "probe ROS-side PoseStamped publisher",
                        "goal_publish_sent_at": unrelated_sent_at,
                        "goal_id": unrelated_goal["goal_id"],
                        "goal_accepted_at": unrelated_goal["accepted_at"],
                        "target_marker_x": unrelated_marker_x,
                    },
                    "b_goal_id": unrelated_goal["goal_id"],
                    "revocation_initiated_at": release_sent_at,
                    "revocation_event": release_event,
                    "revocation_event_timestamp": revocation_at,
                    "checkpoints": observations,
                    "a_owned_goal_cancel_request_count": len(a_goal["cancel_callbacks"]),
                    "unrelated_goal_cancel_request_count": len(
                        unrelated["cancel_callbacks"]
                    ),
                    "cancel_goal_ids": [
                        callback["cancel_goal_id"]
                        for goal in (a_goal, unrelated)
                        for callback in goal["cancel_callbacks"]
                    ],
                    "selectivity_result": selectivity,
                    "observed": selectivity,
                    "outcome_class": selectivity,
                    "verdict": "MEASURED",
                    **self._post_revocation_measurement(
                        setup["goal_id"], revocation_at, observation_end_at
                    ),
                    "interpretation_guardrail": (
                        "the direct ROS-side goal is a test-only selectivity challenge for a "
                        "candidate patch; it is not attributed to an external HORUS client"
                    ),
                }
            )
            return self._finish_result(result, ctx)
        except Exception:
            self._cleanup_context(ctx)
            raise

    def run_case(self, test_id: str, trial_number: int) -> dict[str, Any]:
        self._progress(
            f"[HORUS long probe] {test_id} trial {trial_number}/{self.args.trials}"
        )
        try:
            if test_id == "A1_EXPLICIT_CANCEL":
                return self.run_explicit_cancel(trial_number)
            if test_id in {"R1_RELEASE", "R2_TTL_EXPIRY", "R3_DISCONNECT"}:
                return self._run_single_revocation(test_id, trial_number)
            if test_id == "R4_HANDOFF":
                return self.run_handoff(trial_number)
            if test_id == "F1_SELECTIVITY":
                return self.run_fix_selectivity(trial_number)
            raise ValueError(f"unknown test id: {test_id}")
        except Exception as exc:
            self.node.force_cleanup_all()
            try:
                wait_until(
                    lambda: not self.node.active_goal_ids(),
                    3.0,
                    f"emergency cleanup after {test_id}-T{trial_number:02d}",
                )
            except Exception:
                pass
            return {
                "test_id": test_id,
                "trial_id": f"{test_id}-T{trial_number:02d}",
                "trial_number": trial_number,
                "revision": self.args.revision,
                "runtime_label": self.args.runtime_label,
                "trial_complete": False,
                "verdict": "ERROR",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
                "active_goal_ids_after_emergency_cleanup": self.node.active_goal_ids(),
            }


def selected_cases(suite: str) -> list[str]:
    if suite == "revocation":
        return ["A1_EXPLICIT_CANCEL", "R1_RELEASE", "R2_TTL_EXPIRY", "R3_DISCONNECT"]
    if suite == "handoff":
        return ["R4_HANDOFF"]
    if suite == "fix":
        return [
            "A1_EXPLICIT_CANCEL",
            "R1_RELEASE",
            "R2_TTL_EXPIRY",
            "R3_DISCONNECT",
            "R4_HANDOFF",
            "F1_SELECTIVITY",
        ]
    return [
        "A1_EXPLICIT_CANCEL",
        "R1_RELEASE",
        "R2_TTL_EXPIRY",
        "R3_DISCONNECT",
        "R4_HANDOFF",
    ]


def aggregate_results(trials: list[dict[str, Any]]) -> dict[str, Any]:
    aggregate: dict[str, Any] = {}
    for test_id in sorted({trial["test_id"] for trial in trials}):
        selected = [trial for trial in trials if trial["test_id"] == test_id]
        complete = [trial for trial in selected if trial.get("trial_complete")]
        outcomes: dict[str, int] = {}
        for trial in complete:
            outcome = str(trial.get("outcome_class", "UNKNOWN"))
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
        aggregate[test_id] = {
            "trials_requested": len(selected),
            "trials_complete": len(complete),
            "trials_error": len(selected) - len(complete),
            "outcomes": outcomes,
            "cancel_requests_at_measurement_end": sum(
                int(trial.get("cancel_request_count_at_measurement_end", 0))
                for trial in complete
            ),
            "max_simultaneous_active_goals": max(
                (int(trial.get("max_simultaneous_active_goals", 0)) for trial in complete),
                default=0,
            ),
        }
    return aggregate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repeated long-running HORUS Nav2 action/revocation measurement"
    )
    parser.add_argument(
        "--suite",
        choices=("revocation", "handoff", "fix", "all"),
        default="all",
        help=(
            "revocation=A1+R1/R2/R3, handoff=R4, fix=all plus test-only "
            "selectivity challenge, all=A1+R1/R2/R3/R4"
        ),
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=int(os.environ.get("HORUS_LONG_ACTION_TRIALS", "5")),
    )
    parser.add_argument("--observation-sec", type=float, default=10.0)
    parser.add_argument("--goal-duration-sec", type=float, default=30.0)
    parser.add_argument("--revocation-delay-sec", type=float, default=2.0)
    parser.add_argument("--feedback-period-sec", type=float, default=0.25)
    parser.add_argument("--heartbeat-interval-sec", type=float, default=0.30)
    parser.add_argument("--lease-ttl-ms", type=int, default=1200)
    parser.add_argument("--simulated-speed-mps", type=float, default=0.1)
    parser.add_argument("--revision", default=FIXED_HORUS_REVISION)
    parser.add_argument(
        "--runtime-label",
        default="fixed-unmodified",
        help="Use test-only-fix when a parent runner supplies a patched temporary tree",
    )
    args = parser.parse_args()
    if args.trials < 1:
        parser.error("--trials must be at least 1")
    if args.observation_sec < 0.5:
        parser.error("--observation-sec must be at least 0.5")
    if args.goal_duration_sec < 30.0:
        parser.error("--goal-duration-sec must be at least 30 seconds")
    if args.revocation_delay_sec <= 0:
        parser.error("--revocation-delay-sec must be positive")
    if args.feedback_period_sec <= 0:
        parser.error("--feedback-period-sec must be positive")
    if args.lease_ttl_ms < 500:
        parser.error("--lease-ttl-ms must be at least HORUS's 500 ms minimum")
    if args.simulated_speed_mps <= 0:
        parser.error("--simulated-speed-mps must be positive")
    return args


def emit_json(report: dict[str, Any]) -> None:
    print("HORUS_LONG_ACTION_JSON_BEGIN")
    print(json.dumps(report, indent=2, sort_keys=True))
    print("HORUS_LONG_ACTION_JSON_END")


def main() -> int:
    args = parse_args()
    started_at = timestamp()
    report: dict[str, Any] = {
        "schema": "horus-long-action-probe/v1",
        "probe": "horus_long_action_probe.py",
        "suite": args.suite,
        "started_at": started_at,
        "revision": args.revision,
        "runtime_label": args.runtime_label,
        "configuration": {
            "trials_per_case": args.trials,
            "goal_duration_s": args.goal_duration_sec,
            "revocation_delay_s": args.revocation_delay_sec,
            "observation_s": args.observation_sec,
            "checkpoints_s": LongActionTrialRunner._make_checkpoints(args.observation_sec),
            "feedback_period_s": args.feedback_period_sec,
            "lease_ttl_ms_expected": args.lease_ttl_ms,
            "simulated_speed_mps": args.simulated_speed_mps,
            "network_scope": "bridge/backend expected on container loopback; parent runner enforces --network none",
            "physical_robot": False,
        },
        "actual_path": [
            "HorusLink client",
            "unmodified/test-variant HORUS bridge",
            "HORUS backend Nav2ActionAdapter",
            "dummy NavigateToPose action server",
        ],
        "interpretation_guardrails": [
            "simulated distance is a constant-speed software model, not physical movement",
            "dummy action server concurrency is not a claim about a stock Nav2 controller",
            "fix selectivity is patch correctness testing, not attack evidence",
        ],
        "second_action_type": {
            "status": "NOT_RUN",
            "classification": "NAV2_ADAPTER_SPECIFIC_LIMITATION",
            "reason": (
                "the fixed public HORUS backend exposes Nav2ActionAdapter only; inventing a "
                "new vulnerable adapter would violate the actual-backend-path requirement"
            ),
            "source_evidence": [
                "horus_backend/src/nav2_action_adapter.cpp",
                "horus_backend/include/horus_backend/nav2_action_adapter.hpp",
            ],
        },
        "trials": [],
    }

    rclpy.init()
    node = LongActionProbeNode(
        goal_duration_s=args.goal_duration_sec,
        feedback_period_s=args.feedback_period_sec,
        simulated_speed_mps=args.simulated_speed_mps,
    )
    executor = MultiThreadedExecutor(num_threads=12)
    executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    robot_id: str | None = None
    robot_unregistered = False
    try:
        robot_id = register_robot(node)
        report["robot_registration"] = {
            "success": True,
            "robot_id": robot_id,
            "action_topic": ACTION_TOPIC,
            "goal_topic": GOAL_TOPIC,
            "cancel_topic": CANCEL_TOPIC,
        }
        runner = LongActionTrialRunner(node, args)
        cases = selected_cases(args.suite)
        report["cases"] = cases
        for test_id in cases:
            for trial_number in range(1, args.trials + 1):
                report["trials"].append(runner.run_case(test_id, trial_number))

        report["aggregate"] = aggregate_results(report["trials"])
        errors = [trial for trial in report["trials"] if not trial.get("trial_complete")]
        baseline_trials = [
            trial
            for trial in report["trials"]
            if trial["test_id"] == "A1_EXPLICIT_CANCEL" and trial.get("trial_complete")
        ]
        baseline_valid = not baseline_trials or all(
            trial.get("outcome_class") == "EXPLICIT_CANCEL_WORKS"
            for trial in baseline_trials
        )
        try:
            report["robot_unregistration"] = unregister_robot(node, robot_id)
            robot_unregistered = True
        except Exception as exc:
            report["robot_unregistration"] = {
                "success": False,
                "robot_id": robot_id,
                "error": f"{type(exc).__name__}: {exc}",
            }
        report["measurement_valid"] = (
            not errors
            and baseline_valid
            and bool(report["robot_unregistration"].get("success"))
        )
        report["probe_pass"] = report["measurement_valid"]
        report["completed_at"] = timestamp()
        report["duration_s"] = elapsed(report["completed_at"], started_at)
        emit_json(report)
        if errors:
            return 1
        if not baseline_valid:
            return 2
        if not report["measurement_valid"]:
            return 1
        return 0
    except Exception as exc:
        report["probe_pass"] = False
        report["measurement_valid"] = False
        report["fatal_error"] = f"{type(exc).__name__}: {exc}"
        report["fatal_traceback"] = traceback.format_exc()
        report["completed_at"] = timestamp()
        report["duration_s"] = elapsed(report["completed_at"], started_at)
        emit_json(report)
        return 1
    finally:
        node.force_cleanup_all()
        time.sleep(0.2)
        node.stop_all.set()
        time.sleep(0.1)
        if robot_id is not None and not robot_unregistered:
            try:
                unregister_robot(node, robot_id)
            except Exception:
                pass
        executor.shutdown(timeout_sec=3.0)
        node.action_server.destroy()
        node.destroy_node()
        rclpy.shutdown()
        spin_thread.join(timeout=3.0)


if __name__ == "__main__":
    sys.exit(main())
