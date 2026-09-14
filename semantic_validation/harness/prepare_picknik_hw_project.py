#!/usr/bin/env python3
"""Create a disposable PickNik Unity hardware-validation project copy.

The pinned target checkout is never edited. The only added asset is a
side-band JSONL logger plus an Editor batch-build entry point; ROSPublishers.cs
is byte-identical to upstream.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


EXPECTED_COMMIT = "bbaef0762fdb0b429b8ea12a4ca65040748b41dd"
PROGRESS_STEPS = 7
HEARTBEAT_SECONDS = 5
UNITY_LOG_KEYWORDS = (
    "importing",
    "compiling",
    "building",
    "build",
    "android",
    "gradle",
    "error",
    "exception",
    "failed",
    "succeeded",
)


def timestamped(message: str) -> None:
    print(f"[{datetime.now().astimezone():%H:%M:%S}] {message}", flush=True)


def progress(step: int, message: str) -> None:
    timestamped(f"[{step}/{PROGRESS_STEPS}] {message}")


def unity_log_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def emit_unity_log_updates(path: Path, offset: int, remainder: str) -> tuple[int, str]:
    """Print selected new Unity log lines while retaining Unity's full log file."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(offset)
            appended = handle.read()
            offset = handle.tell()
    except FileNotFoundError:
        return offset, remainder

    complete, separator, remainder = (remainder + appended).rpartition("\n")
    if not separator:
        return offset, complete

    matching = [
        line.strip()
        for line in complete.splitlines()
        if line.strip() and any(keyword in line.lower() for keyword in UNITY_LOG_KEYWORDS)
    ]
    limit = 12
    for line in matching[:limit]:
        print(f"[UNITY] {line}", flush=True)
    if len(matching) > limit:
        print(f"[UNITY] {len(matching) - limit} additional matching lines suppressed this interval", flush=True)
    return offset, remainder


