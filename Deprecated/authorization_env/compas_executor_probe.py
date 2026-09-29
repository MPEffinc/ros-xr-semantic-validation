#!/opt/compas-venv/bin/python
"""Offline COMPAS XR executor-boundary audit at the fixed source revisions.

This probe deliberately does not invent a robot executor.  It checks the
official message schema, packaged Grasshopper component, and shipped GHX
example to determine where COMPAS XR stops and project-specific robot control
must begin.  It performs no network access and never contacts a controller.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


COMPAS_XR_REVISION = "b86e6fbbacdc8e84183fc08c846176a1c79304ca"
COMPAS_UNITY_REVISION = "f1516ca568b101447507aebc28a594bdc358df3e"


def git_head(repository: Path) -> str:
    return subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={repository}",
            "-C",
            str(repository),
            "rev-parse",
            "HEAD",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def line_number(text: str, marker: str, start: int = 0) -> int:
    offset = text.find(marker, start)
    if offset < 0:
        raise AssertionError(f"required source marker not found: {marker!r}")
    return text.count("\n", 0, offset) + 1


def source_span(
    root: Path,
    repository: Path,
    revision: str,
    path: Path,
    first_marker: str,
    last_marker: str | None = None,
) -> str:
    text = path.read_text(encoding="utf-8")
    first = line_number(text, first_marker)
    last = first if last_marker is None else line_number(text, last_marker, text.find(first_marker))
    relative_repository = repository.relative_to(root)
    relative_file = path.relative_to(repository)
    return f"{relative_repository}@{revision}:{relative_file}:{first}-{last}"


def direct_items(chunk: ElementTree.Element) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    items = chunk.find("items")
    if items is None:
        return values
    for item in items.findall("item"):
        name = item.attrib.get("name", "")
        values.setdefault(name, []).append(item.text or "")
    return values


def audit_official_ghx(path: Path) -> dict[str, Any]:
    tree = ElementTree.parse(path)
    root = tree.getroot()
    containers = [chunk for chunk in root.iter("chunk") if chunk.attrib.get("name") == "Container"]

    execution_container: ElementTree.Element | None = None
    for container in containers:
        items = direct_items(container)
        if "Execution Service" in items.get("NickName", []):
            execution_container = container
            break
    if execution_container is None:
        raise AssertionError("official GHX Execution Service component not found")

    output_parameters: list[dict[str, str]] = []
    for chunk in execution_container.iter("chunk"):
        if chunk.attrib.get("name") != "OutputParam":
            continue
        items = direct_items(chunk)
        output_parameters.append(
            {
                "name": items.get("Name", [""])[0],
                "nickname": items.get("NickName", [""])[0],
                "guid": items.get("InstanceGuid", [""])[0],
            }
        )

    consumers: dict[str, list[str]] = {}
    for output in output_parameters:
        guid = output["guid"]
        consumers[output["name"]] = []
        for container in containers:
            items = direct_items(container)
            if guid in items.get("Source", []):
                consumers[output["name"]].append(
                    items.get("NickName", items.get("Name", ["unnamed"]))[0]
                )

    all_items = list(root.iter("item"))
    code_inputs = [item.text or "" for item in all_items if item.attrib.get("name") == "CodeInput"]
    user_text = "\n".join(
        item.text or "" for item in all_items if item.attrib.get("name") in {"Text", "UserText"}
    )
    execution_code = next(
        code for code in code_inputs if "from compas_xr.mqtt import SendTrajectory" in code
    )
    robot_api_tokens = (
        "rtde_control",
        "RTDEControlInterface",
        "compas_rrc",
        "MoveGroupCommander",
        "FollowJointTrajectory",
        "execute_joint_trajectory",
        "send_goal",
        "move_group.execute",
    )

    return {
        "path": str(path),
        "execution_service_present": True,
        "execution_service_outputs": [output["name"] for output in output_parameters],
        "execution_service_output_consumers": consumers,
        "trajectory_output_present": any(
            "trajectory" in output["name"].lower() for output in output_parameters
        ),
        "embedded_component_reads_trajectory": ".trajectory" in execution_code,
        "embedded_component_returns_only_element_and_robot": (
            "return element_id, robot_name" in execution_code
        ),
        "project_specific_control_placeholder": "DEFINE ROBOTIC CONTROL" in user_text,
        "placeholder_examples": all(token in user_text for token in ("RRC", "RTDE(UR)", "UR SCRIPT")),
        "implemented_robot_control_api_tokens": [
            token for token in robot_api_tokens if any(token in code for code in code_inputs)
        ],
    }


def audit_runtime_schema(compas_source: Path) -> dict[str, Any]:
    sys.path.insert(0, str(compas_source))
    try:
        from compas_xr.mqtt.messages import ApproveTrajectory, Header, SendTrajectory
    except Exception as exc:  # pragma: no cover - environment evidence
        return {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    trajectory_a = {
        "joint_1": [0.10, 0.20, 0.30],
        "joint_2": [0.00, 0.10, 0.20],
    }
    trajectory_b = {
        "joint_1": [1.10, 1.20, 1.30],
        "joint_2": [0.90, 1.00, 1.10],
    }
    element = "assembly-step-7"
    robot = "ur10e-local-probe"

    def header(sequence: int) -> Header:
        return Header(
            sequence_id=sequence,
            response_id=501,
            device_id="offline-schema-probe",
            time_stamp=f"offline-{sequence}",
        )

    approval_a = ApproveTrajectory(element, robot, trajectory_a, 1, header=header(1))
    send_a = SendTrajectory(element, robot, trajectory_a, header=header(2))
    send_b = SendTrajectory(element, robot, trajectory_b, header=header(3))
    fields = sorted(send_a.data.keys())
    approval_fields = {
        "approval",
        "approval_status",
        "approved_digest",
        "approval_digest",
        "approvers",
        "authorization_epoch",
        "trajectory_version",
    }

    return {
        "available": True,
        "trajectory_a_sha256": canonical_digest(trajectory_a),
        "trajectory_b_sha256": canonical_digest(trajectory_b),
        "digests_differ": canonical_digest(trajectory_a) != canonical_digest(trajectory_b),
        "approval_trajectory_id": approval_a.trajectory_id,
        "send_a_trajectory_id": send_a.trajectory_id,
        "send_b_trajectory_id": send_b.trajectory_id,
        "different_content_same_trajectory_id": (
            send_a.trajectory_id == send_b.trajectory_id
            and canonical_digest(trajectory_a) != canonical_digest(trajectory_b)
        ),
        "send_fields": fields,
        "approval_binding_fields": sorted(approval_fields.intersection(fields)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="ros_xr workspace root",
    )
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    compas_repository = workspace / "frameworks/compas_xr"
    unity_repository = workspace / "frameworks/compas_xr_unity_assembly"

    messages_path = compas_repository / "src/compas_xr/mqtt/messages.py"
    component_path = (
        compas_repository
        / "src/compas_xr/ghpython/components/Cx_SendTrajectory/code.py"
    )
    metadata_path = component_path.with_name("metadata.json")
    userguide_path = compas_repository / "docs/userguide.md"
    example_directory = compas_repository / "docs/examples/scripts"
    ghx_path = example_directory / "ex2_robotic_trajectory_visualization_example.ghx"
    unity_ui_path = unity_repository / "Assets/Scripts/UIFunctionalities.cs"
    unity_messages_path = unity_repository / "Assets/Scripts/MQTTDataCompasXR.cs"

    observed_compas_revision = git_head(compas_repository)
    observed_unity_revision = git_head(unity_repository)
    component_source = component_path.read_text(encoding="utf-8")
    component_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    userguide_source = userguide_path.read_text(encoding="utf-8")
    official_examples = sorted(
        str(path.relative_to(compas_repository))
        for path in example_directory.iterdir()
        if path.suffix.lower() in {".gh", ".ghx"}
    )

    ghx_audit = audit_official_ghx(ghx_path)
    runtime_schema = audit_runtime_schema(compas_repository / "src")
    packaged_outputs = [
        item["name"] for item in component_metadata["ghpython"]["outputParameters"]
    ]

    results: dict[str, Any] = {
        "probe": "COMPAS XR official executor boundary audit",
        "safety_scope": {
            "network_access": False,
            "public_broker": False,
            "robot_or_controller": False,
            "invented_executor": False,
            "activity": "fixed-source, official-example, and local schema inspection only",
        },
        "fixed_revisions": {
            "compas_xr": observed_compas_revision,
            "compas_xr_expected": COMPAS_XR_REVISION,
            "compas_xr_unity_assembly": observed_unity_revision,
            "compas_xr_unity_expected": COMPAS_UNITY_REVISION,
        },
        "official_artifact_inventory": {
            "grasshopper_definitions": official_examples,
            "gh_count": sum(path.endswith(".gh") for path in official_examples),
            "ghx_count": sum(path.endswith(".ghx") for path in official_examples),
            "execution_example": str(ghx_path.relative_to(compas_repository)),
        },
        "packaged_execution_component": {
            "subscribes_to_send_trajectory": (
                "Topic(topic_name_request, SendTrajectory)" in component_source
            ),
            "forwards_full_message_to_worker": "worker.update_result(request_message, 10)"
            in component_source,
            "reads_trajectory_for_output": ".trajectory" in component_source,
            "outputs": packaged_outputs,
            "returns_only_element_and_robot": "return element_id, robot_name" in component_source,
            "approval_or_digest_check": any(
                token in component_source
                for token in ("approval_status", "approved_digest", "trajectory_digest", "sha256")
            ),
        },
        "official_ghx_execution_boundary": ghx_audit,
        "schema_runtime": runtime_schema,
        "documentation_boundary": {
            "requires_additional_cad_input_for_execution": (
                "additional user input is required on the CAD from\n"
                "each user for both planning and execution of trajectories"
                in userguide_source
            ),
            "calls_execution_service_custom_subscriber": (
                "Execution Service component is a custom subscriber" in userguide_source
            ),
            "documentation_claims_robot_transfer": (
                "this component transmits the trajectory details" in userguide_source
            ),
            "source_example_exposes_trajectory_output": ghx_audit["trajectory_output_present"],
            "documentation_source_mismatch": (
                "this component transmits the trajectory details" in userguide_source
                and not ghx_audit["trajectory_output_present"]
            ),
        },
        "source_trace": {
            "send_schema": source_span(
                workspace,
                compas_repository,
                observed_compas_revision,
                messages_path,
                "class SendTrajectory(Message):",
                'return cls(data["element_id"], data["robot_name"], data["trajectory"], Header.parse(data["header"]))',
            ),
            "packaged_subscriber": source_span(
                workspace,
                compas_repository,
                observed_compas_revision,
                component_path,
                "def start_server(worker, options):",
                "worker.display_message(\"Subscribed\")",
            ),
            "packaged_outputs": source_span(
                workspace,
                compas_repository,
                observed_compas_revision,
                component_path,
                "if hasattr(self.worker, \"result\"):",
                "return None, None",
            ),
            "custom_integration_documentation": source_span(
                workspace,
                compas_repository,
                observed_compas_revision,
                userguide_path,
                "COMPAS XR does not provide the complete planning routine",
                "capabilities.",
            ),
            "execution_subscriber_documentation": source_span(
                workspace,
                compas_repository,
                observed_compas_revision,
                userguide_path,
                "#### Step 5.2.4: Send Trajectory Subscriber",
                "topic = 'compas_xr/send_trajectory/project_name'",
            ),
            "official_ghx_embedded_subscriber": source_span(
                workspace,
                compas_repository,
                observed_compas_revision,
                ghx_path,
                "from compas_xr.mqtt import SendTrajectory",
                "return None, None",
            ),
            "official_ghx_control_placeholder": source_span(
                workspace,
                compas_repository,
                observed_compas_revision,
                ghx_path,
                "DEFINE ROBOTIC CONTROL....",
                "- ex. RRC, RTDE(UR), UR SCRIPT, ETC.",
            ),
            "unity_send_trigger": source_span(
                workspace,
                unity_repository,
                observed_unity_revision,
                unity_ui_path,
                "public void ExecuteTrajectoryButtonMethod()",
                "PublishToTopic(mqttTrajectoryManager.compasXRTopics.publishers.sendTrajectoryTopic",
            ),
            "unity_send_schema": source_span(
                workspace,
                unity_repository,
                observed_unity_revision,
                unity_messages_path,
                "public class SendTrajectory",
                "return new SendTrajectory(elementID, robotName, trajectory, header);",
            ),
        },
        "executor_classification": {
            "case": "C",
            "label": "Framework delegates final robot execution to custom integration",
            "framework_exact_binding_guarantee": "MISSING AT PUBLIC HANDOFF",
            "public_official_or_representative_executable_executor": "NOT FOUND",
            "paper_reported_physical_integration": (
                "CAA papers report project-specific ROS/MoveIt plus UR RTDE integration, "
                "but publish no inspectable executor artifact or exact-binding logic"
            ),
            "ta_to_tb_robot_input_test": "NOT RUN",
            "reason": (
                "The official component/sample terminates at a SendTrajectory subscriber, "
                "exposes only element ID and robot name, and leaves robot control as a placeholder."
            ),
            "physical_execution": "UNCONFIRMED",
            "research_weight": "SECONDARY EVIDENCE ONLY",
        },
        "safe_reference_integration_requirements": [
            "canonical trajectory digest and immutable version",
            "binding among element ID, robot ID, trajectory content, and transaction ID",
            "authenticated distinct approvers and approval quorum",
            "authorization epoch, timeout, and replay rejection",
            "final comparison at the controller or robot-action handoff",
        ],
        "external_official_sources_for_report": [
            "https://compas.dev/compas_xr/latest/userguide.html",
            "https://doi.org/10.1007/s41693-024-00138-6",
            "https://doi.org/10.1007/s41693-025-00158-w",
            "https://github.com/compas-dev/compas_xr",
        ],
    }

    required = [
        observed_compas_revision == COMPAS_XR_REVISION,
        observed_unity_revision == COMPAS_UNITY_REVISION,
        official_examples
        == [
            "docs/examples/scripts/ex1_assembly_definition_and_firebaseupload.ghx",
            "docs/examples/scripts/ex2_robotic_trajectory_visualization_example.ghx",
        ],
        packaged_outputs == ["execute_element_id", "execution_robot"],
        results["packaged_execution_component"]["subscribes_to_send_trajectory"],
        results["packaged_execution_component"]["returns_only_element_and_robot"],
        not results["packaged_execution_component"]["reads_trajectory_for_output"],
        not results["packaged_execution_component"]["approval_or_digest_check"],
        ghx_audit["execution_service_present"],
        ghx_audit["execution_service_outputs"]
        == ["execute_element_id", "a"],
        not ghx_audit["trajectory_output_present"],
        ghx_audit["embedded_component_returns_only_element_and_robot"],
        ghx_audit["project_specific_control_placeholder"],
        not ghx_audit["implemented_robot_control_api_tokens"],
        results["documentation_boundary"]["requires_additional_cad_input_for_execution"],
        runtime_schema.get("available") is True,
        runtime_schema.get("digests_differ") is True,
        runtime_schema.get("different_content_same_trajectory_id") is True,
        runtime_schema.get("approval_binding_fields") == [],
    ]
    results["probe_pass"] = all(required)
    results["verdict"] = "PASS_CASE_C" if results["probe_pass"] else "FAIL_AUDIT_ASSERTION"
    print("COMPAS_EXECUTOR_JSON_BEGIN")
    print(json.dumps(results, indent=2, sort_keys=True))
    print("COMPAS_EXECUTOR_JSON_END")
    return 0 if results["probe_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
