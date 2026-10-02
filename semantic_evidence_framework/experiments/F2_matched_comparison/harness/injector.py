#!/usr/bin/env python3
"""Stand-in app command source (NOT a real app). Args: <case> <t0> <out.jsonl>. One command every 20 ms in [1.5, 14.0) s;
header.stamp = generation wall time; frame_id = 'seq=<n>'. Delivery per cases.deliveries (delay, duplicates, reorder)."""
import heapq, json, random, sys, time
import rclpy
from geometry_msgs.msg import PoseStamped
sys.path.insert(0, '/f2/harness'); import cases
case, t0, out = sys.argv[1], float(sys.argv[2]), open(sys.argv[3], 'w', buffering=1)
rng = random.Random(11)
rclpy.init(); node = rclpy.create_node('f2_app_injector'); pub = node.create_publisher(PoseStamped, '/xr/cmd', 200)
heap, seq, nxt, k = [], 0, 1.5, 0
while time.time() - t0 < 15.0:
    if nxt < 14.0 and time.time() - t0 >= nxt:
        g = time.time()
        for j, dl in enumerate(cases.deliveries(case, seq, rng)):
            heapq.heappush(heap, (g + dl, k, seq, g, j)); k += 1
        seq += 1; nxt += 0.020
    while heap and heap[0][0] <= time.time():
        _, _, s, g, j = heapq.heappop(heap)
        m = PoseStamped(); m.header.stamp.sec = int(g); m.header.stamp.nanosec = int((g % 1) * 1e9)
        m.header.frame_id = f'seq={s}'; m.pose.orientation.w = 1.0; pub.publish(m)
        out.write(json.dumps({"seq": s, "t_gen": g, "t_pub": time.time(), "copy": j}) + "\n")
    time.sleep(0.0003)
