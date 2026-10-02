#!/usr/bin/env python3
"""Modified-app variant: the app publishes its own action state on /xr/app_state (one extra publisher per app).
Args: <sa_log> <t0_wall>"""
import json, sys, time, rclpy
from std_msgs.msg import String
sys.path.insert(0, '/f1/harness'); from tail_sa import SaTail
rclpy.init(); n = rclpy.create_node('f1_app_state'); pub = n.create_publisher(String, '/xr/app_state', 100)
sa = SaTail(sys.argv[1]); t0 = float(sys.argv[2])
sa.callbacks = [lambda d: pub.publish(String(data=json.dumps({"wall": d['wall'], "active": int(d['isActive'])})))]
while time.time() - t0 < 13.8: time.sleep(0.05)
