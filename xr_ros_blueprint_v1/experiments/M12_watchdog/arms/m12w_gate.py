#!/usr/bin/env python3
"""M12_watchdog gate (R15). Same A2 rule as R11 m12_gate.py (app-read acquisition age <= TAU, valid == 1, read
sequence strictly increasing; TAU = 0.100 s sim clock), plus mode A2S:
  A2S  A2 AND the S2 receive evidence: the driver's latest packet-receipt time (file written by the patched remote
       driver: "<rx_ns> <rx_count>", CLOCK_MONOTONIC) must be <= SRC_TAU = 0.100 s old at gate receive (container
       monotonic clock), and rx_count must have advanced since the previous admitted command or be <= SRC_TAU old.
       This checks the latest state of a separate stream; it does NOT prove which packet a given pose came from.
The gate rewrites frame_id to 'base_link' (as R11) and logs every decision. Args: <mode> <log> <end_s> [rx_file]"""
import json, os, sys, time
import rclpy
from rclpy.parameter import Parameter
from geometry_msgs.msg import PoseStamped
MODE, LOG, END = sys.argv[1], sys.argv[2], float(sys.argv[3]); RX = sys.argv[4] if len(sys.argv) > 4 else None
TAU, SRC_TAU = 0.100, 0.100; T0 = int(os.environ["P1_T0_NS"]) / 1e9
rclpy.init(); n = rclpy.create_node("m12w_gate", parameter_overrides=[Parameter("use_sim_time", value=True)])
pub = n.create_publisher(PoseStamped, "/servo_node/pose_target_cmds", 50); out = open(LOG, "w", buffering=1)
st = {"last_seq": -1}
def parse(f):
    parts = f.split("|"); return parts[0], dict(p.split("=", 1) for p in parts[1:] if "=" in p)
def read_rx():
    try:
        a = open(RX).read().split(); return int(a[0]), int(a[1])
    except Exception: return None, None
def on_msg(m):
    now = n.get_clock().now().nanoseconds / 1e9; wall = time.time(); mono = time.monotonic_ns()
    base, kv = parse(m.header.frame_id); stamp = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
    rec = {"t": wall - T0, "sim_now": now, "bid": int(kv.get("bid", -1)), "stamp_age": now - stamp, "p": [m.pose.position.x, m.pose.position.y, m.pose.position.z]}
    if "acq_ns" not in kv: ok, why = False, "no_provenance"
    else:
        acq_age = now - int(kv["acq_ns"]) / 1e9; seq = int(kv["seq"]); rec.update(acq_age=acq_age, seq=seq, valid=int(kv["valid"]), res=int(kv.get("res", -1)))
        ok = acq_age <= TAU and int(kv["valid"]) == 1 and seq > st["last_seq"]
        why = "ok" if ok else ("acq_age" if acq_age > TAU else ("invalid" if int(kv["valid"]) != 1 else "seq_not_increasing"))
        if ok and MODE == "A2S":
            rx_ns, rx_cnt = read_rx(); rec.update(rx_age=None if rx_ns is None else (mono - rx_ns) / 1e9, rx_count=rx_cnt)
            if rx_ns is None or (mono - rx_ns) / 1e9 > SRC_TAU: ok, why = False, "source_rx_age"
        if ok: st["last_seq"] = seq
    rec.update(admit=ok, why=why); out.write(json.dumps(rec) + "\n")
    if ok:
        o = PoseStamped(); o.header.stamp = m.header.stamp; o.header.frame_id = "base_link"; o.pose = m.pose; pub.publish(o)
def tick():
    if time.time() - T0 > END: raise SystemExit(0)
n.create_subscription(PoseStamped, "/m12/bridge_out", on_msg, 50); n.create_timer(0.05, tick)
try: rclpy.spin(n)
except (SystemExit, KeyboardInterrupt, rclpy.executors.ExternalShutdownException): pass
