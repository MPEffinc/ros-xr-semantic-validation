#!/usr/bin/env python3
"""M7 scripted tf broadcaster: base_link -> moving_ref at 100 Hz (sim clock), from frame_script.offset(). Logs every
published transform. Args: <log> <dynamic 0|1> <end_s>   env P1_T0_NS. The motion starts when sim time first exceeds
the sim time at wall T0+1.0 s (recorded)."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import rclpy
from rclpy.parameter import Parameter
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster
from frame_script import offset
LOG, DYN, END = sys.argv[1], sys.argv[2] == "1", float(sys.argv[3]); T0 = int(os.environ["P1_T0_NS"]) / 1e9
rclpy.init(); n = rclpy.create_node("m7_tf_frame", parameter_overrides=[Parameter("use_sim_time", value=True)])
br = TransformBroadcaster(n); out = open(LOG, "w", buffering=1); st = {"t_start": None}
def tick():
    now = n.get_clock().now(); ts = now.nanoseconds / 1e9
    if ts == 0: return
    if st["t_start"] is None and time.time() - T0 > 1.0:
        st["t_start"] = ts; out.write(json.dumps({"k": "t_start", "sim": ts, "wall": time.time()}) + "\n")
    o = offset(ts, DYN, st["t_start"] if st["t_start"] is not None else 1e18)
    t = TransformStamped(); t.header.stamp = now.to_msg(); t.header.frame_id = "base_link"; t.child_frame_id = "moving_ref"
    t.transform.translation.x, t.transform.translation.y, t.transform.translation.z = o; t.transform.rotation.w = 1.0
    br.sendTransform(t); out.write(json.dumps({"k": "tf", "sim": ts, "wall": time.time(), "o": o}) + "\n")
    if time.time() - T0 > END: raise SystemExit(0)
n.create_timer(0.01, tick)
try: rclpy.spin(n)
except (SystemExit, KeyboardInterrupt, rclpy.executors.ExternalShutdownException): pass
