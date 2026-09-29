#!/usr/bin/env python3
"""Apply the pre-registered PHASE 6 criteria (experiments/PROTOCOL.md) to trials.jsonl files.

Usage: analyze.py OUT_JSON OUT_MD trials.jsonl [trials.jsonl ...]
"""
from __future__ import annotations

import collections
import json
import sys
from typing import Any

TERM = ("CANCELED", "ABORTED")


def pv(ok: bool | None) -> str:
    return "UNKNOWN" if ok is None else ("PASS" if ok else "FAIL")


def lease_end_goals(m: dict[str, Any], how: str) -> dict[str, str]:
    if not m.get("a_goal_executing") or m.get("lease_end_observed_s") is None:
        return {"PG3-stop": "UNKNOWN", "PG3-cont": "UNKNOWN"}
    end = m["lease_end_observed_s"]
    lat = m.get("a_goal_terminal_latency_s")
    stop = m.get("a_goal_terminal") in TERM and lat is not None and lat - end <= 1.0
    cont = m.get("a_goal_status_end_plus_3s") in ("EXECUTING", "SUCCEEDED")
    out = {"PG3-stop": pv(stop), "PG3-cont": pv(cont)}
    if how in ("release", "ttl"):
        out["PG4"] = pv(not m.get("stale_goal_reached_ros"))
    if how == "disconnect":
        out["PG2-reconnect"] = ("PASS" if m.get("a2_cancel_terminal") == "CANCELED" else "FAIL") \
            if m.get("goal_still_active_at_reconnect") else "N/A"
    return out


def verdicts(case: str, m: dict[str, Any] | None) -> dict[str, str]:
    if m is None:
        return {"ALL": "UNKNOWN"}
    if case == "C1_normal":
        if not m.get("a_goal_executing"):
            return {"PG1": "UNKNOWN", "PG2": "UNKNOWN"}
        lat = m.get("a_cancel_latency_s")
        return {"PG1": pv(bool(m.get("b_denied")) and not m.get("b_goal_reached_ros")),
                "PG2": pv(m.get("a_cancel_terminal") == "CANCELED" and lat is not None and lat <= 3)}
    if case == "C2_release_executing":
        return lease_end_goals(m, "release")
    if case == "C3_ttl_expiry_executing":
        return lease_end_goals(m, "ttl")
    if case == "C4_disconnect_reconnect":
        return lease_end_goals(m, "disconnect")
    if case in ("C5_handoff", "C5F_handoff_back_to_back"):
        if not (m.get("a_goal_executing") and m.get("b_granted") and m.get("b_goal_reached_ros")):
            return {"PG2": "UNKNOWN", "PG6": "UNKNOWN"}
        pg6 = not m.get("b_goal_terminated_before_b_cancel")
        pg2 = (m.get("b_cancel_terminal") == "CANCELED") if pg6 else None
        return {"PG2": "N/A" if pg2 is None else pv(pg2), "PG6": pv(pg6)}
    if case == "C6_catalog_change_during_lease":
        if not m.get("a_granted"):
            return {"PG1": "UNKNOWN", "PG5": "UNKNOWN"}
        return {"PG1": pv(not m.get("b_goal_reached_ros_before_change")),
                "PG5": pv(not m.get("b_goal_reached_ros_after_change"))}
    if case == "C7_teleop_stream_after_release":
        if not m.get("a_granted") or not m.get("teleop_msgs_before_release"):
            return {"PG4": "UNKNOWN"}
        return {"PG4": pv(m.get("teleop_msgs_after_release_plus_0_2s") == 0)}
    return {"ALL": "UNKNOWN"}


def main() -> int:
    out_json, out_md, *inputs = sys.argv[1:]
    rows = []
    for path in inputs:
        with open(path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                rows.append({"source": path.split("/results/raw/")[-1], "baseline": r["baseline"],
                             "case": r["case"], "trial": r["trial"], "error": r["error"],
                             "measurements": r["measurements"],
                             "verdicts": verdicts(r["case"], r["measurements"])})
    agg: dict[tuple[str, str, str], collections.Counter] = collections.defaultdict(collections.Counter)
    for r in rows:
        for goal, v in r["verdicts"].items():
            agg[(r["case"], goal, r["baseline"])][v] += 1
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"trials": rows,
                   "aggregate": [{"case": c, "goal": g, "baseline": b, "counts": dict(n)}
                                 for (c, g, b), n in sorted(agg.items())]}, f, indent=1, sort_keys=True)
    baselines = sorted({r["baseline"] for r in rows})
    lines = ["| Case | Goal | " + " | ".join(baselines) + " |",
             "|---|---|" + "---|" * len(baselines)]
    for c, g in sorted({(c, g) for (c, g, _b) in agg}):
        cells = []
        for b in baselines:
            n = agg.get((c, g, b), collections.Counter())
            cells.append(", ".join(f"{k} {v}" for k, v in sorted(n.items())) or "NOT_RUN")
        lines.append(f"| {c} | {g} | " + " | ".join(cells) + " |")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
