#!/usr/bin/env python3
"""M7 converter arms (moving_ref -> base_link, before Servo). Same for every arm: age check now - header.stamp <= TAU =
0.100 s (sim) and tf lookup with bounded wait 50 ms; only the transform TIME differs:
  L  latest available tf (Time() = 0)
  S  tf at header.stamp (the transport stamp, which a republisher may re-stamp)
  R  tf at represented_at (the declared representation time carried in the typed message)
Publishes PoseStamped base_link (stamp = header.stamp) to Servo; logs the transform used and the decision.
Args: <mode L|S|R> <log> <end_s>   env P1_T0_NS"""
import json, os, sys, time
import rclpy
from rclpy.duration import Duration
from rclpy.parameter import Parameter
from rclpy.time import Time
from geometry_msgs.msg import PoseStamped
from m7_msgs.msg import RepresentedPose
import tf2_ros
MODE, LOG, END = sys.argv[1], sys.argv[2], float(sys.argv[3]); TAU = 0.100; T0 = int(os.environ["P1_T0_NS"]) / 1e9
rclpy.init(); n = rclpy.create_node("m7_converter", parameter_overrides=[Parameter("use_sim_time", value=True)])
buf = tf2_ros.Buffer(); tf2_ros.TransformListener(buf, None, spin_thread=True); pub = n.create_publisher(PoseStamped, "/servo_node/pose_target_cmds", 50)
out = open(LOG, "w", buffering=1)
def secs(t): return t.sec + t.nanosec * 1e-9
def on_msg(m):
    now = n.get_clock().now().nanoseconds / 1e9; hs = secs(m.header.stamp); ra = secs(m.represented_at)
    rec = {"t": time.time() - T0, "seq": m.seq, "now": now, "header_stamp": hs, "represented_at": ra, "p_F": [m.pose.position.x, m.pose.position.y, m.pose.position.z]}
    if now - hs > TAU:
        rec.update(admit=False, why="age"); out.write(json.dumps(rec) + "\n"); return
    when = Time() if MODE == "L" else Time.from_msg(m.header.stamp if MODE == "S" else m.represented_at)
    w0 = time.time()
    try:
        tr = buf.lookup_transform("base_link", m.represented_frame, when, timeout=Duration(seconds=0.05))
    except Exception as e:
        rec.update(admit=False, why="tf_unavailable", err=type(e).__name__, wait_s=time.time() - w0); out.write(json.dumps(rec) + "\n"); return
    o = tr.transform.translation; tt = secs(tr.header.stamp)
    p = [m.pose.position.x + o.x, m.pose.position.y + o.y, m.pose.position.z + o.z]
    rec.update(admit=True, why="ok", tf_time=tt, o_used=[o.x, o.y, o.z], p_out=p, wait_s=time.time() - w0)
    out.write(json.dumps(rec) + "\n")
    ps = PoseStamped(); ps.header.stamp = m.header.stamp; ps.header.frame_id = "base_link"; ps.pose = m.pose
    ps.pose.position.x, ps.pose.position.y, ps.pose.position.z = p; pub.publish(ps)
def tick():
    if time.time() - T0 > END: raise SystemExit(0)
n.create_subscription(RepresentedPose, "/m7/bridged", on_msg, 50); n.create_timer(0.05, tick)
try: rclpy.spin(n)
except (SystemExit, KeyboardInterrupt, rclpy.executors.ExternalShutdownException): pass
