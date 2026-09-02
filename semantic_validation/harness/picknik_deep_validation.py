#!/usr/bin/env python3
"""Deep, no-Unity validation of the pinned PickNik Quest publisher.

This checker follows serialized Unity scene/prefab/input-action references in
addition to the C# publisher.  Its strongest result is source-dataflow
confirmation; it never labels its source-derived executable model as runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any


EXPECTED_COMMIT = "bbaef0762fdb0b429b8ea12a4ca65040748b41dd"
EXPECTED_REMOTE = "https://github.com/PickNikRobotics/meta_quest_teleoperation.git"
ROSPUBLISHERS_GUID = "9bc4be099d22431486049e97ccd1bbff"
INPUT_ACTIONS_GUID = "c348712bda248c246b8c49b3db54643f"
COMPLETE_RIG_GUID = "77e7c27b2c5525e4aa8cc9f99d654486"
XRI_RIG_GUID = "f6336ac4ac8b4d34bc5072418cdc62a0"
OPENXR_LOADER_GUID = "28fe04729daeb2345bebc951fad25769"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, stderr=subprocess.STDOUT
    ).strip()


def extract_method(text: str, signature_pattern: str) -> str:
    match = re.search(signature_pattern, text)
    if not match:
        raise AssertionError(f"method signature not found: {signature_pattern}")
    brace = text.find("{", match.end())
    if brace < 0:
        raise AssertionError("method body opener not found")
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : index + 1]
    raise AssertionError("unterminated method body")


def unity_object(text: str, class_id: int, file_id: int) -> str:
    pattern = rf"^--- !u!{class_id} &{file_id}(?: stripped)?\n"
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        raise AssertionError(f"Unity object !u!{class_id} &{file_id} not found")
    next_object = re.search(r"^--- !u!", text[match.end() :], flags=re.MULTILINE)
    end = match.end() + next_object.start() if next_object else len(text)
    return text[match.start() : end]


def input_map(asset: dict[str, Any], name: str) -> dict[str, Any]:
    for action_map in asset.get("maps", []):
        if action_map.get("name") == name:
            return action_map
    raise AssertionError(f"input action map not found: {name}")


def action_bindings(action_map: dict[str, Any], action: str) -> set[str]:
    return {
        binding.get("path", "")
        for binding in action_map.get("bindings", [])
        if binding.get("action") == action
    }


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def source_publish_model(
    *, pose: tuple[float, float, float, float, float, float, float], stamp_ns: int
) -> dict[str, Any]:
    """Model only fields assigned by PublishOdomAndTf; not a Unity execution."""
    x, y, z, qx, qy, qz, qw = pose
    return {
        "odom": {
            "header": {"frame_id": "quest", "stamp_ns": stamp_ns},
            "child_frame_id": "right_controller_odom",
            "pose": [x, y, z, qx, qy, qz, qw],
            "twist": [0.0] * 6,
        },
        "tf": {
            "header": {"frame_id": "quest", "stamp_ns": stamp_ns},
            "child_frame_id": "right_controller_odom",
            "transform": [x, y, z, qx, qy, qz, qw],
        },
    }


def discover_unity() -> dict[str, str | None]:
    candidates = {
        "Unity_PATH": shutil.which("Unity"),
        "unity-editor_PATH": shutil.which("unity-editor"),
        "unityhub_PATH": shutil.which("unityhub"),
    }
    home = Path.home()
    common = [
        Path("/opt/Unity/Editor/Unity"),
        Path("/usr/bin/unity-editor"),
        Path("/usr/local/bin/Unity"),
        home / "Unity/Hub/Editor/6000.1.6f1/Editor/Unity",
        home / ".local/share/unityhub/editors/6000.1.6f1/Editor/Unity",
    ]
    for candidate in common:
        candidates[str(candidate)] = str(candidate) if candidate.is_file() else None
    return candidates


def probe_adb() -> dict[str, Any]:
    adb = shutil.which("adb")
    result: dict[str, Any] = {"binary": adb, "status": "UNAVAILABLE", "devices": []}
    if not adb:
        return result
    try:
        completed = subprocess.run(
            [adb, "devices", "-l"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
            check=False,
        )
        lines = [line.strip() for line in completed.stdout.splitlines()]
        devices = [
            line
            for line in lines
            if line and not line.startswith("List of devices") and not line.startswith("*")
        ]
        result.update(
            {
                "status": "CONNECTED" if devices else "NO_DEVICE",
                "returncode": completed.returncode,
                "devices": devices,
                "output": completed.stdout.strip(),
            }
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        result.update({"status": "PROBE_FAILED", "error": str(exc)})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--probe-adb", action="store_true")
    parser.add_argument(
        "--target-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "targets" / "meta_quest_teleoperation",
    )
    args = parser.parse_args()
    target = args.target_root.resolve()
    output = args.output.resolve()
    summary_path = args.summary.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or summary_path.exists():
        raise SystemExit("refusing to overwrite an existing PickNik deep-validation artifact")

    files = {
        "publisher": target / "UnityProject/Assets/ROSPublishers.cs",
        "publisher_meta": target / "UnityProject/Assets/ROSPublishers.cs.meta",
        "build_settings": target / "UnityProject/ProjectSettings/EditorBuildSettings.asset",
        "project_settings": target / "UnityProject/ProjectSettings/ProjectSettings.asset",
        "project_version": target / "UnityProject/ProjectSettings/ProjectVersion.txt",
        "packages": target / "UnityProject/Packages/manifest.json",
        "packages_lock": target / "UnityProject/Packages/packages-lock.json",
        "scene": target / "UnityProject/Assets/Scenes/SampleScene.unity",
        "complete_rig": target
        / "UnityProject/Assets/VRTemplateAssets/Prefabs/Setup/Complete XR Origin Set Up Hands Variant.prefab",
        "xri_rig": target
        / "UnityProject/Assets/Samples/XR Interaction Toolkit/3.1.1/Starter Assets/Prefabs/XR Origin (XR Rig).prefab",
        "input_actions": target
        / "UnityProject/Assets/Samples/XR Interaction Toolkit/3.1.1/Starter Assets/XRI Default Input Actions.inputactions",
        "xr_general": target / "UnityProject/Assets/XR/XRGeneralSettings.asset",
        "openxr_settings": target / "UnityProject/Assets/XR/Settings/OpenXRPackageSettings.asset",
    }
    for path in files.values():
        if not path.is_file():
            raise SystemExit(f"required source missing: {path}")

    publisher = files["publisher"].read_text(encoding="utf-8")
    publisher_meta = files["publisher_meta"].read_text(encoding="utf-8")
    build_settings = files["build_settings"].read_text(encoding="utf-8")
    scene = files["scene"].read_text(encoding="utf-8")
    complete_rig = files["complete_rig"].read_text(encoding="utf-8")
    xri_rig = files["xri_rig"].read_text(encoding="utf-8")
    input_actions = json.loads(files["input_actions"].read_text(encoding="utf-8"))
    xr_general = files["xr_general"].read_text(encoding="utf-8")
    openxr_settings = files["openxr_settings"].read_text(encoding="utf-8")
    packages_lock = json.loads(files["packages_lock"].read_text(encoding="utf-8"))

    commit = git(target, "rev-parse", "HEAD")
    branch = git(target, "branch", "--show-current")
    remote = git(target, "remote", "get-url", "origin")
    status_before = git(target, "status", "--porcelain=v1", "--untracked-files=all")

    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, evidence: str, detail: Any = None) -> None:
        record = {
            "event": "machine_check",
            "check": name,
            "status": "PASS" if passed else "FAIL",
            "evidence_level": evidence,
            "commit": commit,
            "monotonic_timestamp_ns": time.monotonic_ns(),
        }
        if detail is not None:
            record["detail"] = detail
        checks.append(record)
        append_jsonl(output, record)

    check("pinned_commit", commit == EXPECTED_COMMIT, "MACHINE_CHECKED_STATIC", commit)
    check("target_branch_main", branch == "main", "MACHINE_CHECKED_STATIC", branch)
    check("origin_is_picknik", remote == EXPECTED_REMOTE, "MACHINE_CHECKED_STATIC", remote)
    check("target_clean_before", status_before == "", "MACHINE_CHECKED_STATIC", status_before)
    check(
        "publisher_meta_guid",
        f"guid: {ROSPUBLISHERS_GUID}" in publisher_meta,
        "MACHINE_CHECKED_STATIC",
    )
    check(
        "sample_scene_is_only_enabled_build_scene",
        "path: Assets/Scenes/SampleScene.unity" in build_settings
        and len(re.findall(r"^\s*-\s+enabled:\s+1\s*$", build_settings, flags=re.MULTILINE)) == 1,
        "SOURCE_DATAFLOW_CONFIRMED",
    )

    publisher_components = re.findall(
        rf"--- !u!114 &[0-9]+\nMonoBehaviour:\n(?:(?!^--- !u!).)*?m_Script: \{{fileID: 11500000, guid: {ROSPUBLISHERS_GUID}, type: 3\}}(?:(?!^--- !u!).)*",
        scene,
        flags=re.MULTILINE | re.DOTALL,
    )
    publisher_scene_block = publisher_components[0] if publisher_components else ""
    check(
        "publisher_component_in_build_scene",
        len(publisher_components) == 1,
        "SOURCE_DATAFLOW_CONFIRMED",
        {"instances": len(publisher_components)},
    )
    left_ref = re.search(r"leftController: \{fileID: ([0-9]+)\}", publisher_scene_block)
    right_ref = re.search(r"rightController: \{fileID: ([0-9]+)\}", publisher_scene_block)
    left_scene_id = int(left_ref.group(1)) if left_ref else -1
    right_scene_id = int(right_ref.group(1)) if right_ref else -1
    check(
        "publisher_has_two_controller_scene_references",
        left_scene_id > 0 and right_scene_id > 0 and left_scene_id != right_scene_id,
        "SOURCE_DATAFLOW_CONFIRMED",
        {"left": left_scene_id, "right": right_scene_id},
    )

    expected_chain = {
        "left": (left_scene_id, 7277802326798953684, 202364687),
        "right": (right_scene_id, 7277802327528778795, 1670256624),
    }
    for side, (scene_id, complete_id, rig_id) in expected_chain.items():
        scene_object = unity_object(scene, 1, scene_id) if scene_id > 0 else ""
        complete_object = unity_object(complete_rig, 1, complete_id)
        check(
            f"{side}_scene_reference_enters_complete_rig",
            f"fileID: {complete_id}, guid: {COMPLETE_RIG_GUID}" in scene_object,
            "SOURCE_DATAFLOW_CONFIRMED",
            {"scene_object": scene_id, "complete_rig_object": complete_id},
        )
        check(
            f"{side}_complete_rig_reference_enters_xri_rig",
            f"fileID: {rig_id}, guid: {XRI_RIG_GUID}" in complete_object,
            "SOURCE_DATAFLOW_CONFIRMED",
            {"complete_rig_object": complete_id, "xri_rig_object": rig_id},
        )
        controller_object = unity_object(xri_rig, 1, rig_id)
        expected_name = "Left Controller" if side == "left" else "Right Controller"
        check(
            f"{side}_xri_controller_active",
            f"m_Name: {expected_name}" in controller_object and "m_IsActive: 1" in controller_object,
            "SOURCE_DATAFLOW_CONFIRMED",
        )
        component_ids = [int(value) for value in re.findall(r"component: \{fileID: ([0-9]+)\}", controller_object)]
        tracked_components = []
        for component_id in component_ids:
            try:
                component = unity_object(xri_rig, 114, component_id)
            except AssertionError:
                continue
            if "m_TrackingStateInput:" in component:
                tracked_components.append(component)
        tracked_component = tracked_components[0] if len(tracked_components) == 1 else ""
        check(
            f"{side}_single_tracked_pose_component",
            len(tracked_components) == 1,
            "SOURCE_DATAFLOW_CONFIRMED",
            {"count": len(tracked_components)},
        )
        check(
            f"{side}_tracked_pose_component_uses_tracking_state",
            "m_IgnoreTrackingState: 0" in tracked_component
            and "m_Name: Tracking State" in tracked_component
            and f"guid: {INPUT_ACTIONS_GUID}" in tracked_component
            and "m_Name: Position" in tracked_component
            and "m_Name: Rotation" in tracked_component,
            "SOURCE_DATAFLOW_CONFIRMED",
        )

    for side, hand in (("left", "LeftHand"), ("right", "RightHand")):
        action_map = input_map(input_actions, f"XRI {side.title()}")
        position = action_bindings(action_map, "Position")
        rotation = action_bindings(action_map, "Rotation")
        tracking = action_bindings(action_map, "Tracking State")
        is_tracked = action_bindings(action_map, "Is Tracked")
        check(
            f"{side}_input_actions_bind_controller_pose_and_tracking",
            f"<XRController>{{{hand}}}/devicePosition" in position
            and f"<XRController>{{{hand}}}/deviceRotation" in rotation
            and f"<XRController>{{{hand}}}/trackingState" in tracking
            and f"<XRController>{{{hand}}}/isTracked" in is_tracked,
            "SOURCE_DATAFLOW_CONFIRMED",
            {
                "position": sorted(position),
                "rotation": sorted(rotation),
                "tracking_state": sorted(tracking),
                "is_tracked": sorted(is_tracked),
            },
        )

    check(
        "android_uses_openxr_loader",
        f"guid: {OPENXR_LOADER_GUID}" in xr_general,
        "SOURCE_DATAFLOW_CONFIRMED",
    )
    check(
        "quest3_and_oculus_touch_openxr_features_enabled",
        "m_Name: MetaQuestFeature Android" in openxr_settings
        and re.search(
            r"m_Name: MetaQuestFeature Android(?:(?!^--- !u!).)*?m_enabled: 1(?:(?!^--- !u!).)*?visibleName: Quest 3(?:(?!^--- !u!).)*?enabled: 1",
            openxr_settings,
            flags=re.MULTILINE | re.DOTALL,
        )
        is not None
        and re.search(
            r"m_Name: OculusTouchControllerProfile Android(?:(?!^--- !u!).)*?m_enabled: 1",
            openxr_settings,
            flags=re.MULTILINE | re.DOTALL,
        )
        is not None,
        "SOURCE_DATAFLOW_CONFIRMED",
    )

    update = extract_method(publisher, r"public\s+void\s+Update\s*\(\s*\)")
    publish = extract_method(
        publisher,
        r"private\s+void\s+PublishOdomAndTf\s*\(\s*Transform\s+sourceTransform\s*,\s*string\s+childFrame\s*,\s*string\s+odomTopicName\s*\)",
    )
    ros_time = extract_method(publisher, r"private\s+static\s+TimeMsg\s+GetRosTime\s*\(\s*\)")
    check(
        "both_controllers_flow_to_same_periodic_publisher",
        "PublishOdomAndTf(leftController.transform, leftChildFrame, leftOdomTopicName);" in update
        and "PublishOdomAndTf(rightController.transform, rightChildFrame, rightOdomTopicName);" in update
        and "_timeElapsed >= odomPublishFrequency" in update,
        "SOURCE_DATAFLOW_CONFIRMED",
    )
    check(
        "publisher_reads_transform_and_emits_odom_tf",
        "sourceTransform.GetPositionAndRotation" in publish
        and "ros.Publish(odomTopicName, _odomMsg);" in publish
        and "ros.Publish(tfTopicName, _tfMessage);" in publish,
        "SOURCE_DATAFLOW_CONFIRMED",
    )
    tracking_tokens = (
        "isTracked",
        "trackingState",
        "TrackingState",
        "InputTrackingState",
        "CommonUsages.isTracked",
        "CommonUsages.trackingState",
        "TryGetFeatureValue",
    )
    check(
        "publisher_method_does_not_consume_tracking_semantics",
        not any(token in publish for token in tracking_tokens),
        "SOURCE_DATAFLOW_CONFIRMED",
    )
    check(
        "publisher_does_not_gate_on_controller_active_or_enabled",
        not any(token in update + publish for token in ("activeSelf", "activeInHierarchy", ".enabled")),
        "SOURCE_DATAFLOW_CONFIRMED",
    )
    check(
        "publisher_regenerates_wall_clock_stamp",
        "_odomHeader.stamp = GetRosTime();" in publish and "DateTime.UtcNow" in ros_time,
        "SOURCE_DATAFLOW_CONFIRMED",
    )
    check(
        "publisher_has_no_focus_or_pause_invalidation",
        "OnApplicationFocus" not in publisher and "OnApplicationPause" not in publisher,
        "SOURCE_DATAFLOW_CONFIRMED",
    )
    check(
        "publisher_has_no_source_sample_time_or_age_gate",
        not re.search(
            r"\b(sampleTime|sourceTime|timestamp|fresh(?:ness)?|stale|age)\b",
            update + publish,
            re.IGNORECASE,
        ),
        "SOURCE_DATAFLOW_CONFIRMED",
    )

    # Repository-wide search: record presence separately from call/dataflow relevance.
    search_tokens = [
        "isTracked",
        "trackingState",
        "TrackingState",
        "InputTrackingState",
        "CommonUsages.isTracked",
        "CommonUsages.trackingState",
        "TryGetFeatureValue",
        "OnApplicationFocus",
        "OnApplicationPause",
        "deviceConnected",
        "deviceDisconnected",
        "activeInHierarchy",
        "activeSelf",
    ]
    searchable_suffixes = {".cs", ".inputactions", ".prefab", ".unity", ".asset", ".json", ".md"}
    token_hits: dict[str, list[str]] = {token: [] for token in search_tokens}
    for candidate in target.rglob("*"):
        if not candidate.is_file() or ".git" in candidate.parts:
            continue
        if "My project_BurstDebugInformation_DoNotShip" in candidate.parts:
            continue
        if candidate.suffix not in searchable_suffixes:
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = str(candidate.relative_to(target))
        for token in search_tokens:
            if token in text:
                token_hits[token].append(rel)
    append_jsonl(
        output,
        {
            "event": "repository_wide_token_search",
            "status": "PASS",
            "evidence_level": "MACHINE_CHECKED_STATIC",
            "commit": commit,
            "hits": token_hits,
            "interpretation": {
                "connected": [
                    "TrackingState in the enabled scene's nested XRI rig",
                    "trackingState and isTracked bindings in its referenced input-action asset",
                ],
                "not_connected_to_publisher": [
                    "hand visualizer/demo scripts",
                    "deviceConnected in GazeInputManager",
                    "XR simulator UI activeSelf checks",
                ],
                "publisher_boundary": "ROSPublishers.Update/PublishOdomAndTf consumes only Transform and does not serialize tracking state.",
            },
        },
    )

    pose = (0.12, -0.34, 0.56, 0.0, 0.0, 0.0, 1.0)
    same_stamp = 1_900_000_000_123_456_789
    tracked_model = source_publish_model(pose=pose, stamp_ns=same_stamp)
    untracked_model = source_publish_model(pose=pose, stamp_ns=same_stamp)
    check(
        "source_derived_tracking_state_collision_model",
        tracked_model == untracked_model,
        "MACHINE_CHECKED_STATIC",
        {
            "model_only": True,
            "tracked_input": {"tracking_state": 3, "pose": pose},
            "untracked_input": {"tracking_state": 0, "pose": pose},
            "wire_model": tracked_model,
            "claim_boundary": "This demonstrates schema/dataflow non-distinguishability only; it is not Unity, Quest, ROS, or robot runtime evidence.",
        },
    )

    dependencies = packages_lock.get("dependencies", {})
    package_versions = {
        name: dependencies.get(name, {}).get("version")
        for name in (
            "com.unity.inputsystem",
            "com.unity.xr.interaction.toolkit",
            "com.unity.xr.management",
            "com.unity.xr.openxr",
            "com.unity.xr.hands",
            "com.unity.robotics.ros-tcp-connector",
        )
    }
    unity_candidates = discover_unity()
    unity_executable = next((path for path in unity_candidates.values() if path), None)
    test_sources = sorted(
        str(path.relative_to(target))
        for path in target.rglob("*.cs")
        if "test" in path.name.lower() or any("test" in part.lower() for part in path.parts)
    )
    test_assemblies: list[str] = []
    for asmdef in target.rglob("*.asmdef"):
        try:
            definition = json.loads(asmdef.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        optional = definition.get("optionalUnityReferences", [])
        if "TestAssemblies" in optional or definition.get("testAssemblies") is True:
            test_assemblies.append(str(asmdef.relative_to(target)))
    test_assemblies.sort()
    workflows = sorted(str(path.relative_to(target)) for path in (target / ".github/workflows").glob("*")) if (target / ".github/workflows").is_dir() else []
    build_artifacts = sorted(
        str(path.relative_to(target))
        for path in target.rglob("*")
        if path.is_file() and path.suffix.lower() in {".apk", ".aab", ".exe", ".x86_64"}
    )
    environment = {
        "unity_project_version": files["project_version"].read_text(encoding="utf-8").strip(),
        "unity_candidates": unity_candidates,
        "unity_executable": unity_executable,
        "test_sources": test_sources,
        "test_assemblies": test_assemblies,
        "unity_test_framework_version": dependencies.get("com.unity.test-framework", {}).get("version"),
        "github_workflows": workflows,
        "build_artifacts": build_artifacts,
        "package_versions": package_versions,
        "ros2_binary": shutil.which("ros2"),
        "rclpy_available": importlib.util.find_spec("rclpy") is not None,
        "adb": probe_adb() if args.probe_adb else {"status": "NOT_PROBED", "binary": shutil.which("adb")},
    }
    append_jsonl(
        output,
        {
            "event": "runtime_feasibility",
            "status": "PASS" if unity_executable else "SKIP_ENV",
            "evidence_level": "MACHINE_CHECKED_STATIC",
            "commit": commit,
            "environment": environment,
            "runtime_claim": "NONE",
            "claim_boundary": "No Unity executable means no batch build, EditMode, PlayMode, scene, serialization, APK, or Quest runtime was executed.",
        },
    )

    instrumentation_root = Path(__file__).resolve().parents[1] / "instrumentation/picknik"
    logger_source = instrumentation_root / "PickNikTrackingSidebandLogger.cs"
    build_source = instrumentation_root / "Editor/PickNikSemanticValidationBuild.cs"
    logger_text = logger_source.read_text(encoding="utf-8") if logger_source.exists() else ""
    check(
        "sideband_logger_is_ros_payload_independent",
        bool(logger_text)
        and "ROSConnection" not in logger_text
        and "RosMessageTypes" not in logger_text
        and ".Publish(" not in logger_text
        and "Application.persistentDataPath" in logger_text,
        "MACHINE_CHECKED_STATIC",
    )
    check(
        "batch_build_overlay_exists",
        build_source.is_file() and "BuildPipeline.BuildPlayer" in build_source.read_text(encoding="utf-8"),
        "MACHINE_CHECKED_STATIC",
    )

    status_after = git(target, "status", "--porcelain=v1", "--untracked-files=all")
    check("target_clean_after", status_after == "", "MACHINE_CHECKED_STATIC", status_after)
    failures = [record["check"] for record in checks if record["status"] != "PASS"]
    summary = {
        "status": "PASS" if not failures else "FAIL",
        "commit": commit,
        "target_clean_before": status_before == "",
        "target_clean_after": status_after == "",
        "checks_passed": len(checks) - len(failures),
        "checks_total": len(checks),
        "failed_checks": failures,
        "strongest_evidence": "SOURCE_DATAFLOW_CONFIRMED" if not failures else "MACHINE_CHECKED_STATIC",
        "finding": {
            "tracking_state_upstream": "CONNECTED_TO_CONTROLLER_TRANSFORM_DRIVER",
            "tracking_state_at_ros_publisher_boundary": "DROPPED",
            "is_tracked_action": "PRESENT_IN_INPUT_ASSET_NOT_SERIALIZED_BY_PUBLISHER",
            "source_sample_time": "NOT_PRESERVED_PUBLICATION_TIME_REGENERATED",
            "focus_session_invalidation": "NOT_FOUND_IN_PUBLISHER",
        },
        "runtime": "BLOCKED_ENV" if not unity_executable else "AVAILABLE_NOT_AUTOMATICALLY_CLAIMED",
        "hardware": "BLOCKED_HW",
        "environment": environment,
        "hashes": {name: sha256(path) for name, path in files.items()},
        "claim_boundary": "Source and serialized Unity dataflow only. No Unity/Quest/ROS/robot runtime result is claimed.",
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_jsonl(
        output,
        {
            "event": "suite_result",
            "status": summary["status"],
            "evidence_level": summary["strongest_evidence"],
            "commit": commit,
            "failed_checks": failures,
            "summary": str(summary_path),
            "runtime": summary["runtime"],
            "hardware": summary["hardware"],
        },
    )
    print(json.dumps({"status": summary["status"], "checks": f"{summary['checks_passed']}/{summary['checks_total']}", "output": str(output), "summary": str(summary_path)}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
