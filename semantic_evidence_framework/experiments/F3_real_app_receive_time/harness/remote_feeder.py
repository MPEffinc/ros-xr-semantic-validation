#!/usr/bin/env python3
"""Scripted Monado 'remote' controllers (struct r_remote_data, 376 B; layout verified at Monado e26a272c1 and
re-verified for the F1 build by the 'remote' driver accepting it). Right controller: squeeze_value (+76) and a_click (+108)
follow the 'grip' intervals; position moves per 'motion'. Args: <scenario.json> <t0_wall> <out.jsonl>"""
import json, socket, struct, sys, time
sc = json.load(open(sys.argv[1])); t0 = float(sys.argv[2]); out = open(sys.argv[3], 'w', buffering=1)
s = None
while s is None:
    try: s = socket.create_connection(("127.0.0.1", 4242))
    except OSError: time.sleep(0.2)
s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
def inside(iv, t): return any(a <= t < b for a, b in iv)
def ctrl(active, grip, pos):
    b = bytearray(120); struct.pack_into('<7f', b, 0, 0, 0, 0, 1, *pos)
    struct.pack_into('<f', b, 76, 1.0 if grip else 0.0); b[105] = 1 if active else 0; b[108] = 1 if grip else 0
    return bytes(b)
head = bytearray(128); struct.pack_into('<7f', head, 96, 0, 0, 0, 1, 0, 1.6, 0)
while time.time() - t0 < sc['duration']:
    t = time.time() - t0
    g = inside(sc.get('grip', []), t)
    x = 0.2 + sum(v * max(0.0, min(t, b) - a) for a, b, v in sc.get('motion_x', []))
    act = not inside(sc.get('controller_inactive', []), t)
    s.sendall(struct.pack('<Q', 0) + bytes(head) + ctrl(True, False, (-0.2, 1.0, -0.3)) + ctrl(act, g, (x, 1.0, -0.3)))
    out.write(json.dumps({"wall": time.time(), "t": t, "grip": g, "x": x, "active": act}) + "\n")
    time.sleep(0.01)
