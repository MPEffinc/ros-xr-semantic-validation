#!/usr/bin/env python3
"""M39 SHARED low-level transition core, used identically by B1 (inside the app copy) and C1 (ROS-side node).

It implements only the mechanics both arms need; the decision WHEN to interrupt / re-admit and WHAT the first
target is belongs to each arm (B1: app copy, C1: transition node) and is counted as that arm's own cost.

Ordered stop:   suppress (caller stops publishing)  ->  Servo pause_servo(true)  ->  JTC one-point hold at the
                measured joint state (sent at once, again on the pause ack, again 0.1 s later)  ->  HELD once every
                arm joint speed <= 0.01 rad/s for 0.1 s (measured /joint_states; finite difference if no velocity).
Ordered resume: (caller supplies the first target, already referenced to the measured EE) publish it to Servo while
                Servo is still paused, so Servo's latest_pose_ no longer holds a pre-interruption target  ->  after
                40 ms (2 Servo periods) pause_servo(false)  ->  ACTIVE on the service ack (Servo resets smoothing and
                clears its rolling window on unpause, servo_node.cpp L159-178 @2.12.4).
Measured EE:    tf base_link -> wrist_3_link (the frame Servo tracks), latest available.
Every event is logged with wall_ns (CLOCK_REALTIME) and mono_ns (CLOCK_MONOTONIC)."""
import json, time
from builtin_interfaces.msg import Duration
from sensor_msgs.msg import JointState
from std_srvs.srv import SetBool
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
import rclpy
import tf2_ros

ARM_JOINTS = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint", "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]
SETTLE_SPEED, SETTLE_FOR, REHOLD_AFTER, UNPAUSE_AFTER = 0.01, 0.1, 0.1, 0.04


