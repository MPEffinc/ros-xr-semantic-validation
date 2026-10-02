#!/usr/bin/env python3
"""F1 consumer-side gate. Evaluates every policy of PROTOCOL_LINKAGE.md §3 on the same /xr/cmd stream.
Runtime evidence: collector JSON lines from a FIFO (trusted path, out of the app process).
App evidence: /xr/app_state (D_STREAM only).  Args: <fifo> <out.jsonl> <t0_wall> <evidence_delay_s> <bound_client>
"""
import bisect, json, sys, threading, time
import rclpy
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String

FIFO, OUT, T0, EV_DELAY, BOUND = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
DELTA, MAX_GAP, MAX_AGE, FUTURE = 0.010, 0.050, 0.200, 0.005
lock = threading.Lock()


class Hist:
    """Evidence samples (sample_wall, active, visible_at)."""
    def __init__(self):
        self.t, self.a, self.vis = [], [], []

    def add(self, t, a, vis):
        self.t.append(t); self.a.append(a); self.vis.append(vis)

    def visible(self, now):
        # samples are appended in arrival order; visible_at is non-decreasing
        return bisect.bisect_right(self.vis, now)

    def latest_ok(self, now):
        n = self.visible(now)
        return n > 0 and self.a[n - 1] and (now - self.t[n - 1]) <= MAX_GAP

    def interval_ok(self, t_gen, now):
        n = self.visible(now)
        if n == 0:
            return False
        lo = bisect.bisect_left(self.t, t_gen - DELTA, 0, n)
        start = max(0, lo - 1)              # include the sample just before the interval
        prev = self.t[start]
        if prev > t_gen - DELTA + MAX_GAP:  # nothing known close enough before the interval
            return False
        for i in range(start, n):
            if self.t[i] - prev > MAX_GAP or not self.a[i]:
                return False
            prev = self.t[i]
        return (now - prev) <= MAX_GAP


rt = {}          # client name -> Hist (runtime evidence)
app = Hist()     # app self-published state stream


def read_fifo():
    with open(FIFO) as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if 'client' not in d:
                continue
            act = bool(d['io']) and not bool(d['inputs_blocked'])
            with lock:
                rt.setdefault(d['name'], Hist()).add(d['wall'], act, time.time() + EV_DELAY)


threading.Thread(target=read_fifo, daemon=True).start()
rclpy.init()
node = rclpy.create_node('f1_gate')
pub = node.create_publisher(PoseStamped, '/xr/cmd_gated', 100)
out = open(OUT, 'w', buffering=1)


def on_app_state(m):
    d = json.loads(m.data)
    with lock:
        app.add(d['wall'], bool(d['active']), time.time())


def on_cmd(m):
    t_arr = time.time()
    t_gen = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
    fields = dict(kv.split('=') for kv in m.header.frame_id.split(';'))
    fresh = (t_arr - t_gen) <= MAX_AGE and t_gen <= t_arr + FUTURE
    dec, dt = {}, {}
    with lock:
        b = rt.get(BOUND)
        for name, fn in (
            ('B0', lambda: True),
            ('D_DIRECT', lambda: fields.get('active') == '1'),
            ('D_STREAM', lambda: fresh and app.latest_ok(t_arr) and app.interval_ok(t_gen, t_arr)),
            ('C_ARRIVAL', lambda: b is not None and b.latest_ok(t_arr)),
            ('C_INTERVAL', lambda: fresh and b is not None and b.latest_ok(t_arr) and b.interval_ok(t_gen, t_arr)),
            ('C_ANY', lambda: any(h.latest_ok(t_arr) for h in rt.values())),
        ):
            s = time.perf_counter_ns(); dec[name] = bool(fn()); dt[name] = time.perf_counter_ns() - s
    if dec['C_INTERVAL']:
        pub.publish(m)
    out.write(json.dumps({"seq": int(fields['seq']), "t_gen": t_gen, "t_arr": t_arr, "dec": dec, "dt_ns": dt}) + "\n")


node.create_subscription(PoseStamped, '/xr/cmd', on_cmd, 100)
node.create_subscription(String, '/xr/app_state', on_app_state, 100)
while time.time() - T0 < 14.0:
    rclpy.spin_once(node, timeout_sec=0.01)
