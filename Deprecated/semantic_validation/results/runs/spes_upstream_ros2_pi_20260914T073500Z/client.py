
import json, os, ssl, sys, time
from datetime import datetime, timezone
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from websocket import create_connection

port = int(os.environ["SPES_PORT"])
count = int(os.environ["POSE_COUNT"])
step = float(os.environ["POSE_STEP"])
interval = float(os.environ["SEND_INTERVAL"])
settle = float(os.environ["DISCOVERY_SETTLE"])
out = os.environ["CLIENT_OUT"]

rclpy.init()
node = Node("spes_upstream_desktop_observer")
seen = []
node.create_subscription(
    PoseStamped, os.environ["POSE_TOPIC"],
    lambda m: seen.append({
        "desktop_observer_index": len(seen) + 1,
        "header_stamp": {"sec": int(m.header.stamp.sec),
                         "nanosec": int(m.header.stamp.nanosec)},
        "frame_id": m.header.frame_id,
        "position": {"x": m.pose.position.x, "y": m.pose.position.y,
                     "z": m.pose.position.z},
        "observe_monotonic_ns": time.monotonic_ns(),
        "observe_wall_utc": datetime.now(timezone.utc).isoformat(),
    }), 10)

# Give cross-host DDS discovery an unhurried window before any WSS packet is
# sent, so that a discovery race cannot be mistaken for message loss.
end = time.monotonic() + settle
while time.monotonic() < end:
    rclpy.spin_once(node, timeout_sec=0.05)

ws = create_connection("wss://127.0.0.1:%d/ws" % port, timeout=10,
                       sslopt={"cert_reqs": ssl.CERT_NONE, "check_hostname": False})
sent = []
for i in range(count):
    packet = {
        "position": {"x": 0.0, "y": round(i * step, 9), "z": 0.0},
        "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
        "move": True, "gripper": "open", "scale": 1.0, "device": "VR",
        "message": "questless synthetic source",
    }
    ws.send(json.dumps({"type": "pose", "data": packet}))
    sent.append({"wss_packet_index": i + 1,
                 "send_monotonic_ns": time.monotonic_ns(),
                 "send_wall_utc": datetime.now(timezone.utc).isoformat(),
                 "position": packet["position"]})
    end = time.monotonic() + interval
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.01)
ws.close()

end = time.monotonic() + 3.0
while time.monotonic() < end:
    rclpy.spin_once(node, timeout_sec=0.05)

with open(out, "w") as handle:
    for record in sent:
        handle.write(json.dumps({"event": "wss_packet_sent", **record}, sort_keys=True) + "\n")
    for record in seen:
        handle.write(json.dumps({"event": "desktop_observed_publish", **record}, sort_keys=True) + "\n")
print(json.dumps({"wss_packets_sent": len(sent), "desktop_observed_publishes": len(seen)}))
node.destroy_node()
rclpy.shutdown()
