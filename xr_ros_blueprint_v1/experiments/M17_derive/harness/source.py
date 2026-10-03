#!/usr/bin/env python3
"""M17 trusted synthetic source: 100 Hz SourceSample (session s1, seq from 1, header.stamp = sample time), grip from
ENGAGE_T. Also the trusted robot-state publisher (EE anchor, 50 Hz). Logs every sample. Args: <log> <end_s>  env T0"""
import json, os, sys, time
import rclpy
from geometry_msgs.msg import PointStamped
from m17_msgs.msg import SourceSample
sys.path.insert(0, os.path.dirname(__file__)); from common import hand, ANCHOR, ENGAGE_T
LOG, END = sys.argv[1], float(sys.argv[2]); T0 = float(os.environ["T0"]); out = open(LOG, "w", buffering=1)
rclpy.init(); n = rclpy.create_node("m17_source"); ps = n.create_publisher(SourceSample, "/m17/source", 50); pr = n.create_publisher(PointStamped, "/m17/robot_ee", 10)
st = {"seq": 0, "k": 0}
def tick():
    t = time.time() - T0
    if t > END: raise SystemExit(0)
    if t < 0: return
    st["seq"] += 1; h = hand(t); m = SourceSample(); m.header.stamp = n.get_clock().now().to_msg(); m.header.frame_id = "xr_origin"
    m.session = "s1"; m.seq = st["seq"]; m.hand.x, m.hand.y, m.hand.z = h; m.grip = t >= ENGAGE_T; m.valid = True; ps.publish(m)
    out.write(json.dumps({"t": t, "seq": st["seq"], "stamp": m.header.stamp.sec + m.header.stamp.nanosec * 1e-9, "hand": h, "grip": m.grip}) + "\n")
    st["k"] += 1
    if st["k"] % 2 == 0:
        r = PointStamped(); r.header.stamp = m.header.stamp; r.header.frame_id = "base_link"; r.point.x, r.point.y, r.point.z = ANCHOR; pr.publish(r)
n.create_timer(0.010, tick)
try: rclpy.spin(n)
except (SystemExit, KeyboardInterrupt, rclpy.executors.ExternalShutdownException): pass
