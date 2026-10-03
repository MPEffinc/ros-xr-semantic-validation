#!/usr/bin/env python3
"""M17 gate arms (outside the app). Both log one decision per command and forward admitted ones to /m17/admitted.
  AP  app-provenance gate (standard freshness/sequence/validity practice, trusts the app's fields):
      admit iff valid and now - header.stamp <= TAU and now - src_time <= TAU and src_seq > last admitted seq (per session)
  TV  trusted verifier (independent of the app): subscribes the source and the robot state itself, owns engage
      (first grip sample) and calibration (anchor), recomputes the declared mapping for the referenced sample and admits iff
      the sample exists in its own buffer (bounded wait 20 ms), the SOURCE marks it valid, its OWN receipt age <= TAU,
      src_seq > last admitted seq, and |app target - recomputed target| <= TOL. It also logs the target a trusted mapper
      would have generated directly from the latest sample (shadow; descriptive).
Args: <arm AP|TV> <log> <end_s>  env T0"""
import json, math, os, sys, time
import rclpy
from geometry_msgs.msg import PointStamped
from m17_msgs.msg import SourceSample, ProvCommand
sys.path.insert(0, os.path.dirname(__file__)); from common import mapping, TAU, TOL
ARM, LOG, END = sys.argv[1], sys.argv[2], float(sys.argv[3]); T0 = float(os.environ["T0"]); out = open(LOG, "w", buffering=1)
rclpy.init(); n = rclpy.create_node(f"m17_gate_{ARM.lower()}"); fwd = n.create_publisher(ProvCommand, "/m17/admitted", 50)
st = {"last": {}, "buf": {}, "latest": None, "ref": None, "anchor": None, "pending": []}
def sec(tm): return tm.sec + tm.nanosec * 1e-9
def now(): return n.get_clock().now().nanoseconds / 1e9
def decide(m, t_rx):
    t = time.time() - T0; rec = {"t": t, "cmd_id": m.cmd_id, "src_seq": m.src_seq, "arm": ARM}
    if ARM == "AP":
        nw = now(); why = None
        if not m.valid: why = "invalid"
        elif nw - sec(m.header.stamp) > TAU: why = "stamp_age"
        elif nw - sec(m.src_time) > TAU: why = "src_age"
        elif m.src_seq <= st["last"].get(m.src_session, 0): why = "seq"
    else:
        s = st["buf"].get((m.src_session, m.src_seq)); why = None; rec["recomputed"] = None
        if s is None: why = "sample_unknown"
        elif not s["valid"]: why = "source_invalid"
        elif time.monotonic() - s["rx"] > TAU: why = "sample_rx_age"
        elif m.src_seq <= st["last"].get(m.src_session, 0): why = "seq"
        elif st["ref"] is None or st["anchor"] is None: why = "not_engaged"
        else:
            r = mapping(s["hand"], st["ref"], st["anchor"]); rec["recomputed"] = r
            d = math.dist(r, (m.target.x, m.target.y, m.target.z)); rec["diff_m"] = d
            if d > TOL: why = "mapping_mismatch"
        if st["latest"] is not None and st["ref"] is not None and st["anchor"] is not None:
            rec["shadow_direct"] = mapping(st["latest"]["hand"], st["ref"], st["anchor"]); rec["shadow_seq"] = st["latest"]["seq"]
    rec["admit"] = why is None; rec["why"] = why or "ok"; rec["latency_ms"] = (time.monotonic() - t_rx) * 1000
    if why is None: st["last"][m.src_session] = m.src_seq; fwd.publish(m)
    out.write(json.dumps(rec) + "\n")
def on_cmd(m):
    if ARM == "TV" and (m.src_session, m.src_seq) not in st["buf"]: st["pending"].append((time.monotonic(), m)); return
    decide(m, time.monotonic())
def on_src(s):
    h = (s.hand.x, s.hand.y, s.hand.z); st["buf"][(s.session, s.seq)] = {"hand": h, "valid": s.valid, "rx": time.monotonic(), "seq": s.seq}
    st["latest"] = st["buf"][(s.session, s.seq)]
    if s.grip and st["ref"] is None and st["anchor"] is not None: st["ref"] = h
    if len(st["buf"]) > 400: st["buf"].pop(next(iter(st["buf"])))
def tick():
    if time.time() - T0 > END: raise SystemExit(0)
    keep = []
    for t_rx, m in st["pending"]:
        if (m.src_session, m.src_seq) in st["buf"] or time.monotonic() - t_rx > 0.020: decide(m, t_rx)
        else: keep.append((t_rx, m))
    st["pending"] = keep
n.create_subscription(ProvCommand, "/m17/app_cmd", on_cmd, 50)
if ARM == "TV":
    n.create_subscription(SourceSample, "/m17/source", on_src, 100)
    n.create_subscription(PointStamped, "/m17/robot_ee", lambda m: st.__setitem__("anchor", (m.point.x, m.point.y, m.point.z)), 10)
n.create_timer(0.002, tick)
try: rclpy.spin(n)
except (SystemExit, KeyboardInterrupt, rclpy.executors.ExternalShutdownException): pass
