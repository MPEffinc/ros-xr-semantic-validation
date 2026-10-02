#!/usr/bin/env python3
"""M39 C1: ROS-side transition component; the app is UNMODIFIED (remapped to /m39/app_cmd).

Inputs it has: the app's PoseStamped stream, runtime evidence (libmonado collector, shared reader), tf, /joint_states.
Inputs it does NOT have: the grip button (libmonado exposes no input values; this app publishes no button topic).

Interruption   = runtime evidence not ok (stale > 50 ms, or not FOCUSED/IO_ACTIVE, or INPUTS_BLOCKED) or app command
                 silence > 100 ms  ->  stop forwarding + shared ordered stop (pause, hold, settle).
Re-admission   = HELD, evidence ok, and app commands flowing with every gap <= 100 ms for >= 100 ms.
Re-basing      = command-semantics adapter for this app (pose targets in base_link, positions additive in the base
                 frame, rotations composed as R_target = R_anchor * R_hand_relative):
                   dp = p_EE - p_first ;  C = R_EE * R_first^-1
                   p' = p + dp ;  R' = C * R   (= R_EE * (R_first^-1 * R): hand-relative rotation since re-admission
                 applied in the same order the app uses). Positions are NOT rotated by C (a full SE(3) left
                 product C*T would rotate later translations; see host test). Fixed until the next interruption.
Args: <arm_log.jsonl> <ev_fifo> <end_s>   env P1_T0_NS"""
import os, sys, time
import rclpy
from geometry_msgs.msg import PoseStamped
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, os.environ.get("M39_HARNESS", "/m39/harness"))
from m39_transition import TransitionCore
from m39_evidence import Evidence

SILENCE, FLOW_FOR = 0.100, 0.100


class Rebase:
    def __init__(self, ee, first):
        self.dp = [ee["p"][i] - first["p"][i] for i in range(3)]
        self.C = R.from_quat(ee["q"]) * R.from_quat(first["q"]).inv()

    def apply(self, p, q):
        return [p[i] + self.dp[i] for i in range(3)], list((self.C * R.from_quat(q)).as_quat())


def pq(m):
    return [m.pose.position.x, m.pose.position.y, m.pose.position.z], [m.pose.orientation.x, m.pose.orientation.y,
                                                                       m.pose.orientation.z, m.pose.orientation.w]


def main():
    log_path, fifo, end_s = sys.argv[1], sys.argv[2], float(sys.argv[3])
    t0 = int(os.environ["P1_T0_NS"]) / 1e9
    rclpy.init(); node = rclpy.create_node("m39_c1_transition")
    core = TransitionCore(node, log_path); ev = Evidence(fifo)
    pub = node.create_publisher(PoseStamped, "/servo_node/pose_target_cmds", 10)
    st = {"rebase": None, "last_cmd": None, "flow_since": None, "latest": None, "fwd": 0, "drop": 0, "prev_tick": 0.0}

    def forward(m):
        p, q = pq(m); p2, q2 = st["rebase"].apply(p, q)
        o = PoseStamped(); o.header = m.header
        o.pose.position.x, o.pose.position.y, o.pose.position.z = p2
        o.pose.orientation.x, o.pose.orientation.y, o.pose.orientation.z, o.pose.orientation.w = q2
        return o

    def on_cmd(m):
        now = time.time(); ok, age, _, _, bad = ev.state()
        if bad is not None and st["last_cmd"] is not None and bad > st["last_cmd"]: ok = False  # deactivation since last cmd
        prev = st["last_cmd"]; st["last_cmd"] = now; st["latest"] = m
        if prev is None or now - prev > SILENCE or not ok:
            st["flow_since"] = now if ok else None
        elif st["flow_since"] is None:
            st["flow_since"] = now
        if core.state in ("ACTIVE", "RESUMING") and ok and st["rebase"] is not None:
            pub.publish(forward(m)); st["fwd"] += 1
        else:
            st["drop"] += 1
            if core.state in ("ACTIVE", "RESUMING") and not ok:
                core.interrupt("evidence_not_ok")

    def tick():
        now = time.time(); ok, age, fo, fl, bad = ev.state()
        if bad is not None and bad > st["prev_tick"]: ok = False  # latch anything since the previous tick
        st["prev_tick"] = now
        if not ok:
            st["flow_since"] = None
        if core.state == "INIT":
            core.interrupt("startup"); return
        if core.state in ("ACTIVE", "RESUMING"):
            if not ok:
                core.interrupt("evidence_not_ok"); return
            if st["last_cmd"] is None or now - st["last_cmd"] > SILENCE:
                core.interrupt("command_silence"); return
        if core.is_held() and ok and st["flow_since"] is not None and st["last_cmd"] is not None \
                and now - st["last_cmd"] <= SILENCE and now - st["flow_since"] >= FLOW_FOR:
            ee = core.ee()
            if ee is None: return
            first = st["latest"]; fp, fq = pq(first)
            st["rebase"] = Rebase(ee, {"p": fp, "q": fq})
            core.log("c1_readmit", ev_age=age, ev_flags=fl, first_p=fp, first_q=fq, ee_p=ee["p"], ee_q=ee["q"],
                     dp=st["rebase"].dp, C=list(st["rebase"].C.as_quat()))
            core.resume(forward(first), pub)
        if now - t0 > end_s:
            core.log("final", forwarded=st["fwd"], dropped=st["drop"]); raise SystemExit(0)

    node.create_subscription(PoseStamped, "/m39/app_cmd", on_cmd, 50)
    node.create_timer(0.005, tick)
    try:
        rclpy.spin(node)
    except (SystemExit, KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == "__main__":
    main()
