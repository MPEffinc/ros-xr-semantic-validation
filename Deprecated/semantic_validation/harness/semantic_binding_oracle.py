#!/usr/bin/env python3
"""Executable threat model for one-field mitigations.

This is an analytical oracle, not a production defense or runtime finding.
It demonstrates which semantic hazards remain outside each minimal guard.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable


Case = dict[str, object]


CASES: list[Case] = [
    {
        "name": "normal_current_controller",
        "hazard": False,
        "pose_valid": True,
        "actively_tracked": True,
        "source": "CONTROLLER",
        "age_ms": 10,
        "generation": 7,
        "current_generation": 7,
        "invalidation_epoch": 2,
        "authorized_epoch": 2,
    },
    {
        "name": "valid_but_inferred",
        "hazard": True,
        "pose_valid": True,
        "actively_tracked": False,
        "source": "CONTROLLER",
        "age_ms": 10,
        "generation": 7,
        "current_generation": 7,
        "invalidation_epoch": 2,
        "authorized_epoch": 2,
    },
    {
        "name": "viewer_fallback",
        "hazard": True,
        "pose_valid": True,
        "actively_tracked": True,
        "source": "VIEWER",
        "age_ms": 10,
        "generation": 7,
        "current_generation": 7,
        "invalidation_epoch": 2,
        "authorized_epoch": 2,
    },
    {
        "name": "stale_controller_sample",
        "hazard": True,
        "pose_valid": True,
        "actively_tracked": True,
        "source": "CONTROLLER",
        "age_ms": 3000,
        "generation": 7,
        "current_generation": 7,
        "invalidation_epoch": 2,
        "authorized_epoch": 2,
    },
    {
        "name": "future_clock_domain_sample",
        "hazard": True,
        "pose_valid": True,
        "actively_tracked": True,
        "source": "CONTROLLER",
        "age_ms": -1000,
        "generation": 7,
        "current_generation": 7,
        "invalidation_epoch": 2,
        "authorized_epoch": 2,
    },
    {
        "name": "old_transport_generation",
        "hazard": True,
        "pose_valid": True,
        "actively_tracked": True,
        "source": "CONTROLLER",
        "age_ms": 10,
        "generation": 6,
        "current_generation": 7,
        "invalidation_epoch": 2,
        "authorized_epoch": 2,
    },
    {
        "name": "recovery_without_rearm",
        "hazard": True,
        "pose_valid": True,
        "actively_tracked": True,
        "source": "CONTROLLER",
        "age_ms": 10,
        "generation": 7,
        "current_generation": 7,
        "invalidation_epoch": 3,
        "authorized_epoch": 2,
    },
]


def valid_only(case: Case) -> bool:
    return bool(case["pose_valid"])


def tracked_only(case: Case) -> bool:
    return bool(case["actively_tracked"])


def source_only(case: Case) -> bool:
    return case["source"] == "CONTROLLER"


def age_only(case: Case) -> bool:
    return -100 <= int(case["age_ms"]) <= 500


def generation_only(case: Case) -> bool:
    return case["generation"] == case["current_generation"]


def rearm_only(case: Case) -> bool:
    return case["authorized_epoch"] == case["invalidation_epoch"]


def semantic_binding(case: Case) -> bool:
    return all((
        valid_only(case),
        tracked_only(case),
        source_only(case),
        age_only(case),
        generation_only(case),
        rearm_only(case),
    ))


GUARDS: dict[str, Callable[[Case], bool]] = {
    "pose_valid_only": valid_only,
    "tracked_or_emulated_only": tracked_only,
    "source_only": source_only,
    "age_only": age_only,
    "generation_only": generation_only,
    "rearm_epoch_only": rearm_only,
    "composed_semantic_binding": semantic_binding,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, object]] = []
    for name, guard in GUARDS.items():
        misses = []
        false_blocks = []
        decisions = []
        for case in CASES:
            actionable = guard(case)
            correct = actionable is (not bool(case["hazard"]))
            decisions.append({"case": case["name"], "actionable": actionable, "correct": correct})
            if case["hazard"] and actionable:
                misses.append(case["name"])
            if not case["hazard"] and not actionable:
                false_blocks.append(case["name"])
        records.append({
            "event": "oracle_guard_result",
            "guard": name,
            "hazards_missed": misses,
            "false_blocks": false_blocks,
            "decisions": decisions,
            "status": "PASS" if not misses and not false_blocks else "INCOMPLETE",
            "evidence_level": "ANALYTICAL_EXECUTABLE_MODEL",
        })

    overall = (
        next(record for record in records if record["guard"] == "composed_semantic_binding")["status"] == "PASS"
        and all(
            record["status"] == "INCOMPLETE"
            for record in records
            if record["guard"] != "composed_semantic_binding"
        )
    )
    records.append({
        "event": "oracle_summary",
        "single_field_guards_all_incomplete": overall,
        "status": "PASS" if overall else "FAIL",
        "boundary": "Threat model only; not production mitigation evidence.",
    })
    with args.output.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps(records[-1], sort_keys=True))
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
