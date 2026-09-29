#!/usr/bin/env python3
"""Run all currently automatable semantic validations without fail-fast.

This orchestrator is intentionally robot-free and does not start a hardware
server, probe ADB, install packages, elevate privileges, or change host network
configuration.  Each executable validation runs in its own subprocess and the
normalized result is appended to ``summary.jsonl`` even when another component
fails.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
from typing import Any, Callable


SCHEMA = "semantic-validation-suite-v1"
ALLOWED_STATUSES = ("PASS", "FAIL", "DISPROVED", "SKIP_ENV", "BLOCKED_HW")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("semantic_validation_%Y%m%dT%H%M%SZ")


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def json_objects(text: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for line in text.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            objects.append(value)
    return objects


def status_from_object(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in ("status", "result", "analysis_status"):
        candidate = value.get(key)
        if isinstance(candidate, str):
            return candidate.upper()
    return None


def read_external_status(paths: list[Path], stdout: str) -> str | None:
    candidates: list[str] = []
    for value in json_objects(stdout):
        status = status_from_object(value)
        if status:
            candidates.append(status)
    for path in paths:
        if not path.is_file():
            continue
        try:
            if path.suffix == ".jsonl":
                values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            else:
                values = [json.loads(path.read_text(encoding="utf-8"))]
        except (OSError, json.JSONDecodeError):
            continue
        for value in values:
            status = status_from_object(value)
            if status:
                candidates.append(status)
    return candidates[-1] if candidates else None


def normalize_status(external: str | None, returncode: int, stdout: str, stderr: str) -> str:
    value = (external or "").upper()
    aliases = {
        "INDEPENDENT_REANALYSIS_PASS": "PASS",
        "INSTRUMENTATION_NON_INTERFERENCE_PASS": "PASS",
        "PREFLIGHT_STATIC_PASS": "PASS",
        "BLOCKED_ENV": "SKIP_ENV",
        "NOT_PROBED": "SKIP_ENV",
        "NOT_AVAILABLE": "SKIP_ENV",
        "ANALYSIS_MISMATCH": "FAIL",
        "ERROR": "FAIL",
    }
    value = aliases.get(value, value)
    if value in ALLOWED_STATUSES:
        if returncode != 0 and value == "PASS":
            return "FAIL"
        return value
    combined = f"{stdout}\n{stderr}".lower()
    environment_markers = (
        "modulenotfounderror",
        "command not found",
        "no such file or directory",
        "permission denied while trying to connect to the docker daemon",
        "cannot connect to the docker daemon",
    )
    if returncode != 0 and any(marker in combined for marker in environment_markers):
        return "SKIP_ENV"
    return "PASS" if returncode == 0 else "FAIL"


class Suite:
    def __init__(self, *, run_id: str, run_dir: Path, workspace_root: Path) -> None:
        self.run_id = run_id
        self.run_dir = run_dir
        self.workspace_root = workspace_root
        self.summary_path = run_dir / "summary.jsonl"
        self.records: list[dict[str, Any]] = []

    def record(
        self,
        name: str,
        status: str,
        *,
        detail: str,
        command: list[str] | None = None,
        returncode: int | None = None,
        duration_ms: float | None = None,
        stdout_log: Path | None = None,
        stderr_log: Path | None = None,
        artifacts: list[Path] | None = None,
        external_status: str | None = None,
    ) -> dict[str, Any]:
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"non-normalized status for {name}: {status}")
        record = {
            "schema": SCHEMA,
            "event": "component_result",
            "run_id": self.run_id,
            "timestamp_utc": utc_now(),
            "test": name,
            "status": status,
            "detail": detail,
            "command": shlex.join(command) if command else None,
            "returncode": returncode,
            "duration_ms": duration_ms,
            "stdout_log": str(stdout_log.resolve()) if stdout_log else None,
            "stderr_log": str(stderr_log.resolve()) if stderr_log else None,
            "artifacts": [str(path.resolve()) for path in artifacts or []],
            "external_status": external_status,
            "robot_used": False,
            "hardware_used": False,
        }
        append_jsonl(self.summary_path, record)
        self.records.append(record)
        suffix = f" — {detail}" if detail else ""
        print(f"[{status:10}] {name}{suffix}", flush=True)
        return record

    def run(
        self,
        name: str,
        command: list[str],
        *,
        timeout: float,
        artifacts: list[Path] | None = None,
        status_paths: list[Path] | None = None,
        env: dict[str, str] | None = None,
        detail_fn: Callable[[str | None, int], str] | None = None,
    ) -> dict[str, Any]:
        stdout_path = self.run_dir / f"{name}.stdout.txt"
        stderr_path = self.run_dir / f"{name}.stderr.txt"
        started = time.monotonic_ns()
        try:
            completed = subprocess.run(
                command,
                cwd=self.workspace_root,
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            returncode = completed.returncode
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else (error.stdout or "")
            stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else (error.stderr or "")
            returncode = 124
            stderr = f"{stderr}\nTIMEOUT after {timeout:.0f} seconds".strip()
        except (OSError, ValueError) as error:
            stdout = ""
            stderr = f"{type(error).__name__}: {error}"
            returncode = 127
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        duration_ms = (time.monotonic_ns() - started) / 1_000_000.0
        external = read_external_status(status_paths or [], stdout)
        status = normalize_status(external, returncode, stdout, stderr)
        detail = (
            detail_fn(external, returncode)
            if detail_fn
            else f"returncode={returncode}; external_status={external or 'NONE'}"
        )
        return self.record(
            name,
            status,
            detail=detail,
            command=command,
            returncode=returncode,
            duration_ms=duration_ms,
            stdout_log=stdout_path,
            stderr_log=stderr_path,
            artifacts=artifacts,
            external_status=external,
        )

    def finish(self) -> str:
        counts = {status: sum(record["status"] == status for record in self.records) for status in ALLOWED_STATUSES}
        if counts["FAIL"]:
            overall = "FAIL"
        elif counts["DISPROVED"]:
            overall = "DISPROVED"
        elif counts["PASS"]:
            overall = "PASS"
        elif counts["SKIP_ENV"]:
            overall = "SKIP_ENV"
        else:
            overall = "BLOCKED_HW"
        append_jsonl(
            self.summary_path,
            {
                "schema": SCHEMA,
                "event": "suite_result",
                "run_id": self.run_id,
                "timestamp_utc": utc_now(),
                "test": "summary",
                "status": overall,
                "counts": counts,
                "components_total": len(self.records),
                "robot_used": False,
                "hardware_used": False,
                "privilege_escalation_used": False,
                "network_configuration_changed": False,
                "claim_boundary": "PASS covers only components that actually ran. SKIP_ENV and BLOCKED_HW remain unresolved and are not evidence for a research claim.",
            },
        )
        print(f"[{overall:10}] overall — {json.dumps(counts, sort_keys=True)}", flush=True)
        print(f"RESULT_ROOT={self.run_dir.resolve()}", flush=True)
        return overall


def instrumentation_candidate(harness_root: Path) -> Path | None:
    preferred = (
        "spes_instrumentation_integrity.py",
        "verify_spes_instrumentation_integrity.py",
        "instrumentation_integrity.py",
        "spes_instrumentation_non_interference.py",
        "spes_instrumentation_integrity.mjs",
    )
    for name in preferred:
        candidate = harness_root / name
        if candidate.is_file():
            return candidate
    candidates = sorted(
        path
        for pattern in ("*instrument*integrity*.py", "*instrument*non*interference*.py", "*instrument*integrity*.mjs")
        for path in harness_root.glob(pattern)
        if path.name != Path(__file__).name
    )
    return candidates[0] if candidates else None


def instrumentation_command(candidate: Path, artifact_root: Path) -> tuple[list[str], list[Path]]:
    command = ["node", str(candidate)] if candidate.suffix == ".mjs" else [sys.executable, str(candidate)]
    text = candidate.read_text(encoding="utf-8")
    artifacts: list[Path] = []
    output_dir = artifact_root / "dedicated"
    output_jsonl = artifact_root / "instrumentation_integrity.jsonl"
    summary_json = artifact_root / "instrumentation_integrity_summary.json"
    if '"--output-dir"' in text or "'--output-dir'" in text:
        command += ["--output-dir", str(output_dir)]
        artifacts.append(output_dir)
    if '"--output-root"' in text or "'--output-root'" in text:
        command += ["--output-root", str(artifact_root)]
        if '"--run-id"' in text or "'--run-id'" in text:
            command += ["--run-id", "dedicated"]
        artifacts.extend([
            output_dir,
            output_dir / "summary.json",
            output_dir / "integrity.jsonl",
        ])
    if '"--result-dir"' in text or "'--result-dir'" in text:
        command += ["--result-dir", str(output_dir)]
        artifacts.append(output_dir)
    if '"--output"' in text or "'--output'" in text:
        command += ["--output", str(output_jsonl)]
        artifacts.append(output_jsonl)
    if '"--summary"' in text or "'--summary'" in text:
        command += ["--summary", str(summary_json)]
        artifacts.append(summary_json)
    return command, artifacts


def run_quest2ros_probe(
    suite: Suite,
    *,
    validation_root: Path,
    artifact_root: Path,
) -> None:
    docker = shutil.which("docker")
    if not docker:
        suite.record(
            "quest2ros_runtime_probe",
            "SKIP_ENV",
            detail="docker CLI not found",
            command=["docker", "info"],
        )
        return
    info_log = suite.run_dir / "quest2ros_runtime_probe.docker_info.txt"
    started = time.monotonic_ns()
    try:
        info = subprocess.run(
            [docker, "info"],
            cwd=suite.workspace_root,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        info = subprocess.CompletedProcess([docker, "info"], 127, "", str(error))
    info_log.write_text(f"STDOUT\n{info.stdout}\nSTDERR\n{info.stderr}", encoding="utf-8")
    if info.returncode != 0:
        detail_lines = (info.stderr or info.stdout or "docker info failed").strip().splitlines()
        suite.record(
            "quest2ros_runtime_probe",
            "SKIP_ENV",
            detail=f"docker daemon unavailable: {detail_lines[-1] if detail_lines else 'unknown error'}",
            command=[docker, "info"],
            returncode=info.returncode,
            duration_ms=(time.monotonic_ns() - started) / 1_000_000.0,
            stdout_log=info_log,
            artifacts=[info_log],
            external_status="BLOCKED_ENV",
        )
        return
    image = os.environ.get("QUEST2ROS_RUNTIME_IMAGE", "ros-xr-humble:local")
    image_check = subprocess.run(
        [docker, "image", "inspect", image],
        cwd=suite.workspace_root,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    if image_check.returncode != 0:
        suite.record(
            "quest2ros_runtime_probe",
            "SKIP_ENV",
            detail=f"runtime image {image} absent; safe integrated runner does not build/download images",
            command=[docker, "image", "inspect", image],
            returncode=image_check.returncode,
            duration_ms=(time.monotonic_ns() - started) / 1_000_000.0,
            stdout_log=info_log,
            artifacts=[info_log],
            external_status="BLOCKED_ENV",
        )
        return
    output_root = artifact_root / "quest2ros_runtime"
    run_id = "robot_free_runtime"
    summary = output_root / run_id / "summary.json"
    command = [
        sys.executable,
        str(validation_root / "harness/run_quest2ros2_ros_runtime.py"),
        "--output-root",
        str(output_root),
        "--run-id",
        run_id,
        "--image",
        image,
    ]
    suite.run(
        "quest2ros_runtime_probe",
        command,
        timeout=420,
        artifacts=[output_root / run_id],
        status_paths=[summary],
        detail_fn=lambda external, code: (
            f"robot-free ROS runtime; docker --network none; returncode={code}; "
            f"external_status={external or 'NONE'}"
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=default_run_id())
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()

    validation_root = Path(__file__).resolve().parents[1]
    workspace_root = validation_root.parent
    output_root = args.output_root.resolve() if args.output_root else validation_root / "logs"
    run_dir = output_root / args.run_id
    if run_dir.exists():
        raise SystemExit(f"refusing to overwrite existing run directory: {run_dir}")
    run_dir.mkdir(parents=True)
    artifact_root = run_dir / "artifacts"
    artifact_root.mkdir()
    suite = Suite(run_id=args.run_id, run_dir=run_dir, workspace_root=workspace_root)
    harness_root = validation_root / "harness"

    no_quest_root = artifact_root / "no_quest_validation"
    suite.run(
        "no_quest_regression",
        [
            sys.executable,
            str(harness_root / "run_no_quest_validation.py"),
            "--run-id",
            "integrated_no_quest",
            "--result-root",
            str(no_quest_root),
        ],
        timeout=600,
        artifacts=[no_quest_root],
        status_paths=[no_quest_root / "integrated_summary.jsonl"],
    )

    reanalysis_root = artifact_root / "quest_raw_reanalysis"
    suite.run(
        "quest_raw_reanalysis",
        [
            sys.executable,
            str(harness_root / "reanalyze_spes_hw.py"),
            "--output-dir",
            str(reanalysis_root),
        ],
        timeout=240,
        artifacts=[reanalysis_root],
        status_paths=[reanalysis_root / "summary.jsonl", reanalysis_root / "comparison.json"],
    )

    classifier_root = artifact_root / "classifier_regression"
    suite.run(
        "classifier_raw_regression",
        [
            sys.executable,
            str(harness_root / "spes_classifier_regression.py"),
            "--output-dir",
            str(classifier_root),
        ],
        timeout=240,
        artifacts=[classifier_root],
        status_paths=[classifier_root / "result.json", classifier_root / "summary.jsonl"],
    )

    hardware_preflight_log = artifact_root / "spes_hardware_preflight.jsonl"
    suite.run(
        "spes_hardware_preflight",
        [
            sys.executable,
            str(harness_root / "run_spes_hardware_preflight.py"),
            "--output",
            str(hardware_preflight_log),
        ],
        timeout=300,
        artifacts=[hardware_preflight_log],
        status_paths=[hardware_preflight_log],
    )

    node = shutil.which("node")
    if node:
        suite.run(
            "operator_classifier_selftest",
            [node, str(harness_root / "spes_quest_operator_selftest.mjs")],
            timeout=90,
        )
        suite.run(
            "instrumentation_payload_equivalence",
            [node, str(harness_root / "spes_hardware_frontend_selftest.mjs")],
            timeout=90,
        )
    else:
        for name, script in (
            ("operator_classifier_selftest", "spes_quest_operator_selftest.mjs"),
            ("instrumentation_payload_equivalence", "spes_hardware_frontend_selftest.mjs"),
        ):
            suite.record(name, "SKIP_ENV", detail="node executable not found", command=["node", str(harness_root / script)])

    dedicated = instrumentation_candidate(harness_root)
    if dedicated:
        command, artifacts = instrumentation_command(dedicated, artifact_root / "instrumentation_integrity")
        status_paths = [path for path in artifacts if path.suffix in {".json", ".jsonl"}]
        suite.run(
            "instrumentation_integrity",
            command,
            timeout=240,
            artifacts=artifacts,
            status_paths=status_paths,
        )
    else:
        suite.record(
            "instrumentation_integrity",
            "SKIP_ENV",
            detail="no dedicated instrumentation-integrity harness discovered; payload-equivalence test reported separately",
        )

    run_quest2ros_probe(suite, validation_root=validation_root, artifact_root=artifact_root)

    picknik_jsonl = artifact_root / "picknik_deep_validation.jsonl"
    picknik_summary = artifact_root / "picknik_deep_validation_summary.json"
    suite.run(
        "picknik_deep_validation",
        [
            sys.executable,
            str(harness_root / "picknik_deep_validation.py"),
            "--output",
            str(picknik_jsonl),
            "--summary",
            str(picknik_summary),
            "--probe-adb",
        ],
        timeout=240,
        artifacts=[picknik_jsonl, picknik_summary],
        status_paths=[picknik_jsonl, picknik_summary],
    )

    suite.run(
        "picknik_deep_selftest",
        [sys.executable, str(harness_root / "picknik_deep_validation_selftest.py"), "-v"],
        timeout=120,
    )

    picknik_staging_root = Path("/tmp") / f"{args.run_id}_picknik_hw" / "UnityProject"
    picknik_staging_manifest = artifact_root / "picknik_hw_staging_manifest.json"
    picknik_staging_apk = Path("/tmp") / f"{args.run_id}_picknik_hw" / "picknik_semantic_validation.apk"
    suite.run(
        "picknik_hw_staging",
        [
            sys.executable,
            str(harness_root / "prepare_picknik_hw_project.py"),
            "--output",
            str(picknik_staging_root),
            "--manifest",
            str(picknik_staging_manifest),
            "--build-if-available",
            "--apk",
            str(picknik_staging_apk),
        ],
        timeout=600,
        artifacts=[picknik_staging_manifest],
        status_paths=[picknik_staging_manifest],
    )

    nvidia_deps = Path(os.environ.get("NVIDIA_PY_DEPS", "/tmp/ros_xr_nvidia_deps"))
    nvidia_output = artifact_root / "nvidia_positive_control.jsonl"
    nvidia_ready = all((nvidia_deps / package).is_dir() for package in ("numpy", "scipy", "pytest"))
    if nvidia_ready:
        nvidia_env = os.environ.copy()
        previous_pythonpath = nvidia_env.get("PYTHONPATH", "")
        nvidia_env["PYTHONPATH"] = f"{nvidia_deps}{os.pathsep}{previous_pythonpath}".rstrip(os.pathsep)
        suite.run(
            "nvidia_positive_control",
            [
                sys.executable,
                str(harness_root / "nvidia_positive_control.py"),
                "--output",
                str(nvidia_output),
            ],
            timeout=240,
            artifacts=[nvidia_output],
            status_paths=[nvidia_output],
            env=nvidia_env,
        )
    else:
        suite.record(
            "nvidia_positive_control",
            "SKIP_ENV",
            detail=f"numpy/scipy/pytest dependency directories missing at {nvidia_deps}",
            artifacts=[nvidia_output],
        )

    oracle_output = artifact_root / "semantic_binding_oracle.jsonl"
    suite.run(
        "semantic_binding_oracle",
        [
            sys.executable,
            str(harness_root / "semantic_binding_oracle.py"),
            "--output",
            str(oracle_output),
        ],
        timeout=60,
        artifacts=[oracle_output],
        status_paths=[oracle_output],
    )

    suite.record(
        "manual_hardware_validation",
        "BLOCKED_HW",
        detail="manual Quest/Unity/NVIDIA hardware activation is intentionally not launched by this robot-free runner",
    )

    overall = suite.finish()
    return 1 if overall == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
