#!/usr/bin/env python3
"""M12_receiver gate (component level; nothing downstream). TAU = 0.100 s on the receiver/gate wall ROS clock.
  B0 (original receiver output /received_pose_states): only header.stamp exists (= receiver publish time), so the only
     check is the generic stamp age <= TAU. Provenance of the underlying packet is NOT available ("not checkable").
  B1 (/received_pose_states_prov): neutral states are classified 'neutral_stop' (forwarded as a stop/hold, never as
     motion). Motion is admitted iff rx_stamp age <= TAU and, when the producer supplied seq/session: within a session
     the source seq must not decrease, and a source seq equal to the last admitted one with a different receipt count is a
     duplicate packet (blocked); a new session resets the expectation. If a session that supplied seq stops supplying it,
     the PRIMARY policy is fail-closed (block motion, 'provenance_missing'); the fail-open decision is logged alongside.
Args: <B0|B1> <log> <t0> <end_s>"""
import json, sys, time
import rclpy
from teleop_bridge_msgs.msg import ReceivedPoseStates
from m12r_prov_msgs.msg import ReceivedPoseStatesProv
MODE, LOG, T0, END = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]); TAU = 0.100
rclpy.init(); n = rclpy.create_node("m12r_gate"); out = open(LOG, "w", buffering=1)
st = {"session": None, "last_seq": None, "last_rx": None, "session_had_seq": False}
def ts(t): return t.sec + t.nanosec * 1e-9
def b0(m):
    now = n.get_clock().now().nanoseconds / 1e9; age = now - ts(m.header.stamp)
    out.write(json.dumps({"t": time.time() - T0, "x": m.pose.position.x, "teleop": m.teleop_enable, "source": m.source, "stamp_age": age,
                          "neutral": None, "admit": age <= TAU, "admit_failopen": age <= TAU, "why": "stamp_age" if age > TAU else "ok",
                          "provenance": "absent"}) + "\n")
def b1(p):
    m = p.state; now = n.get_clock().now().nanoseconds / 1e9; rec = {"t": time.time() - T0, "x": m.pose.position.x, "teleop": m.teleop_enable,
        "source": m.source, "stamp_age": now - ts(m.header.stamp), "neutral": p.neutral, "rx_count": p.rx_count,
        "rx_age": (now - ts(p.rx_stamp)) if p.rx_count else None, "src_seq": p.src_seq if p.src_seq_valid else None, "session": p.src_session}
    if p.neutral:
        ok = fo = False; why = "neutral_stop"
    elif not p.rx_count or rec["rx_age"] > TAU:
        ok = fo = False; why = "rx_age"
    elif p.src_seq_valid:
        if p.src_session != st["session"]:
            st.update(session=p.src_session, last_seq=None, last_rx=None)
        st["session_had_seq"] = True
        if st["last_seq"] is not None and (p.src_seq < st["last_seq"] or (p.src_seq == st["last_seq"] and p.rx_count != st["last_rx"])):
            ok = fo = False; why = "seq_regress_or_duplicate"
        else:
            ok = fo = True; why = "ok"; st.update(last_seq=p.src_seq, last_rx=p.rx_count)
    else:
        fo = True
        ok = not st["session_had_seq"]; why = "provenance_missing" if not ok else "ok_no_seq"
    rec.update(admit=ok, admit_failopen=fo, why=why, provenance="present"); out.write(json.dumps(rec) + "\n")
if MODE == "B0": n.create_subscription(ReceivedPoseStates, "/received_pose_states", b0, 100)
else: n.create_subscription(ReceivedPoseStatesProv, "/received_pose_states_prov", b1, 100)
while time.time() - T0 < END: rclpy.spin_once(n, timeout_sec=0.01)
