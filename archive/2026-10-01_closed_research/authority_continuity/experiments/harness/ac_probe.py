#!/usr/bin/env python3
"""Authority-transition probe for HORUS (authority_continuity PHASE 6).

Two HorusLink clients (A, B) talk to the HORUS bridge exactly like the MR app's
protocol does; the robot plant is the official Nav2 TB3 loopback simulation.
The probe only observes ROS; it never modifies HORUS.  The HorusLink framing
client is imported read-only from the archived testbed
(Deprecated/authorization_env/horus_runtime_probe.py, hash recorded by the runner).

Output: one JSON object per trial (JSONL) with a monotonic timeline and the
per-trial measurements used by analyze.py.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import threading
import time
import uuid
from typing import Any, Callable

sys.path.insert(0, "/deprecated_env")

import rclpy  # noqa: E402
from action_msgs.msg import GoalStatus, GoalStatusArray  # noqa: E402
from action_msgs.srv import CancelGoal  # noqa: E402
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, Twist  # noqa: E402
from horus_interfaces.srv import RegisterRobot  # noqa: E402
from rclpy.callback_groups import ReentrantCallbackGroup  # noqa: E402
from rclpy.executors import MultiThreadedExecutor  # noqa: E402
from rclpy.node import Node  # noqa: E402
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy  # noqa: E402
from rclpy.serialization import serialize_message  # noqa: E402
from std_msgs.msg import String  # noqa: E402

import horus_runtime_probe as hl  # noqa: E402  (archived, read-only)

ROBOT = hl.ROBOT  # "robot1"
GOAL_TOPIC = f"/{ROBOT}/goal_pose"
CANCEL_TOPIC = f"/{ROBOT}/goal_cancel"
STATUS_TOPIC = f"/{ROBOT}/goal_status"
TELEOP_TOPIC = f"/{ROBOT}/cmd_vel"  # observed only; the loopback plant listens on /cmd_vel
NAV2_ACTION = "/navigate_to_pose"
START = (-2.0, -0.5)
GOAL_A = (1.5, -0.5)
GOAL_B = (-1.5, 1.0)
TERMINAL = {GoalStatus.STATUS_SUCCEEDED: "SUCCEEDED", GoalStatus.STATUS_CANCELED: "CANCELED",
            GoalStatus.STATUS_ABORTED: "ABORTED"}
STATUS_NAME = {0: "UNKNOWN", 1: "ACCEPTED", 2: "EXECUTING", 3: "CANCELING", 4: "SUCCEEDED",
               5: "CANCELED", 6: "ABORTED"}
T0 = time.monotonic()


def now() -> float:
    return round(time.monotonic() - T0, 4)


def wait_for(pred: Callable[[], bool], timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.02)
    return pred()


class Observer(Node):
    def __init__(self) -> None:
        super().__init__("ac_observer")
        self.cb = ReentrantCallbackGroup()
        self.lock = threading.Lock()
        self.events: list[dict[str, Any]] = []
        self.goal_state: dict[str, int] = {}
        self.goal_first_seen: dict[str, float] = {}
        self.goal_first_active: dict[str, bool] = {}
        state_qos = QoSProfile(depth=50, reliability=ReliabilityPolicy.RELIABLE,
                               durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(String, "/horus/multi_operator/control_lease_state",
                                 self._on_lease, state_qos, callback_group=self.cb)
        self.create_subscription(GoalStatusArray, f"{NAV2_ACTION}/_action/status",
                                 self._on_status, 50, callback_group=self.cb)
        self.create_subscription(PoseStamped, GOAL_TOPIC, self._on_goal_topic, 50,
                                 callback_group=self.cb)
        self.create_subscription(String, CANCEL_TOPIC, self._on_cancel_topic, 50,
                                 callback_group=self.cb)
        self.create_subscription(String, STATUS_TOPIC, self._on_horus_status, 50,
                                 callback_group=self.cb)
        self.create_subscription(Twist, TELEOP_TOPIC, self._on_teleop, 200, callback_group=self.cb)
        self.create_subscription(Twist, "/cmd_vel", self._on_plant_cmd, 200, callback_group=self.cb)
        self.initpose_pub = self.create_publisher(PoseWithCovarianceStamped, "/initialpose", 10)
        self.cancel_cli = self.create_client(CancelGoal, f"{NAV2_ACTION}/_action/cancel_goal",
                                             callback_group=self.cb)

    def log(self, kind: str, **data: Any) -> None:
        with self.lock:
            self.events.append({"t": now(), "kind": kind, **data})

    def reset_trial(self) -> None:
        with self.lock:
            self.events = []

    def _on_lease(self, m: String) -> None:
        try:
            s = json.loads(m.data)
        except json.JSONDecodeError:
            return
        holders = [(x.get("robot_name"), x.get("holder_app_id")) for x in s.get("leases", [])]
        self.log("lease_state", event=s.get("event"), request_id=s.get("request_id"),
                 denied_reason=s.get("denied_reason"), holders=holders)

    def _on_status(self, m: GoalStatusArray) -> None:
        for st in m.status_list:
            gid = bytes(st.goal_info.goal_id.uuid).hex()
            with self.lock:
                prev = self.goal_state.get(gid)
                if gid not in self.goal_first_seen:
                    self.goal_first_seen[gid] = now()
                    # Status arrays also list old, already-terminal goals (retained results from
                    # earlier trials/baselines); only goals first seen in an active state are new.
                    self.goal_first_active[gid] = st.status in (1, 2)
                self.goal_state[gid] = st.status
            if prev != st.status:
                self.log("nav2_goal", goal=gid[:12], status=STATUS_NAME.get(st.status, st.status))

    def _on_goal_topic(self, m: PoseStamped) -> None:
        self.log("ros_goal_pose", x=round(m.pose.position.x, 3), y=round(m.pose.position.y, 3))

    def _on_cancel_topic(self, m: String) -> None:
        self.log("ros_goal_cancel", data=m.data)

    def _on_horus_status(self, m: String) -> None:
        self.log("horus_goal_status", data=m.data)

    def _on_teleop(self, m: Twist) -> None:
        self.log("ros_teleop", x=round(m.linear.x, 3))

    def _on_plant_cmd(self, m: Twist) -> None:
        moving = abs(m.linear.x) > 1e-3 or abs(m.angular.z) > 1e-3
        self.log("plant_cmd", moving=moving)

    # helpers ---------------------------------------------------------------
    def active_goals(self) -> list[str]:
        with self.lock:
            return [g for g, s in self.goal_state.items() if s in (1, 2, 3)]

    def goals_seen_after(self, t: float) -> list[str]:
        with self.lock:
            return sorted((g for g, ts in self.goal_first_seen.items()
                           if ts >= t and self.goal_first_active.get(g)),
                          key=lambda g: self.goal_first_seen[g])

    def status_of(self, gid: str) -> int | None:
        with self.lock:
            return self.goal_state.get(gid)

    def cancel_all(self) -> None:
        if not self.cancel_cli.wait_for_service(timeout_sec=3.0):
            return
        fut = self.cancel_cli.call_async(CancelGoal.Request())  # zero id + zero stamp = all
        wait_for(fut.done, 3.0)

    def set_start_pose(self) -> None:
        msg = PoseWithCovarianceStamped()
        msg.header.frame_id = "map"
        msg.pose.pose.position.x, msg.pose.pose.position.y = START
        msg.pose.pose.orientation.w = 1.0
        for _ in range(5):
            msg.header.stamp = self.get_clock().now().to_msg()
            self.initpose_pub.publish(msg)
            time.sleep(0.1)


class Client(hl.HorusLinkClient):
    """Archived HorusLink client plus the XR operations used by the HORUS app protocol."""

    def __init__(self, label: str, obs: Observer) -> None:
        super().__init__(label, int.from_bytes(uuid.uuid4().bytes[:7], "little") | 1)
        self.obs = obs
        self.app_id = f"app-{label}"
        self.hb_stop = threading.Event()
        self.hb_thread: threading.Thread | None = None
        self.stream_stop = threading.Event()

    def open(self) -> None:
        self.connect()
        for ch, topic, typ in ((1, hl.CATALOG_TOPIC, "std_msgs/msg/String"),
                               (2, hl.LEASE_TOPIC, "std_msgs/msg/String"),
                               (3, TELEOP_TOPIC, "geometry_msgs/msg/Twist"),
                               (4, GOAL_TOPIC, "geometry_msgs/msg/PoseStamped"),
                               (5, CANCEL_TOPIC, "std_msgs/msg/String")):
            self.register_publisher(ch, topic, typ)
        self.obs.log("client_open", client=self.label)

    def lease(self, action: str, rid: str) -> None:
        self.publish_json_string(hl.LEASE_TOPIC, {
            "request_id": rid, "robot_name": ROBOT, "app_id": self.app_id, "role": "operator",
            "session_id": f"sess-{self.label}", "action": action, "panel_open": True,
            "teleop_active": False, "task_active": True, "task_kind": "navigation"})
        self.obs.log("xr_lease_" + action, client=self.label, request_id=rid)

    def start_heartbeat(self, period: float = 0.3) -> None:
        self.hb_stop.clear()

        def run() -> None:
            n = 0
            while not self.hb_stop.wait(period):
                n += 1
                try:
                    self.lease("heartbeat", f"{self.label}-hb-{n}")
                except OSError:
                    return
        self.hb_thread = threading.Thread(target=run, daemon=True)
        self.hb_thread.start()

    def stop_heartbeat(self) -> None:
        self.hb_stop.set()
        if self.hb_thread:
            self.hb_thread.join(timeout=1.0)

    def catalog(self, op: str, robots: bool = True) -> None:  # type: ignore[override]
        payload: dict[str, Any] = {"role": "host", "op": op, "session_id": "ac-session"}
        if robots:
            payload["robots"] = [{"robot_name": ROBOT, "teleop_command_topic": TELEOP_TOPIC,
                                  "go_to_goal_topic": GOAL_TOPIC,
                                  "go_to_cancel_topic": CANCEL_TOPIC}]
        self.publish_json_string(hl.CATALOG_TOPIC, payload)
        self.obs.log("xr_catalog", client=self.label, op=op)

    def goal(self, xy: tuple[float, float], tag: str) -> None:
        m = PoseStamped()
        m.header.frame_id = "map"
        m.pose.position.x, m.pose.position.y = xy
        m.pose.orientation.w = 1.0
        self.publish_serialized(GOAL_TOPIC, bytes(serialize_message(m)), False)
        self.obs.log("xr_goal", client=self.label, tag=tag, x=xy[0], y=xy[1])

    def cancel(self) -> None:
        m = String()
        m.data = "cancel"
        self.publish_serialized(CANCEL_TOPIC, bytes(serialize_message(m)), False)  # bridge re-adds CDR header (topic_manager.cpp:535-537)
        self.obs.log("xr_cancel", client=self.label)

    def twist(self, x: float) -> None:
        m = Twist()
        m.linear.x = x
        self.publish_serialized(TELEOP_TOPIC, bytes(serialize_message(m)), False)

    def shut(self) -> None:
        self.stop_heartbeat()
        self.stream_stop.set()
        self.close()
        self.obs.log("client_closed", client=self.label)


def lease_event(obs: Observer, event: str, rid: str | None = None, after: float = 0.0) -> bool:
    with obs.lock:
        return any(e["kind"] == "lease_state" and e["event"] == event and e["t"] >= after and
                   (rid is None or e.get("request_id") == rid) for e in obs.events)


def first(obs: Observer, pred: Callable[[dict[str, Any]], bool]) -> float | None:
    with obs.lock:
        for e in obs.events:
            if pred(e):
                return e["t"]
    return None


def count(obs: Observer, pred: Callable[[dict[str, Any]], bool]) -> int:
    with obs.lock:
        return sum(1 for e in obs.events if pred(e))


def moving_after(obs: Observer, t: float, window: float = 0.5) -> bool:
    """True if the Nav2 controller commanded motion in [t, t+window]."""
    return count(obs, lambda e: e["kind"] == "plant_cmd" and e["moving"] and
                 t <= e["t"] <= t + window) > 0


def start_goal(obs: Observer, c: Client, xy: tuple[float, float], tag: str) -> str | None:
    t = now()
    c.goal(xy, tag)
    ok = wait_for(lambda: bool(obs.goals_seen_after(t)), 6.0)
    if not ok:
        return None
    gid = obs.goals_seen_after(t)[0]
    wait_for(lambda: obs.status_of(gid) == GoalStatus.STATUS_EXECUTING, 4.0)
    return gid


def gid_status(obs: Observer, gid: str | None) -> str | None:
    if gid is None:
        return None
    s = obs.status_of(gid)
    return STATUS_NAME.get(s, str(s)) if s is not None else None


def terminal_time(obs: Observer, gid: str | None, after: float) -> tuple[str | None, float | None]:
    if gid is None:
        return None, None
    with obs.lock:
        for e in obs.events:
            if (e["kind"] == "nav2_goal" and e["goal"] == gid[:12] and e["t"] >= after and
                    e["status"] in ("SUCCEEDED", "CANCELED", "ABORTED")):
                return e["status"], round(e["t"] - after, 4)
    return None, None


# ---------------------------------------------------------------------------
# Cases.  Each returns a dict of measurements; verdicts are computed in analyze.py
# against the pre-registered criteria in experiments/PROTOCOL.md.
# ---------------------------------------------------------------------------

def acquire(obs: Observer, c: Client, rid: str) -> bool:
    t = now()
    c.lease("acquire", rid)
    return wait_for(lambda: lease_event(obs, "lease_granted", rid, t) or
                    lease_event(obs, "lease_updated", rid, t), 2.0)


def case_c1_normal(obs: Observer, a: Client, b: Client) -> dict[str, Any]:
    r: dict[str, Any] = {}
    r["a_granted"] = acquire(obs, a, "c1-a")
    a.start_heartbeat()
    t = now()
    b.lease("acquire", "c1-b")
    r["b_denied"] = wait_for(lambda: lease_event(obs, "lease_denied", "c1-b", t), 2.0)
    ga = start_goal(obs, a, GOAL_A, "A1")
    r["a_goal_executing"] = gid_status(obs, ga) == "EXECUTING"
    t = now()
    b.goal(GOAL_B, "B-during-A")
    time.sleep(0.8)
    r["b_goal_reached_ros"] = count(obs, lambda e: e["kind"] == "ros_goal_pose" and
                                    e["x"] == GOAL_B[0] and e["t"] >= t) > 0
    r["a_goal_status_after_b_attempt"] = gid_status(obs, ga)
    t = now()
    a.cancel()
    wait_for(lambda: gid_status(obs, ga) in ("CANCELED", "ABORTED", "SUCCEEDED"), 4.0)
    r["a_cancel_terminal"], r["a_cancel_latency_s"] = terminal_time(obs, ga, t)
    return r


def _lease_end_case(obs: Observer, a: Client, b: Client, how: str) -> dict[str, Any]:
    r: dict[str, Any] = {"how": how}
    r["a_granted"] = acquire(obs, a, f"{how}-a")
    a.start_heartbeat()
    ga = start_goal(obs, a, GOAL_A, "A1")
    r["a_goal_executing"] = gid_status(obs, ga) == "EXECUTING"
    time.sleep(1.0)
    t_end = now()
    if how == "release":
        a.stop_heartbeat()
        a.lease("release", f"{how}-rel")
        wait_for(lambda: lease_event(obs, "lease_released", f"{how}-rel", t_end), 2.0)
    elif how == "ttl":
        a.stop_heartbeat()  # client stays connected, lease must expire (ttl param)
        wait_for(lambda: lease_event(obs, "lease_expired", None, t_end), 4.0)
    elif how == "disconnect":
        a.shut()
        wait_for(lambda: lease_event(obs, "client_disconnected_release", None, t_end), 3.0)
    r["lease_end_observed_s"] = (lambda x: None if x is None else round(x - t_end, 4))(
        first(obs, lambda e: e["kind"] == "lease_state" and e["t"] >= t_end and
              e["event"] in ("lease_released", "lease_expired", "client_disconnected_release")))
    time.sleep(3.0)
    r["cancel_msgs_on_ros_after_end"] = count(obs, lambda e: e["kind"] == "ros_goal_cancel" and
                                              e["t"] >= t_end)
    r["a_goal_terminal"], r["a_goal_terminal_latency_s"] = terminal_time(obs, ga, t_end)
    r["a_goal_status_end_plus_3s"] = gid_status(obs, ga)
    r["plant_moving_end_plus_2_5s"] = moving_after(obs, t_end + 2.5)
    if how in ("release", "ttl"):
        # Previous holder, now without a lease, sends a new goal (stale admission).
        t = now()
        a.goal(GOAL_B, "A-after-end")
        time.sleep(1.0)
        r["stale_goal_reached_ros"] = count(obs, lambda e: e["kind"] == "ros_goal_pose" and
                                            e["x"] == GOAL_B[0] and e["t"] >= t) > 0
    if how == "disconnect":
        # Reconnection: a new connection for the same operator re-acquires and cancels.
        a2 = Client("A", obs)
        a2.open()
        r["a2_granted"] = acquire(obs, a2, "disc-a2")
        active_before = obs.active_goals()
        r["goal_still_active_at_reconnect"] = bool(active_before)
        t = now()
        a2.cancel()
        wait_for(lambda: not obs.active_goals(), 4.0)
        r["a2_cancel_terminal"], r["a2_cancel_latency_s"] = terminal_time(obs, ga, t)
        a2.shut()
    return r


def case_c2_release(obs, a, b):
    return _lease_end_case(obs, a, b, "release")


def case_c3_ttl(obs, a, b):
    return _lease_end_case(obs, a, b, "ttl")


def case_c4_disconnect(obs, a, b):
    return _lease_end_case(obs, a, b, "disconnect")


def _handoff(obs: Observer, a: Client, b: Client, fast: bool) -> dict[str, Any]:
    r: dict[str, Any] = {"fast": fast}
    r["a_granted"] = acquire(obs, a, "h-a")
    a.start_heartbeat()
    ga = start_goal(obs, a, GOAL_A, "A1")
    r["a_goal_executing"] = gid_status(obs, ga) == "EXECUTING"
    time.sleep(1.0)
    a.stop_heartbeat()
    t_rel = now()
    a.lease("release", "h-a-rel")
    if fast:
        b.lease("acquire", "h-b")  # back-to-back, no wait for grant
        t_bgoal = now()
        b.goal(GOAL_B, "B1")
        r["b_granted"] = wait_for(lambda: lease_event(obs, "lease_granted", "h-b", t_rel), 2.0)
    else:
        wait_for(lambda: lease_event(obs, "lease_released", "h-a-rel", t_rel), 2.0)
        r["b_granted"] = acquire(obs, b, "h-b")
        t_bgoal = now()
        b.goal(GOAL_B, "B1")
    b.start_heartbeat()
    wait_for(lambda: bool([g for g in obs.goals_seen_after(t_bgoal) if g != ga]), 6.0)
    new = [g for g in obs.goals_seen_after(t_bgoal) if g != ga]
    gb = new[0] if new else None
    r["b_goal_reached_ros"] = gb is not None
    wait_for(lambda: gid_status(obs, gb) in ("EXECUTING", "CANCELED", "ABORTED", "SUCCEEDED"),
             4.0)
    time.sleep(1.5)
    r["a_goal_final_before_b_cancel"] = gid_status(obs, ga)
    r["b_goal_status_before_b_cancel"] = gid_status(obs, gb)
    r["b_goal_terminated_before_b_cancel"] = r["b_goal_status_before_b_cancel"] in (
        "CANCELED", "ABORTED")
    t_c = now()
    b.cancel()
    wait_for(lambda: gid_status(obs, gb) in ("CANCELED", "ABORTED", "SUCCEEDED"), 3.0)
    r["b_cancel_terminal"], r["b_cancel_latency_s"] = terminal_time(obs, gb, t_c)
    r["plant_moving_after_b_cancel_2_5s"] = moving_after(obs, t_c + 2.5)
    r["horus_status_after_b_cancel"] = [e["data"] for e in obs.events
                                        if e["kind"] == "horus_goal_status" and e["t"] >= t_c]
    return r


def case_c5_handoff(obs, a, b):
    return _handoff(obs, a, b, fast=False)


def case_c5f_handoff_fast(obs, a, b):
    return _handoff(obs, a, b, fast=True)


def case_c6_catalog(obs: Observer, a: Client, b: Client) -> dict[str, Any]:
    r: dict[str, Any] = {}
    r["a_granted"] = acquire(obs, a, "c6-a")
    a.start_heartbeat()
    t = now()
    b.goal(GOAL_B, "B-before-change")
    time.sleep(0.8)
    r["b_goal_reached_ros_before_change"] = count(obs, lambda e: e["kind"] == "ros_goal_pose" and
                                                  e["x"] == GOAL_B[0] and e["t"] >= t) > 0
    b.catalog("remove")  # B asserts role "host" and removes robot1's protected topics
    time.sleep(0.4)
    t = now()
    gb = start_goal(obs, b, GOAL_B, "B-after-change")
    r["b_goal_reached_ros_after_change"] = count(obs, lambda e: e["kind"] == "ros_goal_pose" and
                                                 e["x"] == GOAL_B[0] and e["t"] >= t) > 0
    r["b_goal_nav2_status"] = gid_status(obs, gb)
    r["a_still_holder"] = not lease_event(obs, "lease_released", None, 0.0)
    return r


def case_c7_stream(obs: Observer, a: Client, b: Client) -> dict[str, Any]:
    r: dict[str, Any] = {}
    r["a_granted"] = acquire(obs, a, "c7-a")
    a.start_heartbeat()

    def stream() -> None:
        while not a.stream_stop.wait(0.05):
            try:
                a.twist(0.123)
            except OSError:
                return
    th = threading.Thread(target=stream, daemon=True)
    th.start()
    time.sleep(1.0)
    t_rel = now()
    a.stop_heartbeat()
    a.lease("release", "c7-rel")
    time.sleep(2.0)
    a.stream_stop.set()
    th.join(timeout=1.0)
    r["teleop_msgs_before_release"] = count(obs, lambda e: e["kind"] == "ros_teleop" and
                                            e["t"] < t_rel)
    r["teleop_msgs_after_release_plus_0_2s"] = count(obs, lambda e: e["kind"] == "ros_teleop" and
                                                     e["t"] >= t_rel + 0.2)
    return r


CASES = {
    "C1_normal": case_c1_normal,
    "C2_release_executing": case_c2_release,
    "C3_ttl_expiry_executing": case_c3_ttl,
    "C4_disconnect_reconnect": case_c4_disconnect,
    "C5_handoff": case_c5_handoff,
    "C5F_handoff_back_to_back": case_c5f_handoff_fast,
    "C6_catalog_change_during_lease": case_c6_catalog,
    "C7_teleop_stream_after_release": case_c7_stream,
}


def register(obs: Observer) -> str:
    cli = obs.create_client(RegisterRobot, "/horus/register_robot", callback_group=obs.cb)
    if not cli.wait_for_service(timeout_sec=10.0):
        raise RuntimeError("register_robot unavailable")
    req = RegisterRobot.Request()
    req.robot_config.name = ROBOT
    req.robot_config.robot_type = "wheeled"
    req.robot_config.control_topics = [TELEOP_TOPIC, GOAL_TOPIC]
    req.robot_config.metadata_keys = ["horus.backend.nav2_action_topic", "horus.backend.goal_topic",
                                      "horus.backend.cancel_topic", "horus.backend.status_topic"]
    req.robot_config.metadata_values = [NAV2_ACTION, GOAL_TOPIC, CANCEL_TOPIC, STATUS_TOPIC]
    fut = cli.call_async(req)
    wait_for(fut.done, 10.0)
    res = fut.result()
    if res is None or not res.success:
        raise RuntimeError("robot registration failed")
    return res.robot_id


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--cases", default=",".join(CASES))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rclpy.init()
    obs = Observer()
    ex = MultiThreadedExecutor(num_threads=8)
    ex.add_node(obs)
    threading.Thread(target=ex.spin, daemon=True).start()
    robot_id = register(obs)
    time.sleep(1.0)
    rc = 0
    with open(args.out, "a", encoding="utf-8") as out:
        for case in args.cases.split(","):
            for trial in range(1, args.trials + 1):
                obs.cancel_all()
                wait_for(lambda: not obs.active_goals(), 5.0)
                obs.set_start_pose()
                time.sleep(1.0)
                obs.reset_trial()
                a, b = Client("A", obs), Client("B", obs)
                rec: dict[str, Any] = {"baseline": args.baseline, "case": case, "trial": trial,
                                       "robot_id": robot_id, "started_monotonic": now()}
                try:
                    a.open()
                    b.open()
                    a.catalog("snapshot")
                    time.sleep(0.3)
                    rec["measurements"] = CASES[case](obs, a, b)
                    rec["error"] = None
                except Exception as exc:  # recorded, not hidden
                    rec["measurements"] = None
                    rec["error"] = f"{type(exc).__name__}: {exc}"
                    rc = 1
                finally:
                    for c in (a, b):
                        try:
                            c.shut()
                        except Exception:
                            pass
                time.sleep(0.5)
                with obs.lock:
                    rec["timeline"] = list(obs.events)
                out.write(json.dumps(rec, sort_keys=True) + "\n")
                out.flush()
                print(f"[{args.baseline}] {case} #{trial} error={rec['error']} "
                      f"m={json.dumps(rec['measurements'], sort_keys=True)}", flush=True)
                time.sleep(1.6)  # > lease TTL so no lease survives into the next trial
    obs.cancel_all()
    rclpy.shutdown()
    return rc


if __name__ == "__main__":
    sys.exit(main())
