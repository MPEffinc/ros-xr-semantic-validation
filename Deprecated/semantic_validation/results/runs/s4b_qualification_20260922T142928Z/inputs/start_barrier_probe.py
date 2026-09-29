#!/usr/bin/env python3
"""Qualification-only common start barrier primitive; no ROS/Gazebo runtime."""
import json
import multiprocessing as mp
import time
from pathlib import Path


OUT = Path("/home/cclab/ros_xr/semantic_validation/results/runs/s4b_qualification_20260922T142928Z/timing/start_barrier_probe.json")


def recorder(ready: mp.Event, release: mp.Event, queue: mp.Queue) -> None:
    ready_ns = time.monotonic_ns()
    ready.set()
    released = release.wait(timeout=5.0)
    queue.put({"role": "recorder", "ready_monotonic_ns": ready_ns,
               "release_observed_monotonic_ns": time.monotonic_ns(), "released": released})


def sender(ready: mp.Event, release: mp.Event, queue: mp.Queue) -> None:
    ready_seen = ready.wait(timeout=5.0)
    ready_seen_ns = time.monotonic_ns()
    released = release.wait(timeout=5.0)
    queue.put({"role": "sender", "ready_seen": ready_seen, "ready_seen_monotonic_ns": ready_seen_ns,
               "first_send_monotonic_ns": time.monotonic_ns(), "released": released})


if __name__ == "__main__":
    ready = mp.Event()
    release = mp.Event()
    queue = mp.Queue()
    processes = [mp.Process(target=recorder, args=(ready, release, queue)),
                 mp.Process(target=sender, args=(ready, release, queue))]
    for process in processes:
        process.start()
    if not ready.wait(timeout=5.0):
        raise SystemExit("recorder never became ready")
    release_ns = time.monotonic_ns()
    release.set()
    rows = [queue.get(timeout=5.0) for _ in processes]
    for process in processes:
        process.join(timeout=5.0)
    sender_row = next(row for row in rows if row["role"] == "sender")
    result = {"clock": "CLOCK_MONOTONIC", "release_monotonic_ns": release_ns, "rows": rows,
              "assertions": {"recorder_ready_before_release": next(row for row in rows if row["role"] == "recorder")["ready_monotonic_ns"] <= release_ns,
                             "sender_waited_for_ready": sender_row["ready_seen"],
                             "sender_started_after_release": sender_row["first_send_monotonic_ns"] >= release_ns}}
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not all(result["assertions"].values()):
        raise SystemExit(1)

