#!/usr/bin/env python3
"""Feed Monado's 'remote' driver (TCP 4242) with a scripted right controller.
Layout of struct r_remote_data at monado e26a272c1 (verified with sizeof/offsetof): total 376 B,
right controller at 136+120=256, controller.active at +105, a_click at +108, pose at +0 (quat xyzw, pos xyz).
Usage: remote_feeder.py <a_click_intervals_json> <duration_s>   intervals are relative to start."""
import json, socket, struct, sys, time
iv = json.loads(sys.argv[1]); dur = float(sys.argv[2])
s = socket.create_connection(("127.0.0.1", 4242)); s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
t0 = time.time()
def ctrl(active, a_click, pos):
    b = bytearray(120)
    struct.pack_into('<7f', b, 0, 0, 0, 0, 1, *pos)
    b[105] = 1 if active else 0
    b[108] = 1 if a_click else 0
    return bytes(b)
def head():
    b = bytearray(128)
    struct.pack_into('<7f', b, 96, 0, 0, 0, 1, 0, 1.6, 0)   # center pose
    return bytes(b)
log = open(sys.argv[3], 'w') if len(sys.argv) > 3 else None
while time.time() - t0 < dur:
    t = time.time() - t0
    a = any(x <= t < y for x, y in iv)
    pkt = struct.pack('<Q', 0) + head() + ctrl(True, False, (-0.2, 1.0, -0.3)) + ctrl(True, a, (0.2, 1.0, -0.3))
    assert len(pkt) == 376
    s.sendall(pkt)
    if log: log.write(json.dumps({"wall": time.time(), "a_click": a}) + "\n")
    time.sleep(0.01)
