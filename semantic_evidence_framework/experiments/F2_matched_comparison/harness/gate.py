#!/usr/bin/env python3
"""F2 gate: all arms get the SAME command-freshness rule F and the SAME evidence-freshness rule E (PROTOCOL_F2.md §2).
Args: <fifo> <out.jsonl> <t0> <evidence_delay_s> <bound_client>"""
import bisect, json, sys, threading, time
import rclpy
from geometry_msgs.msg import PoseStamped

FIFO, OUT, T0, EV_DELAY, BOUND = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
MAX_AGE, FUTURE, EV_FRESH, DELTA = 0.200, 0.005, 0.050, 0.010
lock = threading.Lock()
T, A, VIS = [], [], []      # bound client's evidence samples: wall, active, visible_at


def reader():
    with open(FIFO) as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get('name') != BOUND:
                continue
            with lock:
                T.append(d['wall']); A.append(bool(d['io']) and not bool(d['inputs_blocked'])); VIS.append(time.time() + EV_DELAY)


threading.Thread(target=reader, daemon=True).start()


def n_visible(now):
    return bisect.bisect_right(VIS, now)


def state_at(t, n):
    """(known, active) from the latest visible sample at or before t, if within EV_FRESH of t."""
    i = bisect.bisect_right(T, t, 0, n) - 1
    if i < 0 or t - T[i] > EV_FRESH:
        return False, False
    return True, A[i]


def interval_ok(tg, ta, n):
    lo = bisect.bisect_left(T, tg - DELTA, 0, n); i = max(0, lo - 1)
    if i >= n or T[i] > tg - DELTA + EV_FRESH:
        return False
    prev = T[i]
    for k in range(i, n):
        if T[k] > ta:
            break
        if T[k] - prev > EV_FRESH or not A[k]:
            return False
        prev = T[k]
    return ta - prev <= EV_FRESH


last = {}   # per ORD arm: last admitted t_gen
ARMS = ['B0', 'FRESH', 'ARR', 'GEN_ARR', 'INTERVAL', 'ORD', 'ARR_ORD', 'GEN_ARR_ORD', 'INTERVAL_ORD']
rclpy.init(); node = rclpy.create_node('f2_gate'); out = open(OUT, 'w', buffering=1)


def on_cmd(m):
    ta = time.time(); tg = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9; seq = int(m.header.frame_id.split('=')[1])
    fresh = (ta - tg) <= MAX_AGE and tg <= ta + FUTURE
    dec, dt = {}, {}
    with lock:
        n = n_visible(ta)
        for arm in ARMS:
            s = time.perf_counter_ns()
            if arm == 'B0':
                ok = True
            else:
                ok = fresh
                if ok and arm != 'FRESH' and arm != 'ORD':
                    k_arr, a_arr = state_at(ta, n); ok = k_arr and a_arr
                    if ok and arm.startswith('GEN_ARR'):
                        k_gen, a_gen = state_at(tg, n); ok = k_gen and a_gen
                    if ok and arm.startswith('INTERVAL'):
                        ok = interval_ok(tg, ta, n)
                if ok and arm.endswith('ORD'):
                    ok = tg > last.get(arm, -1.0)
                    if ok:
                        last[arm] = tg
            dec[arm] = ok; dt[arm] = time.perf_counter_ns() - s
    out.write(json.dumps({"seq": seq, "t_gen": tg, "t_arr": ta, "dec": dec, "dt_ns": dt}) + "\n")


node.create_subscription(PoseStamped, '/xr/cmd', on_cmd, 200)
while time.time() - T0 < 15.5:
    rclpy.spin_once(node, timeout_sec=0.01)
