#!/usr/bin/env python3
"""Scripted Monado 'remote' controllers for M39 (extends F3 remote_feeder.py; struct r_remote_data 376 B,
right controller at +256: pose quat xyzw +0, position +16, squeeze_value +76, active +105, a_click +108).
Scenario JSON:
  duration                 s after t0
  grip        [[a,b],...]  right grip pressed for a <= t < b
  u           [x,y,z]      unit translation direction (tracking space)
  trans       [[a,b,v],..] translation along u at v m/s during [a,b)
  rot         [[a,b,w,ax]] rotation at w rad/s about hand-LOCAL axis ax in {"x","y","z"} during [a,b); segments are
                           composed in list order by right-multiplication (local frame), as a hand twisting in place
  controller_inactive [[a,b]]  device 'active' byte cleared (tracking loss; probe only)
Args: <scenario.json> <t0_wall> <out.jsonl>.  Logs wall (CLOCK_REALTIME) and mono (CLOCK_MONOTONIC) per packet."""
import json, socket, struct, sys, time
from scipy.spatial.transform import Rotation as R
sc = json.load(open(sys.argv[1])); t0 = float(sys.argv[2]); out = open(sys.argv[3], 'w', buffering=1)
P0 = (0.2, 1.0, -0.3)
s = None
while s is None:
    try: s = socket.create_connection(("127.0.0.1", 4242))
    except OSError: time.sleep(0.2)
s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
AX = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}
def inside(iv, t): return any(a <= t < b for a, b in iv)
def hand(t):
    d = sum(v * max(0.0, min(t, b) - a) for a, b, v in sc.get('trans', []))
    u = sc.get('u', [1, 0, 0]); p = tuple(P0[i] + d * u[i] for i in range(3))
    q = R.identity()
    for a, b, w, ax in sc.get('rot', []):
        ang = w * max(0.0, min(t, b) - a)
        if ang: q = q * R.from_rotvec([c * ang for c in AX[ax]])
    return p, q.as_quat()
def ctrl(active, grip, pos, quat):
    b = bytearray(120); struct.pack_into('<7f', b, 0, *quat, *pos)
    struct.pack_into('<f', b, 76, 1.0 if grip else 0.0); b[105] = 1 if active else 0; b[108] = 1 if grip else 0
    return bytes(b)
head = bytearray(128); struct.pack_into('<7f', head, 96, 0, 0, 0, 1, 0, 1.6, 0)
while time.time() - t0 < sc['duration']:
    t = time.time() - t0
    g = inside(sc.get('grip', []), t); act = not inside(sc.get('controller_inactive', []), t)
    p, q = hand(t)
    s.sendall(struct.pack('<Q', 0) + bytes(head) + ctrl(True, False, (-0.2, 1.0, -0.3), (0, 0, 0, 1)) + ctrl(act, g, p, q))
    out.write(json.dumps({"wall": time.time(), "mono": time.monotonic(), "t": t, "grip": g, "p": p, "q": list(q), "active": act}) + "\n")
    time.sleep(0.01)
