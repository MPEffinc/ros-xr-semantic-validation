#!/usr/bin/env python3
"""Audit whether a real authenticated, scope-bound shared ROS bridge exists.

This deliberately refuses to create synthetic Viewer/Operator roles.  It
cross-checks fixed local framework evidence and records why each available
candidate does or does not meet the Track C threat-boundary prerequisites.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contains(path: Path, *markers: str) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    return all(marker in text for marker in markers)


def main() -> int:
    quest_report = WORKSPACE / "XR_BRIDGE_ANALYSIS.md"
    quest_runtime = WORKSPACE / "evidence/quest2ros2_runtime.log"
    quest_identity = WORKSPACE / "evidence/quest2ros2_identity.txt"
    auth_report = WORKSPACE / "AUTHORIZATION_CONTINUITY_RESULTS.md"
    compas_report = WORKSPACE / "DECISIVE_FOLLOWUP_RESULTS.md"

    candidates: list[dict[str, Any]] = [
        {
            "candidate": "Quest2ROS2 plus ros_tcp_communication",
            "fixed_revisions": {
                "Quest2ROS2": "07aaf651",
                "ros_tcp_communication": "5c5f08956d4bc7a045c321214b0bc03c63eb20a7",
            },
            "distinct_credentials_verified": False,
            "different_robot_or_action_scope": False,
            "shared_bridge_ros_authority": True,
            "disqualifier": "fixed source has no client authentication, role, ACL, or client-to-ROS-principal mapping",
            "evidence_level": "CONFIRMED_BY_SOURCE_AND_PRIOR_RUNTIME",
        },
        {
            "candidate": "HORUS multi-operator bridge",
            "fixed_revision": "eca75cbf559f09ff793d8993338b2f1ffed1adfd",
            "distinct_credentials_verified": False,
            "different_robot_or_action_scope": False,
            "shared_bridge_ros_authority": True,
            "disqualifier": "app_id, role, and session_id are client assertions in the tested public path, not authenticated principals",
            "evidence_level": "CONFIRMED_BY_SOURCE_AND_PRIOR_RUNTIME",
        },
        {
            "candidate": "COMPAS XR MQTT workflow",
            "fixed_revision": "b86e6fbbacdc8e84183fc08c846176a1c79304ca",
            "distinct_credentials_verified": False,
            "different_robot_or_action_scope": False,
            "shared_bridge_ros_authority": False,
            "disqualifier": "project topics and message headers do not provide authenticated per-user robot/action scope or a shared ROS enforcement principal",
            "evidence_level": "CONFIRMED_BY_SOURCE",
        },
        {
            "candidate": "RobotWebTools rosbridge plus ROSAuth",
            "official_sources": [
                "https://github.com/RobotWebTools/rosbridge_suite/blob/ros2/ROSBRIDGE_PROTOCOL.md",
                "https://github.com/RobotWebTools/rosbridge_suite/blob/ros2/rosbridge_server/scripts/rosbridge_websocket.py",
                "https://github.com/GT-RAIL/rosauth",
            ],
            "distinct_credentials_possible": True,
            "different_robot_or_action_scope_in_maintained_bridge": False,
            "shared_bridge_ros_authority": True,
            "disqualifier": "ROSAuth authenticates a connection; current rosbridge resource globs are server-wide rather than credential-bound per-client robot scopes",
            "evidence_level": "CONFIRMED_BY_OFFICIAL_PROTOCOL_AND_SOURCE_REVIEW",
            "runtime_candidate_added": False,
        },
    ]

    prior_runtime_checks = {
        "quest_direct_low_sros2_block": contains(
            quest_runtime,
            "Direct Low linear.x=0.440 = SROS2 BLOCK",
            "check_create_datawriter",
        ),
        "quest_shared_bridge_allow": contains(
            quest_runtime,
            "Client A Bridge ALLOW",
            "global publisher 1개와 동일 GID 공유",
        ),
        "quest_no_auth_boundary_documented": contains(
            quest_report,
            "Client 인증, Client별 role/ACL 또는 Client→ROS principal mapping 구현은 발견되지 않았다",
        ),
        "horus_self_asserted_identity_documented": contains(
            auth_report,
            "self-asserted",
            "role",
        ),
        "compas_custom_executor_boundary_documented": contains(
            compas_report,
            "Case C",
            "custom integration",
        ),
    }
    evidence_files = [quest_report, quest_runtime, quest_identity, auth_report, compas_report]
    result = {
        "schema": "xr2act-authenticated-scope-audit/v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "track": "C_AUTHENTICATED_SHARED_BRIDGE_SCOPE_BYPASS",
        "selection_requirements": [
            "different verified credentials for A and B",
            "different explicit robot or action scopes",
            "one shared bridge-side ROS process/enclave",
            "broad downstream ROS authority",
        ],
        "candidates": candidates,
        "prior_runtime_checks": prior_runtime_checks,
        "evidence_hashes": {str(path): sha256(path) for path in evidence_files},
        "real_authenticated_multi_principal_threat_boundary_available": False,
        "attack_runtime_performed": False,
        "reason": (
            "No inspected public XR-ROS/shared-bridge implementation simultaneously provided "
            "verified distinct credentials, credential-bound Robot/Action scopes, and a shared "
            "downstream ROS authority. Creating roles or omitting an ACL would be an artificial testbed."
        ),
        "final_classification": "UNCONFIRMED_REAL_THREAT_BOUNDARY_UNAVAILABLE",
        "security_meaning": "NO_VULNERABILITY_CLAIM",
        "negative_control_note": (
            "Prior SROS2 runtime correctly blocked the low direct ROS principal, but this is not "
            "a substitute for a real upstream authenticated A/B scope boundary."
        ),
    }
    result["probe_pass"] = all(prior_runtime_checks.values()) and not result[
        "real_authenticated_multi_principal_threat_boundary_available"
    ]
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["probe_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
