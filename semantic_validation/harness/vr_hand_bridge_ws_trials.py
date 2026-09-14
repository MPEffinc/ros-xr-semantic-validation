#!/usr/bin/env python3
"""VR-hand-bridge-ROS2 synthetic-WebSocket -> production-bridge -> ROS 2 trials.

Research harness (E2 SYNTHETIC_RUNTIME).

Exercised path:

    synthetic WebSocket JSON frame (this file)
      -> production xr_hand_pipeline/hand_ws_publisher.py (unmodified, pinned)
      -> actual ROS 2 geometry_msgs/msg/PoseStamped on
         /left_hand_pose and /right_hand_pose
      -> research subscriber (this file)

Injection point: the production WebSocket wire boundary
(`hand_ws_publisher.py:80-89`), upstream of all host-side bridge logic.
The upstream Godot/OpenXR frontend is NOT executed; no Quest, no robot,
no actuator. The bridge source is not modified.

Wire schema is taken verbatim from the pinned sources:
  - producer  : ws_streamer.gd:43-52   {"left_hand":{"pos":[x,y,z],"quat":[x,y,z,w]},
                                        "right_hand":{...}}
  - consumer  : hand_ws_publisher.py:87-89 (data['left_hand'], data['right_hand'])
                hand_ws_publisher.py:45,52 (hand['pos'], hand['quat'])

Run inside the ROS 2 Humble container; the bridge node must already be running
on 127.0.0.1:8765.
"""

import argparse
import asyncio
import json
import os
import statistics
import threading
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
import websockets

WS_URL = "ws://127.0.0.1:8765"


def now_wall_ns() -> int:
    return time.time_ns()


def now_mono_ns() -> int:
    return time.monotonic_ns()


class Recorder(Node):
    """Research subscriber. Observes only; performs no gating."""

    def __init__(self):
        super().__init__("vr_hand_bridge_recorder")
        self.lock = threading.Lock()
        self.records = []
        self.create_subscription(PoseStamped, "/left_hand_pose",
                                 lambda m: self._cb("left", m), 50)
        self.create_subscription(PoseStamped, "/right_hand_pose",
                                 lambda m: self._cb("right", m), 50)

    def _cb(self, side, msg: PoseStamped):
        rec = {
            "topic": side,
            "recv_wall_ns": now_wall_ns(),
            "recv_monotonic_ns": now_mono_ns(),
            "header_stamp_ns": msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec,
            "frame_id": msg.header.frame_id,
            "pos": [msg.pose.position.x, msg.pose.position.y, msg.pose.position.z],
            "quat": [msg.pose.orientation.x, msg.pose.orientation.y,
                     msg.pose.orientation.z, msg.pose.orientation.w],
        }
        with self.lock:
            self.records.append(rec)

    def snapshot(self):
        with self.lock:
            return list(self.records)


def hand(seq: float, tag: float = 0.0):
    """Godot-frame hand payload. `seq` is encoded in godot_y (-> ROS z)."""
    return {"pos": [0.1 + tag, float(seq), 0.3], "quat": [0.0, 0.0, 0.0, 1.0]}


async def connect():
    return await websockets.connect(WS_URL, open_timeout=5, close_timeout=2)


async def send_raw(ws, text):
    await ws.send(text)


async def probe_closed(ws, timeout=1.5):
    """Return (closed: bool, detail: str) after giving the server time to react."""
    try:
        await asyncio.wait_for(ws.recv(), timeout=timeout)
        return False, "server sent unexpected data"
    except asyncio.TimeoutError:
        return False, "connection still open after timeout"
    except websockets.exceptions.ConnectionClosed as exc:
        return True, f"ConnectionClosed code={exc.code} reason={exc.reason!r}"


