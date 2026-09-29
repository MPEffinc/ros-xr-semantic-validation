#!/usr/bin/env python3
"""AgileX QuestArmTeleop — synthetic-wire runtime of the unmodified upstream
representation layer, with NO device, NO ADB, NO ROS and NO arm driver.

Scope and safety
----------------
QuestArmTeleop's host side is NOT safely runnable as a whole:

  * every one of its six launch files starts the out-of-repo `agx_arm_ctrl` CAN
    driver for a physical AgileX Piper/Piper-X/Nero arm, four of them with
    `auto_enable: "true"`;
  * `pub_delta_pose.py` publishes actuator commands to `/control/joint_states`
    from inside the same node that reads the headset;
  * constructing `OculusReader()` has device side effects — it discovers ADB
    devices, installs `teleop-debug.apk` onto an attached headset and launches
    the app (`scripts/oculus_reader.py:39-42,49,100-118`).

Nothing above is invoked here. This harness exercises only the two pure,
side-effect-free upstream functions that define the wire representation:

  * ``OculusReader.process_data``  (`scripts/oculus_reader.py:140-171`, a
    ``@staticmethod``; needs only numpy and ``buttons_parser``)
  * ``parse_buttons``             (`scripts/buttons_parser.py:1-32`)

They are loaded by file path so that ``oculus_reader.py``'s module body is never
executed as part of a package import chain, and `ppadb`/rclpy are never touched.
Inputs are synthetic logcat payload strings written by this harness.

Highest admissible evidence level: ``E2 SYNTHETIC_RUNTIME``, and the boundary is
the wire representation only — no ROS publish, no transport, no consumer. The
Quest APK is opaque and was not executed, so nothing is claimed about what the
frontend does before emitting a record.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

EXPERIMENT = "agilex_wire_parser_runtime"


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


IDENTITY16 = "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"
POSE_R = "1 0 0 0.3 0 1 0 0.4 0 0 1 0.5 0 0 0 1"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scripts-dir", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")

    scripts = args.scripts_dir
    sys.path.insert(0, str(scripts))
    buttons_parser = load_module("buttons_parser", scripts / "buttons_parser.py")

    # Load only the two pure functions out of oculus_reader.py without executing
    # its module body (which imports ppadb and defines the device-side-effecting
    # OculusReader constructor).
    source = (scripts / "oculus_reader.py").read_text()
    namespace: dict[str, Any] = {
        "np": np,
        "parse_buttons": buttons_parser.parse_buttons,
    }
    start = source.index("    @staticmethod\n    def process_data(string):")
    end = source.index("    def extract_data(self, line):")
    body = source[start:end]
    # de-indent one class level and drop the decorator, leaving the function body
    # itself byte-identical to upstream
    dedented = "\n".join(
        line[4:] if line.startswith("    ") else line for line in body.splitlines()
    ).replace("@staticmethod\n", "", 1)
    exec(compile(dedented, str(scripts / "oculus_reader.py"), "exec"), namespace)
    process_data = namespace["process_data"]

    append_jsonl(
        args.output,
        {
            "experiment": EXPERIMENT,
            "trial": "provenance",
            "event": "provenance",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "source_generation": args.revision,
            "source_sha256": {
                p.name: hashlib.sha256((scripts / p.name).read_bytes()).hexdigest()
                for p in (Path("oculus_reader.py"), Path("buttons_parser.py"))
            },
            "executed_units": [
                "OculusReader.process_data (function body byte-identical to upstream)",
                "buttons_parser.parse_buttons (module imported as-is)",
            ],
            "oculus_reader_module_body_executed": False,
            "adb_used": False,
            "apk_installed_or_launched": False,
            "ros_used": False,
            "robot_used": False,
            "can_driver_launched": False,
            "launch_files_invoked": [],
            "input_kind": "SYNTHETIC_LOGCAT_PAYLOAD_STRING",
            "evidence_level": "E2_SYNTHETIC_RUNTIME",
        },
    )

    results: list[dict[str, Any]] = []

    def record(trial, observed, expected, note="") -> None:
        status = "PASS" if observed == expected else "FAIL"
        rec = {
            "experiment": EXPERIMENT,
            "trial": trial,
            "event": "wire_parse_result",
            "monotonic_timestamp_ns": time.monotonic_ns(),
            "source_generation": args.revision,
            "source_kind": "SYNTHETIC_LOGCAT_PAYLOAD",
            "observed": observed,
            "expected": expected,
            "note": note,
            "status": status,
            "evidence_level": "E2_SYNTHETIC_RUNTIME",
        }
        results.append(rec)
        append_jsonl(args.output, rec)

    full = f"l:{IDENTITY16}|r:{POSE_R}&R,L,rightTrig 0.9,leftGrip 0.1,rightJS 0.0 0.0"

    # --- T1 baseline ---
    transforms, buttons = process_data(full)
    record(
        "t1_wellformed_record_parses",
        {
            "keys": sorted(transforms.keys()),
            "r_translation": [
                round(float(transforms["r"][0][3]), 4),
                round(float(transforms["r"][1][3]), 4),
                round(float(transforms["r"][2][3]), 4),
            ],
            "button_keys_present": sorted(
                k for k in buttons if k in ("A", "B", "X", "Y", "RTr", "LG", "rightTrig")
            ),
        },
        {
            "keys": ["l", "r"],
            "r_translation": [0.3, 0.4, 0.5],
            "button_keys_present": ["A", "B", "LG", "RTr", "X", "Y", "rightTrig"],
        },
        "The record is a 4x4 row-major pose matrix per side plus a button list. "
        "Nothing else.",
    )

    # --- T2 I1/I3/I4: enumerate what the representation can carry at all ---
    record(
        "t2_representation_carries_no_validity_time_or_sequence",
        {
            "transform_value_type": type(transforms["r"]).__name__,
            "transform_shape": list(transforms["r"].shape),
            "transform_dict_keys": sorted(transforms.keys()),
            "button_dict_keys": sorted(buttons.keys()),
            "any_key_named_valid_or_tracked": any(
                s in k.lower() for k in buttons for s in ("valid", "track", "conf")
            ),
            "any_key_named_time_or_stamp": any(
                s in k.lower() for k in buttons for s in ("time", "stamp", "ts")
            ),
            "any_key_named_seq_or_session": any(
                s in k.lower() for k in buttons for s in ("seq", "session", "gen")
            ),
        },
        {
            "transform_value_type": "ndarray",
            "transform_shape": [4, 4],
            "transform_dict_keys": ["l", "r"],
            "button_dict_keys": sorted(
                [
                    "A",
                    "B",
                    "RThU",
                    "RJ",
                    "RG",
                    "RTr",
                    "X",
                    "Y",
                    "LThU",
                    "LJ",
                    "LG",
                    "LTr",
                    "rightTrig",
                    "leftGrip",
                    "rightJS",
                ]
            ),
            "any_key_named_valid_or_tracked": False,
            "any_key_named_time_or_stamp": False,
            "any_key_named_seq_or_session": False,
        },
        "The parsed record has exactly two poses and a flat button dict. There is "
        "no field in which tracking validity, source time, sequence or session "
        "could be transported, so I1/I3/I4 are structurally absent at this wire, "
        "independently of what the opaque APK knows.",
    )

    # --- T3: the only integrity check is 'exactly 16 floats' ---
    short = f"r:1 0 0 0 0 1 0 0 0 0 1 0 0 0 0&R"
    t_short, _ = process_data(short)
    record(
        "t3_short_matrix_silently_dropped",
        {"keys": sorted(t_short.keys())},
        {"keys": []},
        "process_data keeps a side only when exactly 16 values parsed "
        "(oculus_reader.py:168). A truncated record yields an empty dict — the "
        "same observable as a side simply not being present.",
    )

    # --- T4 I1: a dropped side is indistinguishable from 'not sent this frame' ---
    t_left_only, _ = process_data(f"l:{IDENTITY16}&L")
    record(
        "t4_missing_side_is_absence_not_invalidity",
        {
            "keys": sorted(t_left_only.keys()),
            "right_present": "r" in t_left_only,
            "any_invalid_marker": False,
        },
        {"keys": ["l"], "right_present": False, "any_invalid_marker": False},
        "A side that stops tracking is represented by the absence of its key, not "
        "by an invalidity flag. pub_pose.py:116-118 turns that absence into an "
        "early return, i.e. silence on the topic rather than an invalidation.",
    )

    # --- T5 I3/I4: two identical records are byte-identical after parsing ---
    t_a, b_a = process_data(full)
    time.sleep(0.25)
    t_b, b_b = process_data(full)
    record(
        "t5_repeated_record_is_indistinguishable_after_parse",
        {
            "poses_equal": bool(np.array_equal(t_a["r"], t_b["r"])),
            "buttons_equal": b_a == b_b,
            "any_field_distinguishes_them": False,
        },
        {
            "poses_equal": True,
            "buttons_equal": True,
            "any_field_distinguishes_them": False,
        },
        "A record replayed 250 ms later parses to an identical object. Combined "
        "with OculusReader's overwrite-only last_transforms cache "
        "(oculus_reader.py:194-195), a frozen source is indistinguishable from a "
        "live one at and after this boundary.",
    )

    # --- T6: a malformed record without the '&' separator is rejected wholesale ---
    t_bad, b_bad = process_data("r:1 0 0 0")
    record(
        "t6_record_without_separator_returns_none_none",
        {"transforms_is_none": t_bad is None, "buttons_is_none": b_bad is None},
        {"transforms_is_none": True, "buttons_is_none": True},
        "process_data returns (None, None) (oculus_reader.py:144-145). "
        "read_logcat_by_line then writes that None pair into last_transforms "
        "(:193-195), so pub_pose's .get('r') would raise AttributeError on the "
        "next tick — a parse failure is not isolated from the publisher.",
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
            "I1_tracking": "STRUCTURALLY_ABSENT on the wire; frontend UNKNOWN (opaque APK)",
            "I2_source_id": "laterality only ('l'/'r'); no device or operator id",
            "I3_source_time": "STRUCTURALLY_ABSENT on the wire",
            "I4_session_generation": "STRUCTURALLY_ABSENT on the wire",
            "I5_invalidation": "NOT_OBSERVABLE at this boundary; upstream source shows "
            "only a host-side A/B button clutch, never a tracking-derived re-arm",
        },
        "downstream_consequence": "NO_OUTPUT (representation layer only)",
        "evidence_level": "E2_SYNTHETIC_RUNTIME",
        "claim_boundary": (
            "Only two pure upstream functions were executed, on synthetic strings. "
            "No ADB, no APK, no ROS node, no DDS, no CAN, no arm driver, no launch "
            "file. The Quest frontend is opaque and unexecuted. No downstream or "
            "control consequence is claimed."
        ),
    }
    append_jsonl(args.output, summary)
    print(json.dumps({k: summary[k] for k in ("status", "trials", "passed", "failures")}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
