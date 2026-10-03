#!/usr/bin/env python3
"""M12 gate arms (R11), between /m12/bridge_out and Servo. The same age policy TAU = 0.100 s (sim clock) for A1 and A2.
  A0  pass-through (original behaviour: only Servo's own incoming_command_timeout (0.5 s) on header.stamp applies)
  A1  generic timestamp check: admit iff (now - header.stamp) <= TAU at receive
  A2  provenance check (needs the A2 app copy): admit iff acquisition age (now - acq) <= TAU and valid == 1 and
      seq > last admitted seq (strictly increasing; a repeated or older read is not admitted)
  A3  independent runtime-state check (no app change): admit iff runtime evidence ok at receive (shared M39 reader,
      fresh <= 50 ms, FOCUSED, IO_ACTIVE, not INPUTS_BLOCKED, latched since the previous command); it has NO sample link
The gate rewrites frame_id to 'base_link' (Servo planning frame) and keeps header.stamp. Each decision is logged with
the bridge id parsed from frame_id ('bid', ground-truth join only; never used for a decision).
Args: <mode> <log> <ev_fifo|-> <end_s>   env P1_T0_NS, M39_HARNESS"""
import json, os, sys, time
import rclpy
from rclpy.parameter import Parameter
from geometry_msgs.msg import PoseStamped
MODE, LOG, FIFO, END = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]); TAU = 0.100
T0 = int(os.environ["P1_T0_NS"]) / 1e9
ev = None
if MODE == "A3":
    sys.path.insert(0, os.environ.get("M39_HARNESS", "/m39/harness")); from m39_evidence import Evidence; ev = Evidence(FIFO)
rclpy.init(); n = rclpy.create_node("m12_gate", parameter_overrides=[Parameter("use_sim_time", value=True)])
pub = n.create_publisher(PoseStamped, "/servo_node/pose_target_cmds", 50); out = open(LOG, "w", buffering=1)
st = {"last_seq": -1, "prev_rx": 0.0}
def parse(f):
    parts = f.split("|"); kv = dict(p.split("=", 1) for p in parts[1:] if "=" in p); return parts[0], kv
def on_msg(m):
    now = n.get_clock().now().nanoseconds / 1e9; wall = time.time()
    base, kv = parse(m.header.frame_id); stamp = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
    rec = {"t": wall - T0, "sim_now": now, "bid": int(kv.get("bid", -1)), "stamp_age": now - stamp}
    if MODE == "A0": ok, why = True, "pass"
    elif MODE == "A1": ok = rec["stamp_age"] <= TAU; why = "stamp_age"
    elif MODE == "A2":
        if "acq_ns" not in kv: ok, why = False, "no_provenance"
        else:
            acq_age = now - int(kv["acq_ns"]) / 1e9; seq = int(kv["seq"]); rec.update(acq_age=acq_age, seq=seq, valid=int(kv["valid"]))
            ok = acq_age <= TAU and int(kv["valid"]) == 1 and seq > st["last_seq"]
            why = "ok" if ok else ("acq_age" if acq_age > TAU else ("invalid" if int(kv["valid"]) != 1 else "seq_not_increasing"))
            if ok: st["last_seq"] = seq
    else:
        e_ok, age, fo, fl, bad = ev.state(); e_ok = e_ok and not (bad is not None and bad > st["prev_rx"])
        st["prev_rx"] = wall; ok, why = e_ok, "evidence"; rec.update(ev_age=age, ev_flags=fl)
    rec.update(admit=ok, why=why); out.write(json.dumps(rec) + "\n")
    if ok:
        o = PoseStamped(); o.header.stamp = m.header.stamp; o.header.frame_id = "base_link"; o.pose = m.pose; pub.publish(o)
def tick():
    if time.time() - T0 > END: raise SystemExit(0)
n.create_subscription(PoseStamped, "/m12/bridge_out", on_msg, 50); n.create_timer(0.05, tick)
try: rclpy.spin(n)
except (SystemExit, KeyboardInterrupt, rclpy.executors.ExternalShutdownException): pass
