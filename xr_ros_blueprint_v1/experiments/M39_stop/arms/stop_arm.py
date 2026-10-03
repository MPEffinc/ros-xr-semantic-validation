#!/usr/bin/env python3
"""M39_stop stop-only arms (R10). The app is UNMODIFIED and publishes to Servo directly; this node only reacts to the
runtime evidence (same libmonado collector, reader and freshness as M39 C1: ok = fresh <= 50 ms, FOCUSED, IO_ACTIVE,
not INPUTS_BLOCKED, latched between 5 ms ticks). It never resumes (stop policy only).
  HOLD        shared M39 core: pause_servo(true) + JTC one-point hold at the measured joint positions (sent at once,
              on the pause ack, and 0.1 s later)                                    [existing measured-state hold, P1b]
  DECEL_TOPIC same schedule, but each "hold" is a constant-deceleration stop trajectory computed from the measured
              joint positions AND velocities with the formula of JTC 4.42.1 decelerate_to_hold_position()
              (joint_trajectory_controller.cpp L1852-1925): t_stop = |v0|/a, p_hold = p0 + sign(v0) v0^2/(2a), points
              every controller period (0.01 s), a = max_acceleration from the deployment's joint_limits.yaml (3.0 rad/s^2).
              This is an EXTERNAL re-implementation sent on the topic; it is not JTC's internal cancel path.
Args: <mode> <arm_log.jsonl> <ev_fifo> <end_s>   env P1_T0_NS, M39_HARNESS"""
import os, sys, time
import rclpy
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
sys.path.insert(0, os.environ.get("M39_HARNESS", "/m39/harness"))
from m39_transition import TransitionCore, ARM_JOINTS
from m39_evidence import Evidence

A_MAX, DT = 3.0, 0.01


class DecelCore(TransitionCore):
    def hold(self, why):
        if self.js is None:
            self.log("hold_skipped_no_joint_state", why=why); return
        p0, v0 = list(self.js[0]), list(self.js[1])
        t_stop = [abs(v) / A_MAX for v in v0]; tmax = max(t_stop)
        n = int(max(1, round(tmax / DT + 0.5))) + 1
        tr = JointTrajectory(); tr.joint_names = ARM_JOINTS
        hold = [p + (1 if v >= 0 else -1) * v * v / (2 * A_MAX) for p, v in zip(p0, v0)]
        for k in range(n):
            t = k * DT; pt = JointTrajectoryPoint(); pos, vel = [], []
            for i in range(6):
                if t < t_stop[i] and abs(v0[i]) > 1e-7:
                    s = 1 if v0[i] >= 0 else -1
                    pos.append(p0[i] + v0[i] * t - 0.5 * s * A_MAX * t * t); vel.append(max(0.0, (v0[i] - s * A_MAX * t) * s) * s)
                else:
                    pos.append(hold[i]); vel.append(0.0)
            pt.positions = pos; pt.velocities = vel
            ns = int(round(t * 1e9)) if k else 0
            pt.time_from_start = Duration(sec=ns // 10**9, nanosec=ns % 10**9); tr.points.append(pt)
        if n == 1:   # already stopped: same as a hold, keep 20 ms like the hold message
            tr.points[0].time_from_start = Duration(sec=0, nanosec=20_000_000)
        self.jtc.publish(tr); self.hold_t = time.monotonic(); self.slow_since = None
        self.log("hold", why=why, kind="decel", positions=p0, velocities=v0, t_stop_max=tmax, points=len(tr.points), hold_pos=hold)


def main():
    mode, log_path, fifo, end_s = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
    t0 = int(os.environ["P1_T0_NS"]) / 1e9
    rclpy.init(); node = rclpy.create_node("m39_stop_arm")
    core = (DecelCore if mode == "DECEL_TOPIC" else TransitionCore)(node, log_path)
    core.state = "ACTIVE"   # Servo starts unpaused; this arm does not gate engagement
    ev = Evidence(fifo); st = {"armed": False, "prev": 0.0, "done": False}
    core.log("mode", mode=mode, a_max=A_MAX if mode == "DECEL_TOPIC" else None)
    def tick():
        now = time.time(); ok, age, fo, fl, bad = ev.state()
        if bad is not None and bad > st["prev"]: ok = False
        st["prev"] = now
        if not st["armed"] and ok and now - t0 > 1.0:
            st["armed"] = True; core.log("armed", ev_age=age)
        if st["armed"] and not st["done"] and not ok:
            st["done"] = True; core.log("trigger", ev_age=age, ev_flags=fl); core.interrupt("evidence_not_ok")
        if now - t0 > end_s:
            core.log("final"); raise SystemExit(0)
    node.create_timer(0.005, tick)
    try: rclpy.spin(node)
    except (SystemExit, KeyboardInterrupt, rclpy.executors.ExternalShutdownException): pass


if __name__ == "__main__":
    main()