def print_unity_failure_tail(path: Path, line_count: int = 25) -> None:
    timestamped(f"Unity build failed; build log: {path}")
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        timestamped("Unity build log was not created.")
        return
    print(f"[UNITY] Last {min(line_count, len(lines))} Unity log lines:", flush=True)
    for line in lines[-line_count:]:
        print(f"[UNITY] {line}", flush=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def discover_unity() -> str | None:
    for name in ("Unity", "unity-editor"):
        candidate = shutil.which(name)
        if candidate:
            return candidate
    common = [
        Path("/opt/Unity/Editor/Unity"),
        Path.home() / "Unity/Hub/Editor/6000.1.6f1/Editor/Unity",
        Path.home() / ".local/share/unityhub/editors/6000.1.6f1/Editor/Unity",
    ]
    return next((str(path) for path in common if path.is_file()), None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--build-if-available", action="store_true")
    parser.add_argument("--apk", type=Path)
    parser.add_argument(
        "--target-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "targets/meta_quest_teleoperation",
    )
    args = parser.parse_args()
    target = args.target_root.resolve()
    output = args.output.resolve()
    manifest_path = args.manifest.resolve()
    instrumentation = Path(__file__).resolve().parents[1] / "instrumentation/picknik"
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")
    if manifest_path.exists():
        raise SystemExit(f"refusing to overwrite existing manifest: {manifest_path}")

    progress(1, "Verifying pinned PickNik checkout...")
    commit = git(target, "rev-parse", "HEAD")
    clean_before = git(target, "status", "--porcelain=v1", "--untracked-files=all") == ""
    if commit != EXPECTED_COMMIT:
        raise SystemExit(f"unexpected target commit: {commit}")
    if not clean_before:
        raise SystemExit("refusing to stage from a dirty upstream target")
    timestamped(f"Pinned checkout verified: {commit}")

    started_ns = time.time_ns()

    def ignore(path: str, names: list[str]) -> set[str]:
        ignored = {".git", "Library", "Temp", "Logs", "obj"}
        ignored.update(name for name in names if name.endswith("_BurstDebugInformation_DoNotShip"))
        return ignored.intersection(names)

    progress(2, "Copying disposable Unity project...")
    shutil.copytree(target, output, ignore=ignore, symlinks=True)
    timestamped(f"Disposable Unity project copied: {output}")

    progress(3, "Adding semantic-validation overlay...")
    overlay_assets = output / "UnityProject/Assets/SemanticValidation"
    shutil.copytree(instrumentation, overlay_assets)
    timestamped(f"Semantic-validation overlay added: {overlay_assets}")

    progress(4, "Checking ROSPublishers byte identity...")
    upstream_publisher = target / "UnityProject/Assets/ROSPublishers.cs"
    staged_publisher = output / "UnityProject/Assets/ROSPublishers.cs"
    logger = overlay_assets / "PickNikTrackingSidebandLogger.cs"
    logger_text = logger.read_text(encoding="utf-8")
    publisher_identical = upstream_publisher.read_bytes() == staged_publisher.read_bytes()
    logger_payload_independent = (
        "ROSConnection" not in logger_text
        and "RosMessageTypes" not in logger_text
        and ".Publish(" not in logger_text
    )
    timestamped(
        "ROSPublishers byte identity: "
        f"{'PASS' if publisher_identical else 'FAIL'}; side-band payload independence: "
        f"{'PASS' if logger_payload_independent else 'FAIL'}"
    )

    progress(5, "Locating Unity editor...")
    unity = discover_unity()
    build_status = "NOT_REQUESTED"
    build_command: list[str] = []
    build_returncode: int | None = None
    apk = (args.apk or (output / "Builds/picknik_semantic_validation.apk")).resolve()
    build_log = manifest_path.parent / "unity_batch_build.log"
    timestamped(f"Unity found: {unity}" if unity else "Unity not found.")
    if args.build_if_available:
        if unity is None:
            build_status = "SKIP_ENV"
            progress(6, "Android APK build skipped: Unity executable unavailable.")
        else:
            build_command = [
                unity,
                "-batchmode",
                "-quit",
                "-projectPath",
                str(output / "UnityProject"),
                "-executeMethod",
                "PickNikSemanticValidationBuild.BuildAndroid",
                "-logFile",
                str(build_log),
            ]
            environment = dict(os.environ)
            environment["PICKNIK_VALIDATION_APK"] = str(apk)
            progress(6, "Starting Android APK build...")
            build_log.parent.mkdir(parents=True, exist_ok=True)
            build_started = time.monotonic()
            process = subprocess.Popen(
                build_command,
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
            timestamped(f"Unity build started: pid={process.pid} build_log={build_log}")
            log_offset = 0
            log_remainder = ""
            last_heartbeat = build_started - HEARTBEAT_SECONDS
            while process.poll() is None:
                log_offset, log_remainder = emit_unity_log_updates(build_log, log_offset, log_remainder)
                now = time.monotonic()
                if now - last_heartbeat >= HEARTBEAT_SECONDS:
                    timestamped(
                        "Unity build running... "
                        f"elapsed={int(now - build_started)}s pid={process.pid} "
                        f"build_log={build_log} size={unity_log_size(build_log)}"
                    )
                    last_heartbeat = now
                time.sleep(1)
            log_offset, log_remainder = emit_unity_log_updates(build_log, log_offset, log_remainder)
            build_returncode = process.wait()
            timestamped(f"Unity exited rc={build_returncode}")
            build_status = "PASS" if build_returncode == 0 and apk.is_file() else "FAIL"
            if build_status == "PASS":
                timestamped(f"APK created: {apk} (size={apk.stat().st_size}, sha256={sha256(apk)})")
            else:
                print_unity_failure_tail(build_log)
    else:
        progress(6, "Android APK build not requested.")

    clean_after = git(target, "status", "--porcelain=v1", "--untracked-files=all") == ""
    manifest = {
        "status": "PASS" if publisher_identical and logger_payload_independent and clean_after else "FAIL",
        "target": str(target),
        "target_commit": commit,
        "target_clean_before": clean_before,
        "target_clean_after": clean_after,
        "staged_project": str(output / "UnityProject"),
        "instrumentation_asset": str(logger),
        "publisher_sha256_upstream": sha256(upstream_publisher),
        "publisher_sha256_staged": sha256(staged_publisher),
        "publisher_byte_identical": publisher_identical,
        "logger_ros_payload_independent": logger_payload_independent,
        "build_status": build_status,
        "unity_executable": unity,
        "build_command": build_command,
        "build_returncode": build_returncode,
        "build_log": str(build_log),
        "apk": str(apk),
        "apk_exists": apk.is_file(),
        "started_wall_ns": started_ns,
        "completed_wall_ns": time.time_ns(),
        "evidence_level": "MACHINE_CHECKED_STATIC",
        "claim_boundary": "Staging/non-interference check only. PASS is not a Unity compile, APK, Quest, ROS, or robot runtime result.",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    progress(7, f"Manifest written: {manifest_path}")
    print(json.dumps(manifest, sort_keys=True), flush=True)
    return 0 if manifest["status"] == "PASS" and build_status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
