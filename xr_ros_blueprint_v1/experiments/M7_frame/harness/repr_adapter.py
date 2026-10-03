#!/usr/bin/env python3
"""M7 representation adapter (new experimental component, not part of the app): takes the app's base_link target
(header.stamp = app generation time t_g, sim clock) and expresses it in 'moving_ref' AS OF t_g using tf at t_g (bounded
wait 50 ms), publishing m7_msgs/RepresentedPose with header.stamp = represented_at = t_g. Log per message.
Args: <log> <end_s>   env P1_T0_NS"""
import json, os, sys, time
import rclpy
from rclpy.duration import Duration
from rclpy.parameter import Parameter
from rclpy.time import Time
from geometry_msgs.msg import PoseStamped
from m7_msgs.msg import RepresentedPose
import tf2_ros
LOG, END = sys.argv[1], float(sys.argv[2]); T0 = int(os.environ["P1_T0_NS"]) / 1e9
rclpy.init(); n = rclpy.create_node("m7_repr_adapter", parameter_overrides=[Parameter("use_sim_time", value=True)])
buf = tf2_ros.Buffer(); tf2_ros.TransformListener(buf, None, spin_thread=True); pub = n.create_publisher(RepresentedPose, "/m7/represented", 50)
out = open(LOG, "w", buffering=1); st = {"seq": 0}
def on_cmd(m):
    tg = Time.from_msg(m.header.stamp)
    try:
        tr = buf.lookup_transform("base_link", "moving_ref", tg, timeout=Duration(seconds=0.05))
    except Exception as e:
        out.write(json.dumps({"t": time.time() - T0, "stamp": tg.nanoseconds / 1e9, "repr": False, "err": type(e).__name__}) + "\n"); return
    o = tr.transform.translation; st["seq"] += 1
    r = RepresentedPose(); r.header = m.header; r.represented_at = m.header.stamp; r.represented_frame = "moving_ref"; r.seq = st["seq"]
    pw = [m.pose.position.x, m.pose.position.y, m.pose.position.z]
    r.pose.orientation = m.pose.orientation
    r.pose.position.x, r.pose.position.y, r.pose.position.z = pw[0] - o.x, pw[1] - o.y, pw[2] - o.z
    pub.publish(r)
    out.write(json.dumps({"t": time.time() - T0, "seq": st["seq"], "stamp": tg.nanoseconds / 1e9, "repr": True, "o_used": [o.x, o.y, o.z],
                          "p_w": pw,
                          "p_F": [r.pose.position.x, r.pose.position.y, r.pose.position.z]}) + "\n")
def tick():
    if time.time() - T0 > END: raise SystemExit(0)
n.create_subscription(PoseStamped, "/m7/app_cmd", on_cmd, 50); n.create_timer(0.05, tick)
try: rclpy.spin(n)
except (SystemExit, KeyboardInterrupt, rclpy.executors.ExternalShutdownException): pass
