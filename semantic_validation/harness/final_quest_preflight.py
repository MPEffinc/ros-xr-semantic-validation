#!/usr/bin/env python3
"""Read-only final Quest-session preflight.

The script never starts a Quest application, ADB deployment, robot driver, or
actuator path.  Its only writes are the requested result directory and a
temporary writability sentinel in that directory.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SV = ROOT / "semantic_validation"

PASS = "PASS"
USER = "BLOCKED_USER_ACTION"
HARDWARE = "BLOCKED_HARDWARE_NOT_CONNECTED"
DEPENDENCY = "BLOCKED_DEPENDENCY"
STATUSES = {PASS, USER, HARDWARE, DEPENDENCY}


@dataclass
class Check:
    name: str
    status: str
    detail: str
    evidence: dict


def command(argv: list[str], timeout: int = 15, env: dict | None = None) -> dict:
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout, env=env
        )
        return {
            "argv": argv,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "timed_out": True,
        }
    except OSError as exc:
        return {
            "argv": argv,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "timed_out": False,
        }


def docker_command(argv: list[str], timeout: int = 20) -> dict:
    direct = command(["docker", *argv], timeout=timeout)
    if direct["returncode"] == 0:
        direct["access_path"] = "direct"
        return direct
    via_group = command(
        ["sg", "docker", "-c", shlex.join(["docker", *argv])], timeout=timeout
    )
    via_group["access_path"] = "sg docker"
    via_group["direct_error"] = direct["stderr"]
    return via_group


def add(checks: list[Check], name: str, status: str, detail: str, **evidence) -> None:
    assert status in STATUSES
    checks.append(Check(name, status, detail, evidence))


def parse_pin(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?:^revision:\s*|^)([0-9a-f]{40})$", text, re.MULTILINE)
    return match.group(1) if match else None


def repo_checks(checks: list[Check]) -> None:
    targets = {
        "spes": ("spes", "spes_teleop"),
        "picknik": ("picknik", "meta_quest_teleoperation"),
        "docker_teleop": ("docker_teleop", "docker_teleop"),
        "openvr_ur5e": ("openvr_ur5e", "openvr_ur5e_jazzy"),
        "quest2ros2": ("quest2ros2", "quest2ros2"),
        "openarmx": ("openarmx", "openarmx_teleop_vr"),
    }
    for name, (framework, target) in targets.items():
        pin_file = SV / "frameworks" / framework / "PINNED_REVISION"
        checkout = SV / "targets" / target
        expected = parse_pin(pin_file) if pin_file.is_file() else None
        head = command(["git", "-C", str(checkout), "rev-parse", "HEAD"])
        dirty = command(["git", "-C", str(checkout), "status", "--porcelain"])
        passed = (
            expected is not None
            and head["returncode"] == 0
            and head["stdout"] == expected
            and dirty["returncode"] == 0
            and not dirty["stdout"]
        )
        add(
            checks,
            f"repo_pin.{name}",
            PASS if passed else DEPENDENCY,
            "pinned checkout is present and clean" if passed else "pinned checkout mismatch, absent, or dirty",
            expected=expected,
            actual=head["stdout"],
            dirty=dirty["stdout"],
            checkout=str(checkout.relative_to(ROOT)),
        )


def docker_ros_checks(checks: list[Check]) -> None:
    info = docker_command(["info", "--format", "{{.ServerVersion}}"])
    available = info["returncode"] == 0
    add(
        checks,
        "docker.daemon",
        PASS if available else DEPENDENCY,
        "Docker daemon is usable" if available else "Docker daemon is not usable",
        result=info,
    )
    if not available:
        return
    images = {
        "humble_testbed": "ros-xr-humble:local",
        "docker_teleop": "docker-teleop-humble:local",
        "jazzy_base": "ros:jazzy-ros-base",
    }
    for name, image in images.items():
        result = docker_command(["image", "inspect", image, "--format", "{{.Id}}"])
        add(
            checks,
            f"docker.image.{name}",
            PASS if result["returncode"] == 0 else DEPENDENCY,
            f"image available: {image}" if result["returncode"] == 0 else f"missing image: {image}",
            image=image,
            image_id=result["stdout"],
            error=result["stderr"],
        )
    compose = docker_command(["compose", "-f", str(ROOT / "ros_env/compose.yaml"), "config", "--quiet"])
    add(
        checks,
        "docker.humble_compose",
        PASS if compose["returncode"] == 0 else DEPENDENCY,
        "Humble compose configuration validates" if compose["returncode"] == 0 else "Humble compose configuration failed",
        result=compose,
    )
    for distro, image in (("humble", "ros-xr-humble:local"), ("jazzy", "ros:jazzy-ros-base")):
        probe = docker_command(
            [
                "run", "--rm", "--network", "none", image, "bash", "-lc",
                f"source /opt/ros/{distro}/setup.bash && test \"$ROS_DISTRO\" = {distro} && ros2 --help >/dev/null",
            ],
            timeout=30,
        )
        add(
            checks,
            f"ros_env.{distro}",
            PASS if probe["returncode"] == 0 else DEPENDENCY,
            f"isolated ROS 2 {distro} probe passed" if probe["returncode"] == 0 else f"isolated ROS 2 {distro} probe failed",
            result=probe,
        )


def pi_checks(checks: list[Check]) -> None:
    remote = (
        "hostname; "
        "source /opt/ros/humble/setup.bash; "
        "source \"$HOME/ros2_ws/install/setup.bash\"; "
        "ros2 pkg executables semantic_robot_endpoint; "
        "test -d \"$HOME/semantic_robot_endpoint_logs\""
    )
    result = command(
        [
            "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4",
            "-o", "ConnectionAttempts=1", "rosxr", "bash", "-lc", shlex.quote(remote),
        ],
        timeout=10,
    )
    online = result["returncode"] == 0 and "semantic_robot_sink" in result["stdout"]
    status = PASS if online else HARDWARE
    add(
        checks,
        "pi.semantic_robot_sink",
        status,
        "Pi online; installed observation-only sink executable and log directory found"
        if online
        else "Pi is offline/unreachable or its observation-only sink install is unavailable",
        result=result,
        expected_role="PI_RECEIVED observation only",
    )
    local = SV / "testbed/pi_ws/src/semantic_robot_endpoint"
    package_ok = (local / "package.xml").is_file() and any(local.rglob("semantic_robot_sink.py"))
    add(
        checks,
        "pi.sink_source",
        PASS if package_ok else DEPENDENCY,
        "in-repo sink source is present" if package_ok else "in-repo sink source is incomplete",
        path=str(local.relative_to(ROOT)),
    )


def script_checks(checks: list[Check]) -> None:
    required = [
        "semantic_validation/frameworks/spes/spes_preflight.sh",
        "semantic_validation/frameworks/spes/spes_start_all.sh",
        "semantic_validation/frameworks/spes/spes_status.sh",
        "semantic_validation/frameworks/spes/spes_collect.sh",
        "semantic_validation/frameworks/spes/spes_stop_all.sh",
        "semantic_validation/start_quest_experiment.sh",
        "semantic_validation/stop_quest_experiment.sh",
        "semantic_validation/instrumentation/quest-operator.js",
        "semantic_validation/instrumentation/semantic-logger.js",
        "semantic_validation/harness/spes_hardware_server.py",
        "semantic_validation/harness/spes_ros_callback_adapter.py",
        "semantic_validation/harness/spes_native_hardware_day.py",
        "semantic_validation/harness/spes_native_hardware_container.sh",
        "semantic_validation/harness/spes_native_sideband.py",
        "semantic_validation/harness/spes_native_hardware_selftest.py",
    ]
    missing = []
    nonexec = []
    for relative in required:
        path = ROOT / relative
        if not path.is_file():
            missing.append(relative)
        elif path.suffix == ".sh" and not os.access(path, os.X_OK):
            nonexec.append(relative)
    add(
        checks,
        "orchestration.required_files",
        PASS if not missing and not nonexec else DEPENDENCY,
        "required launch/logger/collect/stop files are present"
        if not missing and not nonexec
        else "required orchestration files are missing or non-executable",
        missing=missing,
        non_executable=nonexec,
        checked=required,
    )
    add(
        checks,
        "safety.launch_selection",
        PASS,
        "preflight selected no runtime launch and executed no physical driver",
        selected_launch=None,
        forbidden_launches_executed=[],
        quest_used=False,
        robot_driver_used=False,
    )


def writable_check(checks: list[Check], output_dir: Path) -> None:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix=".preflight-write-", dir=output_dir, delete=True) as handle:
            handle.write(b"ok")
            handle.flush()
        passed, error = True, ""
    except OSError as exc:
        passed, error = False, str(exc)
    add(
        checks,
        "outputs.writable",
        PASS if passed else DEPENDENCY,
        "result output directory is writable" if passed else "result output directory is not writable",
        path=str(output_dir),
        error=error,
    )


def unity_checks(checks: list[Check], skip_live_license: bool) -> None:
    editor = Path("/home/cclab/Unity/Hub/Editor/6000.1.6f1/Editor/Unity")
    android = editor.parent / "Data/PlaybackEngines/AndroidPlayer"
    components = {name: android / name for name in ("SDK", "NDK", "OpenJDK")}
    editor_ok = editor.is_file() and os.access(editor, os.X_OK)
    add(
        checks,
        "unity.editor_6000.1.6f1",
        PASS if editor_ok else DEPENDENCY,
        "Unity editor is installed" if editor_ok else "Unity editor is absent",
        path=str(editor),
    )
    modules_ok = android.is_dir() and all(path.is_dir() for path in components.values())
    add(
        checks,
        "unity.android_modules",
        PASS if modules_ok else DEPENDENCY,
        "AndroidPlayer, SDK, NDK, and OpenJDK are installed" if modules_ok else "Unity Android modules are incomplete",
        paths={name: str(path) for name, path in components.items()},
    )
    license_logs = list((SV / "results/runs").glob("picknik_questless_*/unity_batch_import.log"))
    prior = "\n".join(path.read_text(errors="replace") for path in license_logs[-2:])
    live = None
    combined = prior
    if editor_ok and not skip_live_license:
        live = command(
            [str(editor), "-batchmode", "-quit", "-nographics", "-logFile", "-"],
            timeout=45,
        )
        combined += "\n" + live["stdout"] + "\n" + live["stderr"]
    no_entitlement = "Found 0 entitlement groups" in combined or "No valid Unity Editor license found" in combined
    live_success = live is not None and live["returncode"] == 0 and not no_entitlement
    status = PASS if live_success else USER if no_entitlement else DEPENDENCY
    detail = (
        "Unity batchmode license check passed"
        if status == PASS
        else "Unity editor requires operator license entitlement/login"
        if status == USER
        else "Unity license state could not be established"
    )
    live_summary = None
    if live is not None:
        safe_markers = (
            "Unity Editor version:",
            "Batch mode:",
            "Access token is unavailable",
            "Found 0 entitlement groups",
            "No valid Unity Editor license found",
            "Pro License:",
        )
        safe_lines = [
            line.strip()
            for line in (live["stdout"] + "\n" + live["stderr"]).splitlines()
            if any(marker in line for marker in safe_markers)
        ]
        live_summary = {
            "returncode": live["returncode"],
            "timed_out": live["timed_out"],
            "diagnostic_lines": safe_lines,
        }
    add(
        checks,
        "unity.license",
        status,
        detail,
        live_result=live_summary,
        prior_log_count=len(license_logs),
        prior_no_entitlement=no_entitlement,
    )


def app_hardware_checks(checks: list[Check]) -> None:
    picknik_candidates = [
        ROOT / "Builds/picknik_semantic_validation.apk",
        Path("/tmp/picknik_hw_run/Builds/picknik_semantic_validation.apk"),
    ]
    picknik_apk = [str(path) for path in picknik_candidates if path.is_file() and path.stat().st_size > 1024]
    add(
        checks,
        "app.picknik_apk",
        PASS if picknik_apk else USER,
        "PickNik validation APK exists" if picknik_apk else "PickNik validation APK must be built after Unity license activation",
        artifacts=picknik_apk,
    )
    spes_assets = [
        SV / "targets/spes_teleop/teleop/index.html",
        SV / "instrumentation/quest-operator.js",
        SV / "instrumentation/semantic-logger.js",
    ]
    spes_ok = all(path.is_file() for path in spes_assets)
    add(
        checks,
        "app.spes_web_frontend",
        PASS if spes_ok else DEPENDENCY,
        "Spes native WebXR frontend and side-band instrumentation sources are present"
        if spes_ok else "Spes frontend assets are incomplete",
        artifacts=[str(path.relative_to(ROOT)) for path in spes_assets if path.is_file()],
    )
    adb = command(["adb", "devices"], timeout=8)
    devices = []
    if adb["returncode"] == 0:
        devices = [line.split()[0] for line in adb["stdout"].splitlines()[1:] if line.rstrip().endswith("\tdevice")]
    add(
        checks,
        "hardware.quest_connection",
        HARDWARE if not devices else PASS,
        "Quest is intentionally not connected" if not devices else "ADB device is present (not accessed by preflight)",
        adb_returncode=adb["returncode"],
        devices=devices,
        quest_used=False,
    )


def extended_app_readiness_checks(checks: list[Check]) -> None:
    installed_editors = Path("/home/cclab/Unity/Hub/Editor")

    # Docker_Teleop: source-visible Unity app with a repository-owned build method.
    docker_project = SV / "targets/docker_teleop/UnityApp"
    docker_editor = installed_editors / "6000.2.10f1/Editor/Unity"
    docker_build = docker_project / "Assets/Editor/CommandLineQuestBuild.cs"
    build_text = docker_build.read_text(errors="replace") if docker_build.is_file() else ""
    build_ready = (
        "CommandLineQuestBuild" in build_text
        and "BuildQuestApk" in build_text
        and "BuildPipeline.BuildPlayer" in build_text
    )
    add(
        checks,
        "app.docker_teleop.editor_6000.2.10f1",
        PASS if docker_editor.is_file() else USER,
        "exact Docker_Teleop editor is installed"
        if docker_editor.is_file()
        else "install the project-pinned Unity 6000.2.10f1 editor",
        path=str(docker_editor),
    )
    add(
        checks,
        "app.docker_teleop.command_line_build",
        PASS if build_ready else DEPENDENCY,
        "repository CommandLineQuestBuild.BuildQuestApk entry point is present"
        if build_ready else "repository command-line APK build entry point is missing",
        path=str(docker_build.relative_to(ROOT)),
        method="CommandLineQuestBuild.BuildQuestApk",
    )
    docker_apk_candidates = list(docker_project.glob("App_Build/*.apk")) + [
        ROOT / "local_artifacts/quest_apps/docker_teleop/R.U_7.0.7.apk"
    ]
    docker_apks = [str(path) for path in docker_apk_candidates if path.is_file() and path.stat().st_size > 1024]
    add(
        checks,
        "app.docker_teleop.apk",
        PASS if docker_apks else USER,
        "Docker_Teleop APK exists" if docker_apks else "download the documented upstream release APK or build after installing the exact editor and activating Unity",
        artifacts=docker_apks,
    )

    # Quest2ROS2: the pinned repository intentionally contains only the host half.
    q2r = SV / "targets/quest2ros2"
    frontend_markers = list(q2r.rglob("*.unity")) + list(q2r.rglob("AndroidManifest.xml"))
    q2r_apks = [path for path in q2r.rglob("*.apk") if path.stat().st_size > 1024]
    readmes = [path for path in q2r.glob("README*") if path.is_file()]
    readme_text = "\n".join(path.read_text(errors="replace") for path in readmes)
    external_documented = "quest2ros.github.io" in readme_text.lower() and "Quest2ROS" in readme_text
    add(
        checks,
        "app.quest2ros2.frontend_source",
        DEPENDENCY if not frontend_markers else PASS,
        "pinned repository has no Quest frontend source; external black-box app is required"
        if not frontend_markers else "Quest frontend source was found",
        frontend_markers=[str(path.relative_to(q2r)) for path in frontend_markers],
    )
    add(
        checks,
        "app.quest2ros2.install_procedure",
        PASS if external_documented else DEPENDENCY,
        "README documents the external Quest2ROS distribution/configuration path"
        if external_documented else "external Quest2ROS installation procedure is not locally documented",
        documentation=[str(path.relative_to(ROOT)) for path in readmes],
        distribution="quest2ros.github.io" if external_documented else None,
    )
    add(
        checks,
        "app.quest2ros2.artifact",
        PASS if q2r_apks else USER,
        "external Quest2ROS artifact is locally available"
        if q2r_apks else "operator must obtain/install the external Quest2ROS app before the hardware session",
        artifacts=[str(path) for path in q2r_apks],
    )

    # OpenVR: both ALVR and SteamVR are external runtime prerequisites.
    user_root = Path("/home/cclab")
    steam_candidates = [
        Path("/usr/games/steam"),
        user_root / ".steam/steam/steamapps/common/SteamVR/bin/linux64/vrserver",
        user_root / ".local/share/Steam/steamapps/common/SteamVR/bin/linux64/vrserver",
    ]
    alvr_candidates = [
        user_root / ".local/bin/alvr_dashboard",
        user_root / "ALVR/alvr_dashboard",
        user_root / ".local/share/ALVR/alvr_dashboard",
    ]
    steam_present = shutil.which("steam") is not None or any(path.exists() for path in steam_candidates)
    steamvr_present = shutil.which("vrserver") is not None or any("SteamVR" in str(path) and path.exists() for path in steam_candidates)
    alvr_present = shutil.which("alvr_dashboard") is not None or any(path.exists() for path in alvr_candidates)
    add(
        checks,
        "app.openvr_ur5e.alvr",
        PASS if alvr_present else DEPENDENCY,
        "ALVR streamer/dashboard is present" if alvr_present else "install the external ALVR runtime",
        candidates=[str(path) for path in alvr_candidates],
    )
    add(
        checks,
        "app.openvr_ur5e.steamvr",
        PASS if steam_present and steamvr_present else DEPENDENCY,
        "Steam and SteamVR runtime are present" if steam_present and steamvr_present else "install/configure the external SteamVR/OpenVR runtime",
        steam_present=steam_present,
        steamvr_present=steamvr_present,
        candidates=[str(path) for path in steam_candidates],
    )

    # Reachy: full source exists, while its exact editor and APK do not.
    reachy = SV / "targets/reachy_vr_quest"
    reachy_editor = installed_editors / "6000.3.9f1/Editor/Unity"
    reachy_source = (
        (reachy / "ProjectSettings/ProjectVersion.txt").is_file()
        and (reachy / "Assets/Scenes/ReachyMiniTeleop.unity").is_file()
    )
    reachy_apks = [str(path) for path in reachy.rglob("*.apk") if path.stat().st_size > 1024]
    add(
        checks,
        "app.reachy.source",
        PASS if reachy_source else DEPENDENCY,
        "Reachy Unity project and enabled application scene are present"
        if reachy_source else "Reachy Unity application source is incomplete",
        project=str(reachy.relative_to(ROOT)),
    )
    add(
        checks,
        "app.reachy.editor_6000.3.9f1",
        PASS if reachy_editor.is_file() else USER,
        "exact Reachy editor is installed" if reachy_editor.is_file() else "install the project-pinned Unity 6000.3.9f1 editor",
        path=str(reachy_editor),
    )
    add(
        checks,
        "app.reachy.apk",
        PASS if reachy_apks else USER,
        "Reachy APK exists" if reachy_apks else "build or obtain the documented Reachy APK after satisfying editor/license/package requirements",
        artifacts=reachy_apks,
    )

    # Spes: the native app is WebXR packaged in the Python wheel, not an APK.
    wheels = list(Path("/tmp/spes_wheel_readiness").glob("teleop-*.whl"))
    wheel_assets: list[str] = []
    wheel_ok = False
    if wheels:
        try:
            with zipfile.ZipFile(wheels[-1]) as archive:
                names = set(archive.namelist())
            required_assets = {"teleop/index.html", "teleop/assets/teleop-ui.js"}
            wheel_assets = sorted(required_assets & names)
            wheel_ok = required_assets <= names
        except (OSError, zipfile.BadZipFile):
            wheel_ok = False
    add(
        checks,
        "app.spes.wheel",
        PASS if wheel_ok else DEPENDENCY,
        "built Spes wheel contains the native WebXR assets"
        if wheel_ok else "Spes wheel artifact is absent or missing native WebXR assets",
        wheel=str(wheels[-1]) if wheels else None,
        assets=wheel_assets,
    )
    native_assets = [
        SV / "targets/spes_teleop/teleop/index.html",
        SV / "targets/spes_teleop/teleop/assets/teleop-ui.js",
    ]
    add(
        checks,
        "app.spes.native_web_assets",
        PASS if all(path.is_file() for path in native_assets) else DEPENDENCY,
        "pinned Spes source contains both native WebXR assets"
        if all(path.is_file() for path in native_assets) else "pinned Spes native WebXR assets are incomplete",
        assets=[str(path.relative_to(ROOT)) for path in native_assets if path.is_file()],
    )


def overall_status(checks: list[Check]) -> str:
    states = {item.status for item in checks}
    for candidate in (DEPENDENCY, USER, HARDWARE):
        if candidate in states:
            return candidate
    return PASS


def render_markdown(run_id: str, checks: list[Check], overall: str) -> str:
    lines = [
        "# Final Quest preflight",
        "",
        f"- Run: `{run_id}`",
        f"- Overall: **`{overall}`**",
        "- Quest used: `false`",
        "- Physical driver used: `false`",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for item in checks:
        lines.append(f"| `{item.name}` | `{item.status}` | {item.detail.replace('|', '/')} |")
    lines.extend([
        "",
        "`BLOCKED_HARDWARE_NOT_CONNECTED` is expected during this Quest-free run. "
        "`PI_RECEIVED` remains observation-only and does not establish native consumer or actuator acceptance.",
        "",
    ])
    return "\n".join(lines)


def self_test() -> None:
    assert parse_pin(SV / "frameworks/spes/PINNED_REVISION") == "c5d808155a87b584d6147a5943d4b87c34c92db0"
    dummy = [Check("x", PASS, "", {})]
    assert overall_status(dummy) == PASS
    dummy.append(Check("h", HARDWARE, "", {}))
    assert overall_status(dummy) == HARDWARE
    dummy.append(Check("u", USER, "", {}))
    assert overall_status(dummy) == USER
    dummy.append(Check("d", DEPENDENCY, "", {}))
    assert overall_status(dummy) == DEPENDENCY
    assert all(item in STATUSES for item in (PASS, USER, HARDWARE, DEPENDENCY))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--skip-live-unity-license-check", action="store_true")
    parser.add_argument("--self-test-only", action="store_true")
    args = parser.parse_args()
    self_test()
    if args.self_test_only:
        print("FINAL_QUEST_PREFLIGHT_SELF_TEST_PASS")
        return 0

    generated_run_id = "final_quest_preflight_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = (args.output_dir or (SV / "results/runs" / generated_run_id)).resolve()
    run_id = output_dir.name if args.output_dir else generated_run_id
    checks: list[Check] = []
    writable_check(checks, output_dir)
    repo_checks(checks)
    docker_ros_checks(checks)
    pi_checks(checks)
    script_checks(checks)
    unity_checks(checks, args.skip_live_unity_license_check)
    app_hardware_checks(checks)
    extended_app_readiness_checks(checks)
    overall = overall_status(checks)
    document = {
        "schema": "final-quest-preflight-v1",
        "run_id": run_id,
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "overall": overall,
        "quest_used": False,
        "physical_driver_used": False,
        "checks": [asdict(item) for item in checks],
    }
    (output_dir / "preflight.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    (output_dir / "preflight.md").write_text(render_markdown(run_id, checks, overall), encoding="utf-8")
    print(json.dumps({"run_id": run_id, "overall": overall, "counts": {
        status: sum(item.status == status for item in checks) for status in sorted(STATUSES)
    }, "json": str(output_dir / "preflight.json"), "markdown": str(output_dir / "preflight.md")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
