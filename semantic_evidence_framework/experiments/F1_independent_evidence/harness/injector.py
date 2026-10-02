#!/usr/bin/env python3
"""App-side command injector (stand-in app; NOT a real app). Args: <case> <t0_wall> <sa_log> <out.jsonl>
Generates one command every 20 ms in [1.5, 12.0) s; frame_id carries seq and the app-visible isActive at generation
(self-report, used only by D_DIRECT). Delivery follows the frozen case schedule (PROTOCOL_LINKAGE.md §4)."""
import heapq, json, random, sys, time
import rclpy
from geometry_msgs.msg import PoseStamped
sys.path.insert(0, '/f1/harness'); from tail_sa import SaTail
case, t0, sa_log, out = sys.argv[1], float(sys.argv[2]), sys.argv[3], open(sys.argv[4], 'w', buffering=1)
rng = random.Random(7)
def delay(tg):
    if case == 'K2' and 4.8 <= tg < 7.2: return 2.5
    if case == 'K3a': return rng.uniform(0.0, 0.150)
    return 0.010
rclpy.init(); node = rclpy.create_node('f1_app_injector'); pub = node.create_publisher(PoseStamped, '/xr/cmd', 100)
sa = SaTail(sa_log); heap = []; seq = 0; next_gen = 1.5
while time.time() - t0 < 13.5:
    t = time.time() - t0
    if next_gen < 12.0 and t >= next_gen:
        wall = time.time(); act = int(sa.latest['isActive']) if sa.latest else -1
        m = (seq, wall, act)
        heapq.heappush(heap, (wall + delay(t), seq, m, False))
        if case in ('K3b', 'K3c') and 2.0 <= t < 3.0:
            heapq.heappush(heap, (t0 + 8.0 + (t - 2.0), seq + 100000, m, True))
        seq += 1; next_gen += 0.020
    while heap and heap[0][0] <= time.time():
        _, _, (s, wall, act), replay = heapq.heappop(heap)
        msg = PoseStamped(); msg.header.stamp.sec = int(wall); msg.header.stamp.nanosec = int((wall % 1) * 1e9)
        msg.header.frame_id = f'seq={s};active={act}'; msg.pose.position.x = 0.4; msg.pose.orientation.w = 1.0
        pub.publish(msg)
        out.write(json.dumps({"seq": s, "t_gen": wall, "t_pub": time.time(), "self_active": act, "replay": replay}) + "\n")
    time.sleep(0.0005)
