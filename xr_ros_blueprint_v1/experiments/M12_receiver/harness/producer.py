#!/usr/bin/env python3
"""M12_receiver synthetic packet producer (Docker_Teleop JSON-line schema, the fields the receiver reads): 60 Hz,
right hand pose + controls.right_teleop_enable + controls.source; 'timestamp' = seconds since producer start (like
Unity Time.time). MODE B1 adds 'seq' (per send, per session) and 'session'. Scenario keys (s after t0):
  duration; vx [[a,b,v]] hand x velocity; gaps [[a,b]] no send; reconnect [a,b] close TCP at a, reconnect at b with a
  new session and seq restarting at 0 (B1); dup [a,b,t_src] during [a,b) resend the packet originally sent at t_src
  (same content, same seq/session/timestamp); missing [[a,b]] omit seq/session/timestamp.
Log per send: wall, t, seq, session, dup, missing, x, fields.  Args: <scenario.json> <t0> <out.jsonl> <B0|B1>"""
import json, socket, sys, time
sc = json.load(open(sys.argv[1])); t0 = float(sys.argv[2]); out = open(sys.argv[3], "w", buffering=1); MODE = sys.argv[4]
def inside(iv, t): return any(a <= t < b for a, b in iv)
def connect():
    while True:
        try:
            s = socket.create_connection(("127.0.0.1", 5005)); s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1); return s
        except OSError: time.sleep(0.05)
s = connect(); session = 1; seq = 0; sent = []   # (t, packet)
rc = sc.get("reconnect"); dup = sc.get("dup"); closed = False
while time.time() - t0 < sc["duration"]:
    t = time.time() - t0
    if rc and rc[0] <= t < rc[1]:
        if not closed: s.close(); closed = True
        time.sleep(1 / 60); continue
    if rc and closed and t >= rc[1]:
        s = connect(); closed = False; session += 1; seq = 0
    if inside(sc.get("gaps", []), t): time.sleep(1 / 60); continue
    if dup and dup[0] <= t < dup[1]:
        src = min(sent, key=lambda x: abs(x[0] - dup[2])); pkt = src[1]; is_dup = True
    else:
        x = 0.2 + sum(v * max(0.0, min(t, b) - a) for a, b, v in sc.get("vx", []))
        pkt = {"timestamp": t, "right_hand": {"isTracked": True, "pos": {"x": x, "y": 1.0, "z": -0.3}, "rot": {"x": 0, "y": 0, "z": 0, "w": 1}},
               "left_hand": {"isTracked": False}, "controls": {"right_teleop_enable": True, "source": "quest_dual_controller"}}
        if MODE == "B1" and not inside(sc.get("missing", []), t):
            pkt["seq"] = seq; pkt["session"] = f"s{session}"
        if MODE == "B0" or inside(sc.get("missing", []), t):
            pass
        if inside(sc.get("missing", []), t): pkt.pop("timestamp", None)
        seq += 1; is_dup = False; sent.append((t, pkt))
    try: s.sendall((json.dumps(pkt) + "\n").encode())
    except OSError: s = connect(); session += 1; seq = 0; continue
    out.write(json.dumps({"wall": time.time(), "t": t, "seq": pkt.get("seq"), "session": pkt.get("session"), "dup": is_dup,
                          "missing": inside(sc.get("missing", []), t), "x": pkt["right_hand"]["pos"]["x"], "fields": sorted(pkt.keys())}) + "\n")
    time.sleep(1 / 60)