class TransitionCore:
    def __init__(self, node, log_path, ee_frame="wrist_3_link", base_frame="base_link"):
        self.node, self.ee_frame, self.base_frame = node, ee_frame, base_frame
        self.log_f = open(log_path, "a", buffering=1)
        self.state = "INIT"            # INIT -> HOLDING -> HELD -> RESUMING -> ACTIVE -> HOLDING ...
        self.js = None; self.prev_js = None; self.slow_since = None; self.hold_t = None
        self.pause = node.create_client(SetBool, "/servo_node/pause_servo")
        self.jtc = node.create_publisher(JointTrajectory, "/ur5_arm_controller/joint_trajectory", 10)
        node.create_subscription(JointState, "/joint_states", self._on_js, 50)
        self.tf = tf2_ros.Buffer(); self._tfl = tf2_ros.TransformListener(self.tf, node)
        self._timers = []
        node.create_timer(0.01, self._tick)
        self.epoch = 0

    # ---------- logging / helpers
    def log(self, event, **kw):
        self.log_f.write(json.dumps({"wall_ns": time.time_ns(), "mono_ns": time.monotonic_ns(), "event": event,
                                     "state": self.state, "epoch": self.epoch, **kw}) + "\n")

    def _once(self, delay, fn):
        holder = {}
        def cb():
            holder["t"].cancel(); self._timers.remove(holder["t"]); fn()
        holder["t"] = self.node.create_timer(delay, cb); self._timers.append(holder["t"])

    def _on_js(self, m):
        pos = dict(zip(m.name, m.position)); vel = dict(zip(m.name, m.velocity)) if len(m.velocity) == len(m.name) else {}
        now = time.monotonic()
        if not all(j in pos for j in ARM_JOINTS): return
        q = [pos[j] for j in ARM_JOINTS]
        if vel: v = [vel[j] for j in ARM_JOINTS]
        elif self.js is not None and now > self.js[2]: v = [(a - b) / (now - self.js[2]) for a, b in zip(q, self.js[0])]
        else: v = [0.0] * 6
        self.js = (q, v, now)

    def ee(self):
        try:
            tr = self.tf.lookup_transform(self.base_frame, self.ee_frame, rclpy.time.Time())
        except Exception as e:  # noqa: BLE001
            self.log("ee_lookup_failed", err=type(e).__name__); return None
        t, r = tr.transform.translation, tr.transform.rotation
        return {"p": [t.x, t.y, t.z], "q": [r.x, r.y, r.z, r.w], "stamp_ns": tr.header.stamp.sec * 10**9 + tr.header.stamp.nanosec}

    def _call_pause(self, flag, on_ack=None, tries=0):
        if not self.pause.service_is_ready():
            if tries == 0: self.log("pause_wait_service", data=flag)
            if tries < 200:   # up to 10 s, then give up (logged; the hold still acts at the controller)
                self._once(0.05, lambda: self._call_pause(flag, on_ack, tries + 1))
            else:
                self.log("pause_service_unavailable", data=flag)
            return
        req = SetBool.Request(); req.data = flag
        self.log("pause_call", data=flag)
        fut = self.pause.call_async(req)
        def done(f):
            ok = f.result() is not None and f.result().success
            self.log("pause_ack", data=flag, success=ok, msg=(f.result().message if f.result() is not None else None))
            if on_ack: on_ack(ok)
        fut.add_done_callback(done)

    def hold(self, why):
        if self.js is None:
            self.log("hold_skipped_no_joint_state", why=why); return
        tr = JointTrajectory(); tr.joint_names = ARM_JOINTS
        pt = JointTrajectoryPoint(); pt.positions = list(self.js[0]); pt.velocities = [0.0] * 6
        pt.time_from_start = Duration(sec=0, nanosec=20_000_000); tr.points = [pt]
        self.jtc.publish(tr); self.hold_t = time.monotonic(); self.slow_since = None
        self.log("hold", why=why, positions=list(pt.positions))

    # ---------- arm-facing API
    def interrupt(self, reason):
        """Ordered stop. Idempotent while not ACTIVE/RESUMING/INIT."""
        if self.state in ("HOLDING", "HELD"):
            return
        self.epoch += 1; self.log("interrupt", reason=reason); self.state = "HOLDING"
        ep = self.epoch
        self.hold("interrupt")
        self._call_pause(True, on_ack=lambda ok: (self.state in ("HOLDING", "HELD") and self.epoch == ep) and self.hold("pause_ack"))
        self._once(REHOLD_AFTER, lambda: (self.state in ("HOLDING", "HELD") and self.epoch == ep) and self.hold("rehold"))

    def is_held(self):
        return self.state == "HELD"

    def is_active(self):
        return self.state == "ACTIVE"

    def resume(self, first_msg, publisher, on_active=None):
        """Ordered resume from HELD with an already re-referenced first target."""
        if self.state != "HELD":
            self.log("resume_refused", reason="not_held"); return False
        self.state = "RESUMING"; ep = self.epoch
        publisher.publish(first_msg)
        self.log("first_target_published", p=[first_msg.pose.position.x, first_msg.pose.position.y, first_msg.pose.position.z],
                 q=[first_msg.pose.orientation.x, first_msg.pose.orientation.y, first_msg.pose.orientation.z, first_msg.pose.orientation.w])
        def unpause():
            if self.state != "RESUMING" or self.epoch != ep:
                self.log("unpause_skipped", reason="interrupted_during_resume"); return
            def ack(ok):
                if self.state == "RESUMING" and self.epoch == ep:
                    if ok:
                        self.state = "ACTIVE"; self.log("active")
                        if on_active: on_active()
                    else:
                        self.log("unpause_failed"); self.state = "HELD"
            self._call_pause(False, on_ack=ack)
        self._once(UNPAUSE_AFTER, unpause)
        return True

    def _tick(self):
        if self.state == "HOLDING" and self.js is not None and self.hold_t is None:
            self.hold("retry_after_no_joint_state")
        if self.state == "HOLDING" and self.js is not None and self.hold_t is not None:
            now = time.monotonic()
            if max(abs(v) for v in self.js[1]) <= SETTLE_SPEED:
                if self.slow_since is None: self.slow_since = now
                if now - self.slow_since >= SETTLE_FOR and now - self.hold_t >= REHOLD_AFTER:
                    self.state = "HELD"; self.log("held", q=list(self.js[0]))
            else:
                self.slow_since = None
