#!/usr/bin/env python3
"""M39 SHARED runtime-evidence reader (same source and freshness for every arm that uses it): JSON lines from the
libmonado collector (mnd_collector.c, 5 ms poll) through a FIFO.
state() -> ok iff the latest line for the bound client is <= 50 ms old at the call time and shows FOCUSED and IO_ACTIVE
and not INPUTS_BLOCKED (as F3 gate_rt.py). It also returns last_bad: the wall time of the most recent not-ok sample or
inter-sample gap > 50 ms, so a caller that polls slower than the collector (B1 polls at the app tick) can latch a
deactivation that started and ended between two of its polls."""
import json, threading, time
EV_FRESH = 0.050


class Evidence:
    def __init__(self, fifo, bound="python3.12"):
        self.bound = bound; self.lock = threading.Lock()
        self.t = None; self.flags_ok = False; self.flags = None; self.last_bad = None
        threading.Thread(target=self._reader, args=(fifo,), daemon=True).start()

    def _reader(self, fifo):
        with open(fifo) as f:
            for line in f:
                try: d = json.loads(line)
                except ValueError: continue
                if d.get("name") != self.bound: continue
                ok = bool(d["focused"]) and bool(d["io"]) and not bool(d["inputs_blocked"])
                with self.lock:
                    if self.t is not None and d["wall"] - self.t > EV_FRESH: self.last_bad = d["wall"]
                    if not ok: self.last_bad = d["wall"]
                    self.t, self.flags_ok, self.flags = d["wall"], ok, d["flags"]

    def state(self):
        """(ok, age_s or None, flags_ok, flags, last_bad_wall or None) evaluated now."""
        now = time.time()
        with self.lock: t, fo, fl, lb = self.t, self.flags_ok, self.flags, self.last_bad
        age = None if t is None else now - t
        return (age is not None and age <= EV_FRESH and fo), age, fo, fl, lb
