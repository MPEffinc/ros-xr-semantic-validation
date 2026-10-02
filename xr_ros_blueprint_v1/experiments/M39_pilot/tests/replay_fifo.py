#!/usr/bin/env python3
"""TEST-ONLY: replay recorded collector JSON lines into a FIFO at their original offsets from <src_t0>, re-timed to
the current P1_T0_NS, keeping only lines for client 'python3.12' plus their order. Args: <src.jsonl> <src_t0> <fifo>"""
import json, os, sys, time
src, st0, fifo = sys.argv[1], float(sys.argv[2]), sys.argv[3]; t0 = int(os.environ["P1_T0_NS"]) / 1e9
rows = [json.loads(l) for l in open(src)]; rows = [r for r in rows if r.get("name") == "python3.12"]
with open(fifo, "w", buffering=1) as f:
    for r in rows:
        tgt = t0 + (r["wall"] - st0); d = tgt - time.time()
        if d > 0: time.sleep(d)
        r["wall"] = time.time(); f.write(json.dumps(r) + "\n")
