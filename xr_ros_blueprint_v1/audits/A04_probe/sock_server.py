#!/usr/bin/env python3
"""A04 probe server: a plain Unix stream socket (not Monado) at <path> with file mode <mode>; answers 'ok' to each
client and records the kernel-attested peer credentials (SO_PEERCRED) next to the self-reported name the client sends.
Args: <path> <mode-octal> <seconds>"""
import os, socket, struct, sys, json, time
path, mode, dur = sys.argv[1], int(sys.argv[2], 8), float(sys.argv[3])
if os.path.exists(path): os.unlink(path)
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.bind(path); os.chmod(path, mode); s.listen(8); s.settimeout(0.5)
t = time.time()
while time.time() - t < dur:
    try: c, _ = s.accept()
    except socket.timeout: continue
    pid, uid, gid = struct.unpack("3i", c.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
    claim = c.recv(256).decode(errors="ignore")
    print(json.dumps({"peercred": {"pid": pid, "uid": uid, "gid": gid}, "self_reported": claim}), flush=True); c.sendall(b"ok"); c.close()
