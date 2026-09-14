#!/usr/bin/env python3
"""xiaoxiaoxh/vr-teleoperation — synthetic-payload runtime of the production
`/unity` wire schema, with ZERO possibility of reaching a robot.

SAFETY — read before changing anything here
-------------------------------------------
This repository contains a DIRECT Flexiv robot-control path. The following are
NEVER touched by this harness, and must never be:

  * `real_world/robot/single_flexiv_controller.py` — the sole `import flexivrdk`
    (module scope, line 8); its `__init__` connects, clears faults, calls
    `robot.enable()` and sets an NRT motion mode.
  * `real_world/robot/bimanual_flexiv_server.py` — its `__init__` constructs two
    `FlexivController`s against `192.168.2.110`/`.111` and immediately calls
    `gripper.move(0.1, 10, 0)` on BOTH arms. There is no dry-run flag.
  * `teleop.py` (line 29), `tests/test_robot_server.py` (line 41),
    `real_world/publisher/bimanual_robot_publisher.py` `__main__` (line 171) —
    every one of these constructs the Flexiv server as its first action.
  * `TeleopServer.run()` — unconditionally spawns `process_cmd`, which issues
    `/move_tcp/*` to the configured robot server.

What this harness DOES execute is the smallest unit with **zero in-repo imports
and zero ROS/vendor imports in its entire transitive chain**:

  * `common/data_models.py` — `UnityMes` and `HandMes`, the exact pydantic models
    FastAPI uses to parse the `/unity` POST body. Module-scope imports are only
    pydantic, numpy, enum and typing.

It is loaded by file path, so no package `__init__` chain runs, and it is run in
a container with `--network none`. No socket is opened, no HTTP server is
started, no robot IP is contacted, no Flexiv module is importable or imported.

Highest admissible evidence level: ``E2 SYNTHETIC_RUNTIME``, bounded to the wire
schema. Nothing downstream of the RingBuffer push is executed, so no control
consequence is observed or claimed.

The harness also performs one machine check (``E1``, labelled as such in the
output): a repo-wide scan asserting that the wire's `valid` and `timestamp`
fields are read nowhere in the repository's Python. That is a static assertion
and is recorded at E1, never at E2.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

EXPERIMENT = "xiaoxiaoxh_wire_schema_runtime"

FORBIDDEN_IMPORTS = ("flexivrdk", "pyrealsense2", "rclpy")


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def hand_payload(pos, quat, squeeze=0.0, cmd=0) -> dict[str, Any]:
    return {
        "q": [0.0] * 7,
        "pos": pos,
        "quat": quat,
        "thumbTip": [0.0, 0.0, 0.0],
        "indexTip": [0.0, 0.0, 0.0],
        "middleTip": [0.0, 0.0, 0.0],
        "ringTip": [0.0, 0.0, 0.0],
        "pinkyTip": [0.0, 0.0, 0.0],
        "squeeze": squeeze,
        "cmd": cmd,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")

    root: Path = args.target_root
    models_path = root / "common" / "data_models.py"

    spec = importlib.util.spec_from_file_location("xiaoxiaoxh_data_models", models_path)
    data_models = importlib.util.module_from_spec(spec)
    sys.modules["xiaoxiaoxh_data_models"] = data_models
    spec.loader.exec_module(data_models)

    loaded_forbidden = [m for m in FORBIDDEN_IMPORTS if m in sys.modules]

    append_jsonl(
        args.output,
        {
            "experiment": EXPERIMENT,
            "trial": "provenance",
            "event": "provenance",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "source_generation": args.revision,
            "source_sha256": {
                "common/data_models.py": hashlib.sha256(
                    models_path.read_bytes()
                ).hexdigest()
            },
            "executed_units": ["common/data_models.py :: UnityMes, HandMes"],
            "teleop_server_imported": False,
            "real_world_package_imported": False,
            "flexiv_module_imported": False,
            "forbidden_modules_in_sys_modules": loaded_forbidden,
            "http_server_started": False,
            "socket_opened": False,
            "robot_ip_contacted": None,
            "robot_used": False,
            "xr_hardware_used": False,
            "input_kind": "SYNTHETIC_UNITY_JSON_PAYLOAD",
            "evidence_level": "E2_SYNTHETIC_RUNTIME",
        },
    )
    if loaded_forbidden:
        raise SystemExit(f"ABORT: vendor/hardware module loaded: {loaded_forbidden}")

    results: list[dict[str, Any]] = []

    def record(trial, observed, expected, level="E2_SYNTHETIC_RUNTIME", note="") -> None:
        status = "PASS" if observed == expected else "FAIL"
        rec = {
            "experiment": EXPERIMENT,
            "trial": trial,
            "event": "schema_result",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "source_generation": args.revision,
            "source_kind": "SYNTHETIC_UNITY_JSON_PAYLOAD",
            "observed": observed,
            "expected": expected,
            "note": note,
            "status": status,
            "evidence_level": level,
        }
        results.append(rec)
        append_jsonl(args.output, rec)

    UnityMes = data_models.UnityMes

    base = {
        "timestamp": 12.5,
        "valid": True,
        "leftHand": hand_payload([0.1, 0.2, 0.3], [1.0, 0.0, 0.0, 0.0]),
        "rightHand": hand_payload([0.4, 0.5, 0.6], [1.0, 0.0, 0.0, 0.0], 0.8, 2),
    }

    # --- T1: what the wire schema can carry at all ---
    def field_names(model) -> list[str]:
        # pydantic v1 (__fields__) and v2 (model_fields) both supported
        return sorted(getattr(model, "model_fields", None) or model.__fields__)

    fields = field_names(UnityMes)
    hand_fields = field_names(data_models.HandMes)
    record(
        "t1_wire_schema_field_inventory",
        {
            "unity_mes_fields": fields,
            "hand_mes_fields": hand_fields,
            "has_session_field": any(
                "session" in f.lower() for f in fields + hand_fields
            ),
            "has_sequence_field": any(
                s in f.lower() for f in fields + hand_fields for s in ("seq", "gen")
            ),
            # exact-name test; a substring test would false-positive on
            # "middleTip" (contains "id")
            "has_source_id_field": any(
                f.lower() in ("id", "deviceid", "device_id", "sourceid",
                              "source_id", "serial", "uuid", "clientid")
                for f in fields + hand_fields
            ),
        },
        {
            "unity_mes_fields": ["leftHand", "rightHand", "timestamp", "valid"],
            "hand_mes_fields": [
                "cmd", "indexTip", "middleTip", "pinkyTip", "pos", "q", "quat",
                "ringTip", "squeeze", "thumbTip",
            ],
            "has_session_field": False,
            "has_sequence_field": False,
            "has_source_id_field": False,
        },
        note="The wire carries exactly one validity field and one timestamp, and no "
        "session, sequence, generation, device id or frame id at all (I2/I4 absent "
        "by construction).",
    )

    # --- T2 I1: valid=false parses to a fully-populated, fully-usable message ---
    invalid = json.loads(json.dumps(base))
    invalid["valid"] = False
    m_valid = UnityMes(**base)
    m_invalid = UnityMes(**invalid)
    record(
        "t2_valid_false_payload_parses_identically",
        {
            "invalid_parsed_ok": True,
            "valid_flag": m_invalid.valid,
            "right_pos": list(m_invalid.rightHand.pos),
            "right_quat": list(m_invalid.rightHand.quat),
            "right_cmd": m_invalid.rightHand.cmd,
            "right_squeeze": m_invalid.rightHand.squeeze,
            "actionable_fields_identical_to_valid_message": (
                list(m_invalid.rightHand.pos) == list(m_valid.rightHand.pos)
                and m_invalid.rightHand.cmd == m_valid.rightHand.cmd
                and m_invalid.rightHand.squeeze == m_valid.rightHand.squeeze
            ),
        },
        {
            "invalid_parsed_ok": True,
            "valid_flag": False,
            "right_pos": [0.4, 0.5, 0.6],
            "right_quat": [1.0, 0.0, 0.0, 0.0],
            "right_cmd": 2,
            "right_squeeze": 0.8,
            "actionable_fields_identical_to_valid_message": True,
        },
        note="A payload declaring itself invalid yields a message whose every "
        "actionable field is identical to a valid one. Rejection, if it happens at "
        "all, must happen in a consumer.",
    )

    # --- T3 I1: the sender sets valid unconditionally (machine check, E1) ---
    unity_sender = (
        root / "Unity" / "Assets" / "Scripts" / "HandDataCollector.cs"
    )
    sender_text = unity_sender.read_text(errors="replace") if unity_sender.exists() else ""
    native_validity_apis = (
        "GetControllerPositionValid",
        "GetControllerOrientationValid",
        "IsDataValid",
        "IsDataHighConfidence",
        "GetActiveController",
        "IsTracked",
    )
    record(
        "t3_sender_sets_valid_unconditionally",
        {
            "sender_file_present": bool(sender_text),
            "unconditional_assignment_present": "message.valid = true;" in sender_text,
            "native_validity_apis_called": sorted(
                a for a in native_validity_apis if a in sender_text
            ),
        },
        {
            "sender_file_present": True,
            "unconditional_assignment_present": True,
            "native_validity_apis_called": [],
        },
        level="E1_MACHINE_CHECKED_STATIC",
        note="Cotroller_collect ends with an unconditional `message.valid = true;` "
        "(HandDataCollector.cs:310) and calls no Meta tracking-validity API anywhere. "
        "The application-level `valid` flag is therefore NOT native tracking evidence.",
    )

    # --- T4 I1/I3: neither field is read anywhere in the repo's Python (E1) ---
    py_files = [
        p for p in root.rglob("*.py")
        if "third_party" not in p.parts and ".git" not in p.parts
    ]
    valid_readers: list[str] = []
    timestamp_readers: list[str] = []
    for p in py_files:
        text = p.read_text(errors="replace")
        rel = str(p.relative_to(root))
        if rel == "common/data_models.py":
            continue
        if re.search(r"\bmes\w*\.valid\b|\.valid\b(?!\s*[:=])", text):
            for m in re.finditer(r"^.*\.valid\b.*$", text, re.M):
                if "data_models" not in m.group(0):
                    valid_readers.append(f"{rel}: {m.group(0).strip()}")
        for m in re.finditer(r"^.*\bmes\w*\.timestamp\b.*$", text, re.M):
            timestamp_readers.append(f"{rel}: {m.group(0).strip()}")
    record(
        "t4_wire_valid_and_timestamp_are_never_read",
        {
            "python_files_scanned": len(py_files),
            "readers_of_message_valid": valid_readers,
            "readers_of_message_timestamp": timestamp_readers,
        },
        {
            "python_files_scanned": len(py_files),
            "readers_of_message_valid": [],
            "readers_of_message_timestamp": [],
        },
        level="E1_MACHINE_CHECKED_STATIC",
        note="The two semantic fields the wire does carry are consumed by nothing in "
        "the repository. I1 is DROPPED at the receiver despite being present on the "
        "wire, and I3 likewise.",
    )

    # --- T5 I3: what the timestamp actually is ---
    record(
        "t5_timestamp_is_unity_time_since_app_start",
        {
            "declared_type": "float",
            "sender_uses_unity_time_time": "Time.time" in sender_text,
            "sender_uses_epoch_clock": any(
                tok in sender_text
                for tok in ("DateTimeOffset", "UtcNow", "UnixTimeMilliseconds")
            ),
        },
        {
            "declared_type": "float",
            "sender_uses_unity_time_time": True,
            "sender_uses_epoch_clock": False,
        },
        level="E1_MACHINE_CHECKED_STATIC",
        note="`timestamp` is Unity `Time.time`: seconds since app start on the "
        "headset. It is not an epoch, not a tracking capture time, and not "
        "comparable to any receiver clock — so even a consumer that wanted to check "
        "freshness could not do so from this field alone.",
    )

    failures = [r["trial"] for r in results if r["status"] != "PASS"]
    summary = {
        "experiment": EXPERIMENT,
        "trial": "summary",
        "event": "suite_result",
        "monotonic_timestamp_ns": time.monotonic_ns(),
        "source_generation": args.revision,
        "trials": len(results),
        "passed": sum(1 for r in results if r["status"] == "PASS"),
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
        "semantic_disposition": {
            "I1_tracking": "PRESENT on the wire as `valid`, but set unconditionally "
            "by the sender and read by no consumer — DROPPED at both ends",
            "I2_source_id": "ABSENT (positional leftHand/rightHand only)",
            "I3_source_time": "PRESENT as Unity Time.time, never read, not an "
            "epoch and not comparable to a receiver clock",
            "I4_session_generation": "ABSENT",
            "I5_invalidation": "NOT_EXERCISED here (control path deliberately not run)",
        },
        "downstream_consequence": "NO_OUTPUT (wire schema only)",
        "evidence_level": "E2_SYNTHETIC_RUNTIME for the schema trials; "
        "E1_MACHINE_CHECKED_STATIC for t3/t4/t5 as labelled per trial",
        "claim_boundary": (
            "Only common/data_models.py was executed, on synthetic payloads, in a "
            "container with --network none. TeleopServer, process_cmd, the Flexiv "
            "controller, the bimanual server and every entry-point script were NOT "
            "imported, constructed or run. No robot was contacted. No downstream or "
            "control consequence is observed or claimed."
        ),
    }
    append_jsonl(args.output, summary)
    print(json.dumps({k: summary[k] for k in ("status", "trials", "passed", "failures")}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
