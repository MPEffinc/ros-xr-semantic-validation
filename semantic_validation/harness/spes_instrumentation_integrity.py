#!/usr/bin/env python3
"""Independent non-interference checks for the Spes Quest instrumentation.

No web server is started.  Frontend code runs in Node VM sandboxes and server
logic is invoked on isolated in-process Teleop instances.  The upstream target
is read-only throughout the validation.
"""

from __future__ import annotations

import argparse
import ast
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import inspect
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
from typing import Any


VALIDATION_ROOT = Path(__file__).resolve().parents[1]
HARNESS_ROOT = VALIDATION_ROOT / "harness"
TARGET_ROOT = VALIDATION_ROOT / "targets" / "spes_teleop"
TARGET_PACKAGE = TARGET_ROOT / "teleop"
INSTRUMENTATION_ROOT = VALIDATION_ROOT / "instrumentation"
GENERATED_ROOT = VALIDATION_ROOT / "instrumented" / "spes_frontend"
EXPECTED_COMMIT = "c5d808155a87b584d6147a5943d4b87c34c92db0"
SUCCESS_TOKEN = "INSTRUMENTATION_NON_INTERFERENCE_PASS"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_id_now() -> str:
    return datetime.now(timezone.utc).strftime("spes_instrumentation_integrity_%Y%m%dT%H%M%SZ")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def command(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    completed = subprocess.run(
        args,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
        check=False,
    )
    return {
        "command": args,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def git_provenance() -> dict[str, Any]:
    head = command(["git", "-C", str(TARGET_ROOT), "rev-parse", "HEAD"])
    status = command(["git", "-C", str(TARGET_ROOT), "status", "--porcelain"])
    return {
        "head": head["stdout"].strip(),
        "status": status["stdout"],
        "clean_fixed_revision": head["returncode"] == 0
        and head["stdout"].strip() == EXPECTED_COMMIT
        and status["returncode"] == 0
        and not status["stdout"].strip(),
    }


def source_hashes() -> dict[str, str]:
    paths = {
        "upstream_index": TARGET_PACKAGE / "index.html",
        "upstream_server": TARGET_PACKAGE / "__init__.py",
        "generator": HARNESS_ROOT / "prepare_spes_hardware_frontend.py",
        "server_observer": HARNESS_ROOT / "spes_hardware_server.py",
        "semantic_logger_source": INSTRUMENTATION_ROOT / "semantic-logger.js",
        "quest_operator_source": INSTRUMENTATION_ROOT / "quest-operator.js",
        "generated_index": GENERATED_ROOT / "index.html",
        "generated_semantic_logger": GENERATED_ROOT / "assets" / "semantic-logger.js",
        "generated_quest_operator": GENERATED_ROOT / "assets" / "quest-operator.js",
    }
    return {name: sha256_file(path) for name, path in paths.items()}


def validate_manifest(hashes: dict[str, str]) -> dict[str, Any]:
    manifest_path = GENERATED_ROOT / "INSTRUMENTATION_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks = {
        "source_commit": manifest.get("source_commit") == EXPECTED_COMMIT,
        "source_index_hash": manifest.get("source_index_sha256") == hashes["upstream_index"],
        "generated_index_hash": manifest.get("instrumented_index_sha256")
        == hashes["generated_index"],
        "semantic_logger_manifest_hash": manifest.get("semantic_logger_sha256")
        == hashes["generated_semantic_logger"],
        "quest_operator_manifest_hash": manifest.get("quest_operator_sha256")
        == hashes["generated_quest_operator"],
        "semantic_logger_source_generated_equal": hashes["semantic_logger_source"]
        == hashes["generated_semantic_logger"],
        "quest_operator_source_generated_equal": hashes["quest_operator_source"]
        == hashes["generated_quest_operator"],
        "cache_buster_matches": manifest.get("operator_asset_cache_buster")
        == hashes["quest_operator_source"][:16],
    }
    return {
        "manifest": manifest,
        "checks": checks,
        "passed": all(checks.values()),
    }


def frontend_checks(run_dir: Path, raw_log: Path) -> dict[str, Any]:
    generator = load_module(
        "spes_integrity_generator", HARNESS_ROOT / "prepare_spes_hardware_frontend.py"
    )
    upstream_html = (TARGET_PACKAGE / "index.html").read_text(encoding="utf-8")
    derived_html = generator.instrument(upstream_html)
    canonical_html = (GENERATED_ROOT / "index.html").read_text(encoding="utf-8")
    deterministic_generation = derived_html == canonical_html
    append_jsonl(
        raw_log,
        {
            "event": "deterministic_generation",
            "derived_sha256": sha256_bytes(derived_html.encode()),
            "canonical_sha256": sha256_bytes(canonical_html.encode()),
            "exact_equal": deterministic_generation,
        },
    )

    matrix = command(["node", str(HARNESS_ROOT / "spes_payload_equivalence_matrix.mjs")])
    (run_dir / "payload_matrix.stdout.txt").write_text(matrix["stdout"], encoding="utf-8")
    (run_dir / "payload_matrix.stderr.txt").write_text(matrix["stderr"], encoding="utf-8")
    matrix_record = None
    if matrix["returncode"] == 0 and matrix["stdout"].strip():
        matrix_record = json.loads(matrix["stdout"].strip().splitlines()[-1])
        append_jsonl(raw_log, matrix_record)

    existing = command(["node", str(HARNESS_ROOT / "spes_hardware_frontend_selftest.mjs")])
    (run_dir / "existing_frontend_selftest.stdout.txt").write_text(
        existing["stdout"], encoding="utf-8"
    )
    (run_dir / "existing_frontend_selftest.stderr.txt").write_text(
        existing["stderr"], encoding="utf-8"
    )
    existing_record = None
    if existing["returncode"] == 0 and existing["stdout"].strip():
        existing_record = json.loads(existing["stdout"].strip().splitlines()[-1])
    append_jsonl(
        raw_log,
        {
            "event": "existing_frontend_selftest",
            "returncode": existing["returncode"],
            "parsed_result": existing_record,
            "stderr": existing["stderr"],
        },
    )
    passed = (
        deterministic_generation
        and matrix["returncode"] == 0
        and matrix_record is not None
        and matrix_record.get("result") == "PASS"
        and matrix_record.get("exact_serialization_equal") is True
        and matrix_record.get("send_condition_equal") is True
        and matrix_record.get("experiment_fields_in_pose_payload") is False
        and existing["returncode"] == 0
        and existing_record is not None
        and existing_record.get("result") == "PASS"
    )
    return {
        "passed": passed,
        "deterministic_generation": deterministic_generation,
        "matrix_returncode": matrix["returncode"],
        "matrix": matrix_record,
        "existing_selftest_returncode": existing["returncode"],
        "existing_selftest": existing_record,
    }


def pose_message(
    label: str,
    x: float,
    y: float = 0.0,
    z: float = 0.0,
    *,
    move: bool = True,
    scale: float = 1.0,
    orientation: dict[str, float] | None = None,
    gripper: str = "open",
    reserved_a: bool = False,
    reserved_b: bool = False,
    device: str = "VR",
) -> dict[str, Any]:
    return {
        "position": {"x": x, "y": y, "z": z},
        "orientation": orientation or {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
        "move": move,
        "gripper": gripper,
        "fps": 72,
        "scale": scale,
        "reservedButtonA": reserved_a,
        "reservedButtonB": reserved_b,
        "device": device,
        "message": label,
    }


def json_safe(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def states_equal(first: dict[str, Any], second: dict[str, Any], np_module: Any) -> bool:
    if first.keys() != second.keys():
        return False
    for key in first:
        left = first[key]
        right = second[key]
        if left is None or right is None:
            if left is not right:
                return False
        elif not np_module.allclose(left, right, rtol=0.0, atol=1e-12):
            return False
    return True


def callback_events_equal(first: list[dict[str, Any]], second: list[dict[str, Any]], np_module: Any) -> bool:
    if len(first) != len(second):
        return False
    for left, right in zip(first, second, strict=True):
        if left["message"] != right["message"]:
            return False
        if not np_module.allclose(left["pose"], right["pose"], rtol=0.0, atol=1e-12):
            return False
    return True


def server_differential(run_dir: Path, raw_log: Path) -> dict[str, Any]:
    deps = os.environ.get("SEMANTIC_PY_DEPS", "/tmp/ros_xr_semantic_deps")
    if deps not in sys.path:
        sys.path.insert(0, deps)
    server_module = load_module(
        "spes_integrity_server_observer", HARNESS_ROOT / "spes_hardware_server.py"
    )
    np = server_module.np
    Teleop = server_module.Teleop
    ServerObserver = server_module.ServerObserver
    JsonlWriter = server_module.JsonlWriter

    class_update_before = Teleop._Teleop__update
    class_source_before = inspect.getsource(class_update_before)
    class_source_hash_before = sha256_bytes(class_source_before.encode())
    target_server_hash_before = sha256_file(TARGET_PACKAGE / "__init__.py")

    wrapper_source = inspect.getsource(ServerObserver._observed_update)
    wrapper_tree = ast.parse(textwrap.dedent(wrapper_source))
    original_update_calls = sum(
        1
        for node in ast.walk(wrapper_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "self"
        and node.func.attr == "original_update"
    )

    production = Teleop(frontend_dir=str(TARGET_PACKAGE))
    observed = Teleop(frontend_dir=str(GENERATED_ROOT))
    production_callbacks: list[dict[str, Any]] = []
    observed_callbacks: list[dict[str, Any]] = []
    acknowledgements: list[dict[str, Any]] = []

    def capture(destination: list[dict[str, Any]]):
        def callback(pose: Any, message: dict[str, Any]) -> None:
            destination.append(
                {
                    "pose": np.array(pose, copy=True),
                    "message": copy.deepcopy(message),
                }
            )

        return callback

    production.subscribe(capture(production_callbacks))
    observer_writer = JsonlWriter(run_dir / "server_observer.jsonl")
    observer = ServerObserver(observed, observer_writer, acknowledgements.append)
    observed.subscribe(capture(observed_callbacks))
    original_binding_preserved = observer.original_update.__func__ is class_update_before

    private_names = [
        "relative_pose_init",
        "absolute_pose_init",
        "previous_received_pose",
        "pose",
    ]

    def snapshot(instance: Any) -> dict[str, Any]:
        result = {}
        for name in private_names:
            value = getattr(instance, f"_Teleop__{name}")
            result[name] = None if value is None else np.array(value, copy=True)
        return result

    angle = np.deg2rad(10.0) / 2.0
    sequence: list[tuple[str, dict[str, Any]]] = [
        ("move_false_initial", pose_message("move false initial", 0.0, move=False)),
        ("anchor", pose_message("anchor", 0.0)),
        ("small_scale_one", pose_message("scale one", 0.01)),
        ("small_scale_gt_one", pose_message("scale two", 0.02, scale=2.0)),
        ("small_scale_lt_one", pose_message("scale half", 0.03, scale=0.5)),
        (
            "small_orientation",
            pose_message(
                "orientation",
                0.04,
                orientation={"x": 0.0, "y": 0.0, "z": float(np.sin(angle)), "w": float(np.cos(angle))},
            ),
        ),
        (
            "jump_reject",
            pose_message(
                "jump reject metadata",
                0.50,
                gripper="close",
                reserved_a=True,
                reserved_b=True,
                device="VR",
            ),
        ),
        ("automatic_reanchor", pose_message("automatic reanchor", 0.51)),
        ("post_reanchor", pose_message("post reanchor", 0.52, scale=0.8)),
        (
            "move_false_metadata",
            pose_message(
                "move false metadata",
                0.52,
                move=False,
                gripper="close",
                reserved_a=True,
                reserved_b=True,
                device="Phone",
            ),
        ),
        ("missing_move_error", {"position": {"x": 0.0, "y": 0.0, "z": 0.0}}),
        (
            "missing_position_error",
            {
                "move": True,
                "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
            },
        ),
    ]
    trials = []
    try:
        for trial_name, original_message in sequence:
            production_message = copy.deepcopy(original_message)
            observed_message = copy.deepcopy(original_message)
            production_before = len(production_callbacks)
            observed_before = len(observed_callbacks)
            production_error = None
            observed_error = None
            production_result = None
            observed_result = None
            try:
                production_result = production._Teleop__update(production_message)
            except Exception as error:  # Expected for the two malformed parity cases.
                production_error = {"type": type(error).__name__, "message": str(error)}
            try:
                observed_result = observed._Teleop__update(observed_message)
            except Exception as error:  # Expected for the two malformed parity cases.
                observed_error = {"type": type(error).__name__, "message": str(error)}

            production_new = production_callbacks[production_before:]
            observed_new = observed_callbacks[observed_before:]
            callback_equal = callback_events_equal(production_new, observed_new, np)
            state_equal = states_equal(snapshot(production), snapshot(observed), np)
            message_unchanged = (
                production_message == original_message and observed_message == original_message
            )
            trial_passed = (
                production_error == observed_error
                and production_result == observed_result
                and callback_equal
                and state_equal
                and message_unchanged
            )
            trial = {
                "event": "server_wrapper_differential_trial",
                "trial": trial_name,
                "input": original_message,
                "production_error": production_error,
                "observed_error": observed_error,
                "production_callback_count": len(production_new),
                "observed_callback_count": len(observed_new),
                "callback_equal": callback_equal,
                "private_control_state_equal": state_equal,
                "input_message_unchanged": message_unchanged,
                "production_state": json_safe(snapshot(production)),
                "observed_state": json_safe(snapshot(observed)),
                "result": "PASS" if trial_passed else "FAIL",
            }
            append_jsonl(raw_log, trial)
            trials.append(trial)
    finally:
        observer.close()

    observer_records = [
        json.loads(line)
        for line in (run_dir / "server_observer.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    update_records = [record for record in observer_records if record.get("event") == "server_update"]
    callback_flags_match = [record["callback_emitted"] for record in update_records] == [
        trial["observed_callback_count"] > 0 for trial in trials
    ]
    class_source_after = inspect.getsource(Teleop._Teleop__update)
    class_source_hash_after = sha256_bytes(class_source_after.encode())
    target_server_hash_after = sha256_file(TARGET_PACKAGE / "__init__.py")
    class_method_identity_unchanged = Teleop._Teleop__update is class_update_before
    passed = (
        all(trial["result"] == "PASS" for trial in trials)
        and original_binding_preserved
        and original_update_calls == 1
        and class_method_identity_unchanged
        and class_source_hash_before == class_source_hash_after
        and target_server_hash_before == target_server_hash_after
        and len(update_records) == len(sequence)
        and len(acknowledgements) == len(sequence)
        and callback_flags_match
    )
    summary = {
        "event": "server_wrapper_differential_summary",
        "passed": passed,
        "trial_count": len(trials),
        "all_trial_behavior_equal": all(trial["result"] == "PASS" for trial in trials),
        "original_update_binding_is_actual_class_method": original_binding_preserved,
        "wrapper_original_update_call_sites": original_update_calls,
        "class_method_identity_unchanged": class_method_identity_unchanged,
        "class_update_source_sha256_before": class_source_hash_before,
        "class_update_source_sha256_after": class_source_hash_after,
        "target_server_sha256_before": target_server_hash_before,
        "target_server_sha256_after": target_server_hash_after,
        "observer_update_record_count": len(update_records),
        "sideband_ack_count": len(acknowledgements),
        "callback_flags_match_user_callbacks": callback_flags_match,
        "live_server_started": False,
        "hardware_used": False,
        "trials": trials,
    }
    append_jsonl(raw_log, summary)
    return summary


def existing_server_selftest(run_dir: Path, raw_log: Path) -> dict[str, Any]:
    env = os.environ.copy()
    deps = env.get("SEMANTIC_PY_DEPS", "/tmp/ros_xr_semantic_deps")
    env["PYTHONPATH"] = (
        deps if not env.get("PYTHONPATH") else f"{deps}{os.pathsep}{env['PYTHONPATH']}"
    )
    result = command(
        [sys.executable, str(HARNESS_ROOT / "spes_hardware_server.py"), "--self-test"],
        env=env,
    )
    (run_dir / "existing_server_selftest.stdout.txt").write_text(
        result["stdout"], encoding="utf-8"
    )
    (run_dir / "existing_server_selftest.stderr.txt").write_text(
        result["stderr"], encoding="utf-8"
    )
    parsed = None
    if result["returncode"] == 0 and result["stdout"].strip():
        parsed = json.loads(result["stdout"].strip().splitlines()[-1])
    record = {
        "event": "existing_server_selftest",
        "returncode": result["returncode"],
        "parsed_result": parsed,
        "stderr": result["stderr"],
        "passed": result["returncode"] == 0 and parsed is not None and parsed.get("result") == "PASS",
    }
    append_jsonl(raw_log, record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=VALIDATION_ROOT / "logs" / "instrumentation_integrity",
    )
    parser.add_argument("--run-id", default=run_id_now())
    args = parser.parse_args()
    run_dir = args.output_root.resolve() / args.run_id
    if run_dir.exists():
        raise SystemExit(f"refusing to overwrite existing run directory: {run_dir}")
    run_dir.mkdir(parents=True)
    raw_log = run_dir / "integrity.jsonl"

    provenance_before = git_provenance()
    hashes_before = source_hashes()
    manifest_result = validate_manifest(hashes_before)
    append_jsonl(
        raw_log,
        {
            "event": "integrity_run_start",
            "timestamp": utc_now(),
            "run_id": args.run_id,
            "target": provenance_before,
            "hashes": hashes_before,
            "manifest_validation": manifest_result,
            "hardware_used": False,
            "live_server_started": False,
        },
    )

    frontend = frontend_checks(run_dir, raw_log)
    server = server_differential(run_dir, raw_log)
    existing_server = existing_server_selftest(run_dir, raw_log)
    provenance_after = git_provenance()
    hashes_after = source_hashes()
    sources_unchanged = hashes_before == hashes_after
    passed = (
        provenance_before["clean_fixed_revision"]
        and provenance_after["clean_fixed_revision"]
        and manifest_result["passed"]
        and frontend["passed"]
        and server["passed"]
        and existing_server["passed"]
        and sources_unchanged
    )
    summary = {
        "experiment": "spes_instrumentation_integrity",
        "run_id": args.run_id,
        "timestamp": utc_now(),
        "result": SUCCESS_TOKEN if passed else "INSTRUMENTATION_INTERFERENCE_OR_TEST_FAILURE",
        "passed": passed,
        "target_commit": provenance_after["head"],
        "target_clean_before": provenance_before["clean_fixed_revision"],
        "target_clean_after": provenance_after["clean_fixed_revision"],
        "source_hashes_unchanged_during_run": sources_unchanged,
        "manifest_source_generated_hashes_match": manifest_result["passed"],
        "frontend_payload_equivalence": frontend["passed"],
        "frontend_case_count": frontend.get("matrix", {}).get("case_count")
        if frontend.get("matrix")
        else 0,
        "exact_pose_serialization_equal": bool(
            frontend.get("matrix", {}).get("exact_serialization_equal")
        )
        if frontend.get("matrix")
        else False,
        "send_condition_equal": bool(frontend.get("matrix", {}).get("send_condition_equal"))
        if frontend.get("matrix")
        else False,
        "experiment_fields_in_pose_payload": frontend.get("matrix", {}).get(
            "experiment_fields_in_pose_payload"
        )
        if frontend.get("matrix")
        else None,
        "server_wrapper_behavior_equal": server["passed"],
        "server_differential_trial_count": server["trial_count"],
        "actual_upstream_update_delegated": server[
            "original_update_binding_is_actual_class_method"
        ],
        "class_update_source_unchanged": server["class_update_source_sha256_before"]
        == server["class_update_source_sha256_after"],
        "existing_frontend_selftest_passed": frontend["existing_selftest_returncode"] == 0,
        "existing_server_selftest_passed": existing_server["passed"],
        "hardware_used": False,
        "live_server_started": False,
        "run_dir": str(run_dir),
        "hashes": hashes_after,
    }
    append_jsonl(raw_log, {"event": "integrity_summary", **summary})
    write_json(run_dir / "summary.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
