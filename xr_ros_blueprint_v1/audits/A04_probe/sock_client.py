#!/usr/bin/env python3
"""A04 probe client: connect to <path>, send a self-reported identity string, print the result (connected / errno)."""
import errno, json, os, socket, sys
path, claim = sys.argv[1], sys.argv[2]
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
try:
    s.connect(path); s.sendall(claim.encode()); r = s.recv(16).decode(); print(json.dumps({"uid": os.getuid(), "connected": True, "reply": r}))
except OSError as e:
    print(json.dumps({"uid": os.getuid(), "connected": False, "errno": errno.errorcode.get(e.errno, e.errno)}))
