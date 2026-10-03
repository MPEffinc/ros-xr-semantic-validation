#!/usr/bin/env python3
"""M17 app (the possibly compromised component). Honest behaviour: on every 2nd source sample after engage it publishes
ProvCommand(target = declared mapping of that sample, provenance = that sample's session/seq/time, valid, header.stamp = now).
In the window W0-W1 the scripted condition replaces the honest command (targets stay inside +/-0.05 m of the anchor):
  NORMAL         honest
  FAKE_TARGET    arbitrary target (0.03 m Lissajous around the anchor), provenance of the latest real sample, fresh stamps
  REWRITE_STALE  target mapped from the sample 1.0 s older, provenance rewritten to the latest real sample, fresh stamps
  WRONG_MAP      latest real sample and its true provenance, target from a wrong calibration (+0.020 m on y)
The ground-truth label of every command goes to the harness truth log (never read by any gate).
Args: <cond> <truth_log> <end_s>  env T0"""
import collections, json, math, os, sys, time
import rclpy
from geometry_msgs.msg import PointStamped
from m17_msgs.msg import SourceSample, ProvCommand
sys.path.insert(0, os.path.dirname(__file__)); from common import mapping, W0, W1
COND, LOG, END = sys.argv[1], sys.argv[2], float(sys.argv[3]); T0 = float(os.environ["T0"]); out = open(LOG, "w", buffering=1)
rclpy.init(); n = rclpy.create_node("m17_app"); pub = n.create_publisher(ProvCommand, "/m17/app_cmd", 50)
st = {"anchor": None, "ref": None, "k": 0, "id": 0, "hist": collections.deque(maxlen=300)}
n.create_subscription(PointStamped, "/m17/robot_ee", lambda m: st.__setitem__("anchor", (m.point.x, m.point.y, m.point.z)), 10)
def on_src(s):
    t = time.time() - T0; h = (s.hand.x, s.hand.y, s.hand.z); st["hist"].append((t, s, h))
    if t > END: raise SystemExit(0)
    if not s.grip or st["anchor"] is None: return
    if st["ref"] is None: st["ref"] = h
    st["k"] += 1
    if st["k"] % 2: return
    honest = mapping(h, st["ref"], st["anchor"]); tgt, prov, label = honest, s, "normal"
    if W0 <= t < W1 and COND != "NORMAL":
        if COND == "FAKE_TARGET":
            a = st["anchor"]; tgt = (a[0] + 0.03 * math.sin(2 * math.pi * 1.3 * t), a[1] + 0.03 * math.cos(2 * math.pi * 1.3 * t), a[2]); label = "forged"
        elif COND == "REWRITE_STALE":
            old = next((x for x in st["hist"] if x[0] >= t - 1.0), None); tgt = mapping(old[2], st["ref"], st["anchor"]); label = "forged"
        elif COND == "WRONG_MAP":
            tgt = (honest[0], honest[1] + 0.020, honest[2]); label = "forged"
    st["id"] += 1; m = ProvCommand(); m.header.stamp = n.get_clock().now().to_msg(); m.header.frame_id = "base_link"; m.cmd_id = st["id"]
    m.src_session = prov.session; m.src_seq = prov.seq; m.src_time = prov.header.stamp; m.valid = prov.valid
    m.target.x, m.target.y, m.target.z = tgt; pub.publish(m)
    dev = math.dist(tgt, honest)
    out.write(json.dumps({"t": t, "cmd_id": st["id"], "label": label if (label == "normal" or dev > 0.001) else "forged_equivalent",
                          "src_seq": prov.seq, "target": tgt, "honest_target": honest, "dev_m": dev}) + "\n")
n.create_subscription(SourceSample, "/m17/source", on_src, 50)
try: rclpy.spin(n)
except (SystemExit, KeyboardInterrupt, rclpy.executors.ExternalShutdownException): pass