async def run_trials(rec: Recorder, out_dir: str):
    events = []
    trials = {}

    def mark(label, **kw):
        e = {"label": label, "send_wall_ns": now_wall_ns(),
             "send_monotonic_ns": now_mono_ns()}
        e.update(kw)
        events.append(e)
        return e

    # ---------- P0: rate / presence, 100 well-formed frames at 50 Hz ----------
    ws = await connect()
    mark("P0_RATE_CONNECT")
    n = 100
    period = 0.02
    t0 = now_mono_ns()
    for i in range(n):
        frame = {"left_hand": hand(i), "right_hand": hand(1000 + i)}
        mark("P0_RATE_FRAME", seq=i, payload=frame)
        await send_raw(ws, json.dumps(frame))
        await asyncio.sleep(period)
    t1 = now_mono_ns()
    await asyncio.sleep(1.0)
    trials["P0_RATE"] = {"sent": n, "period_s": period,
                         "send_window_ns": t1 - t0}

    # ---------- A: single normal frame, exact value/stamp check ----------
    frame_a = {"left_hand": {"pos": [1.0, 2.0, 3.0], "quat": [0.0, 0.0, 0.0, 1.0]},
               "right_hand": {"pos": [-1.0, -2.0, -3.0], "quat": [0.0, 0.0, 0.0, 1.0]}}
    ea = mark("A_NORMAL", payload=frame_a)
    await send_raw(ws, json.dumps(frame_a))
    await asyncio.sleep(0.5)
    ea["send_wall_ns_after"] = now_wall_ns()
    closed, detail = await probe_closed(ws, 0.5)
    trials["A_NORMAL"] = {"connection_closed_by_server": closed, "detail": detail}

    # ---------- B: extra semantic fields the schema does not define ----------
    # The wire schema carries NO source timestamp (ws_streamer.gd:43-52), so a
    # "deliberately old source timestamp" can only be supplied as an extra
    # field. This trial establishes whether the bridge reads/validates any such
    # field, i.e. whether a freshness or validity gate exists at all.
    old_ns = 946684800_123456789  # 2000-01-01T00:00:00Z + 123456789 ns
    frame_b = {
        "left_hand": {"pos": [4.0, 5.0, 6.0], "quat": [0.0, 0.0, 0.0, 1.0]},
        "right_hand": {"pos": [-4.0, -5.0, -6.0], "quat": [0.0, 0.0, 0.0, 1.0]},
        "timestamp_ns": old_ns,
        "stamp": old_ns,
        "valid": False,
        "left_valid": False,
        "right_valid": False,
        "tracking_state": "UNTRACKED",
    }
    eb = mark("B_STALE_AND_INVALID_EXTRA_FIELDS", payload=frame_b,
              declared_source_time_ns=old_ns)
    await send_raw(ws, json.dumps(frame_b))
    await asyncio.sleep(0.5)
    eb["send_wall_ns_after"] = now_wall_ns()
    closed, detail = await probe_closed(ws, 0.5)
    trials["B_STALE_AND_INVALID_EXTRA_FIELDS"] = {
        "declared_source_time_ns": old_ns,
        "connection_closed_by_server": closed, "detail": detail}
    await ws.close()

    # ---------- C: missing required field 'right_hand' ----------
    ws = await connect()
    mark("C_CONNECT")
    frame_c = {"left_hand": {"pos": [7.0, 8.0, 9.0], "quat": [0.0, 0.0, 0.0, 1.0]}}
    mark("C_MISSING_RIGHT_HAND", payload=frame_c)
    await send_raw(ws, json.dumps(frame_c))
    closed, detail = await probe_closed(ws, 2.0)
    trials["C_MISSING_RIGHT_HAND"] = {"connection_closed_by_server": closed,
                                      "detail": detail}
    try:
        await ws.close()
    except Exception:
        pass

    # ---------- D: malformed JSON ----------
    ws = await connect()
    mark("D_CONNECT")
    mark("D_MALFORMED_JSON", payload="{not json")
    await send_raw(ws, "{not json")
    closed, detail = await probe_closed(ws, 2.0)
    trials["D_MALFORMED_JSON"] = {"connection_closed_by_server": closed,
                                  "detail": detail}
    try:
        await ws.close()
    except Exception:
        pass

    # ---------- E: wrong field type ----------
    ws = await connect()
    mark("E_CONNECT")
    frame_e = {"left_hand": {"pos": ["a", "b", "c"], "quat": [0, 0, 0, 1]},
               "right_hand": {"pos": [1, 2, 3], "quat": [0, 0, 0, 1]}}
    mark("E_NON_NUMERIC_POS", payload=frame_e)
    await send_raw(ws, json.dumps(frame_e))
    closed, detail = await probe_closed(ws, 2.0)
    trials["E_NON_NUMERIC_POS"] = {"connection_closed_by_server": closed,
                                   "detail": detail}
    try:
        await ws.close()
    except Exception:
        pass

    # ---------- F: recovery — does the bridge still serve after the faults? ----
    ws = await connect()
    mark("F_RECOVERY_CONNECT")
    frame_f = {"left_hand": {"pos": [11.0, 12.0, 13.0], "quat": [0.0, 0.0, 0.0, 1.0]},
               "right_hand": {"pos": [-11.0, -12.0, -13.0], "quat": [0.0, 0.0, 0.0, 1.0]}}
    ef = mark("F_RECOVERY_FRAME", payload=frame_f)
    await send_raw(ws, json.dumps(frame_f))
    await asyncio.sleep(0.5)
    ef["send_wall_ns_after"] = now_wall_ns()
    closed, detail = await probe_closed(ws, 0.5)
    trials["F_RECOVERY"] = {"connection_closed_by_server": closed, "detail": detail}
    await ws.close()

    await asyncio.sleep(1.0)

    records = rec.snapshot()
    with open(os.path.join(out_dir, "ros_messages.jsonl"), "w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    with open(os.path.join(out_dir, "ws_events.jsonl"), "w") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")

    summary = analyze(events, records, trials)
    with open(os.path.join(out_dir, "trials.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))


def analyze(events, records, trials):
    left = [r for r in records if r["topic"] == "left"]
    right = [r for r in records if r["topic"] == "right"]

    # Rate block: the first 100 left/right messages correspond to P0.
    rate = trials["P0_RATE"]
    p0_left = left[:100]
    if len(p0_left) >= 2:
        span = p0_left[-1]["recv_monotonic_ns"] - p0_left[0]["recv_monotonic_ns"]
        rate["observed_left_hz"] = round((len(p0_left) - 1) / (span / 1e9), 3) if span else None
    rate["received_left"] = len(p0_left)
    rate["received_right"] = len(right[:100])

    # Stamp-origin check for the single-frame trials.
    def stamp_origin(label):
        ev = next((e for e in events if e["label"] == label), None)
        if ev is None:
            return None
        lo, hi = ev["send_wall_ns"], ev.get("send_wall_ns_after", ev["send_wall_ns"])
        cands = [r for r in records if lo <= r["recv_wall_ns"] <= hi + 500_000_000]
        out = []
        for r in cands:
            out.append({
                "topic": r["topic"],
                "frame_id": r["frame_id"],
                "header_stamp_ns": r["header_stamp_ns"],
                "harness_send_wall_ns": lo,
                "header_minus_send_ns": r["header_stamp_ns"] - lo,
                "within_send_window": lo <= r["header_stamp_ns"] <= hi,
                "pos": r["pos"],
            })
        return out

    summary = {
        "total_ros_messages": len(records),
        "left_total": len(left),
        "right_total": len(right),
        "frame_ids_observed": sorted({r["frame_id"] for r in records}),
        "header_stamp_is_zero_count": sum(1 for r in records if r["header_stamp_ns"] == 0),
        "trials": trials,
        "stamp_checks": {
            "A_NORMAL": stamp_origin("A_NORMAL"),
            "B_STALE_AND_INVALID_EXTRA_FIELDS": stamp_origin("B_STALE_AND_INVALID_EXTRA_FIELDS"),
            "F_RECOVERY_FRAME": stamp_origin("F_RECOVERY_FRAME"),
        },
    }
    if len(records) >= 2:
        deltas = [records[i]["header_stamp_ns"] - records[i]["recv_wall_ns"]
                  for i in range(len(records))]
        summary["header_stamp_minus_subscriber_recv_wall_ns"] = {
            "median": int(statistics.median(deltas)),
            "min": min(deltas), "max": max(deltas),
        }
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    rclpy.init()
    rec = Recorder()
    t = threading.Thread(target=rclpy.spin, args=(rec,), daemon=True)
    t.start()
    time.sleep(1.5)  # discovery
    try:
        asyncio.run(run_trials(rec, args.out_dir))
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()
