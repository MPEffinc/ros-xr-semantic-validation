#!/usr/bin/env python3
"""Create concise XR2Act evidence and negative-control summaries."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def first_json(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("no JSON object found")


def between(text: str, begin: str, end: str) -> str:
    start = text.index(begin) + len(begin)
    finish = text.index(end, start)
    return text[start:finish]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence_dir.resolve()
    compas_path = evidence / "compas_e2e_execution.log"
    horus_path = evidence / "horus_post_handoff.log"
    scope_path = evidence / "bridge_scope_bypass.log"
    negative_path = evidence / "negative_control.log"
    summary_path = evidence / "xr2act_decisive_summary.md"

    compas_text = compas_path.read_text(encoding="utf-8")
    compas_source = first_json(
        between(compas_text, "COMPAS_SOURCE_AUDIT_BEGIN", "COMPAS_SOURCE_AUDIT_END")
    )
    compas_runtime = first_json(
        between(compas_text, "COMPAS_RUNTIME_BEGIN", "COMPAS_RUNTIME_END")
    )
    horus_records = [
        json.loads(line)
        for line in horus_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    horus_summary = next(
        record for record in reversed(horus_records) if record.get("record_type") == "RUN_SUMMARY"
    )
    scope = json.loads(scope_path.read_text(encoding="utf-8"))

    direct = horus_summary["aggregate"].get("direct_result100", {})
    compas_control = compas_runtime["reference_negative_control"]
    negative = {
        "schema": "xr2act-negative-control/v1",
        "compas_reference": {
            "classification": compas_control["classification"],
            "normal_t_a_allowed": compas_control["normal_a"]["allowed"],
            "same_id_t_b_rejected": not compas_control["same_id_t_b"]["allowed"],
            "cross_robot_t_b_rejected": not compas_control["cross_robot_t_b"]["allowed"],
            "stale_epoch_t_b_rejected": not compas_control["stale_epoch_t_b"]["allowed"],
        },
        "horus_direct_exact_uuid": {
            "trials": direct.get("requested"),
            "complete": direct.get("complete"),
            "success": direct.get("direct_exact_cancel_success"),
            "classification": direct.get("classifications"),
        },
        "test_oracle_distinguishes_safe_behavior": (
            compas_control["normal_a"]["allowed"]
            and not compas_control["same_id_t_b"]["allowed"]
            and not compas_control["cross_robot_t_b"]["allowed"]
            and not compas_control["stale_epoch_t_b"]["allowed"]
            and direct.get("direct_exact_cancel_success") == direct.get("requested")
        ),
        "guardrail": (
            "COMPAS reference executor is test-only and not an official COMPAS feature; "
            "direct Nav2 UUID cancel is a protocol negative control, not the proposed defense."
        ),
    }
    negative_path.write_text(json.dumps(negative, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    official_modes = {
        name: item
        for name, item in horus_summary["aggregate"].items()
        if name.startswith("official_")
    }
    official_requested = sum(item["requested"] for item in official_modes.values())
    official_success = sum(item["official_horus_cancel_success"] for item in official_modes.values())
    interference = sum(
        item["classifications"].get("POST_HANDOFF_B_CANCEL_INTERFERENCE_CONFIRMED", 0)
        for item in official_modes.values()
    )
    official_trials = [
        record
        for record in horus_records
        if str(record.get("mode", "")).startswith("official_")
    ]
    cancel_before_result = [
        record
        for record in official_trials
        if record["cancel_ordering"]["sent_before_a_adapter_result_publish"]
    ]
    cancel_after_result = [
        record
        for record in official_trials
        if not record["cancel_ordering"]["sent_before_a_adapter_result_publish"]
    ]
    before_success = sum(
        record["classification"] == "B_OFFICIAL_CANCEL_SUCCEEDED"
        for record in cancel_before_result
    )
    after_success = sum(
        record["classification"] == "B_OFFICIAL_CANCEL_SUCCEEDED"
        for record in cancel_after_result
    )
    exact_rescue = sum(
        record["classification"] == "POST_HANDOFF_B_CANCEL_INTERFERENCE_CONFIRMED"
        and bool((record.get("direct_exact_cancel") or {}).get("success"))
        and (record.get("direct_exact_terminal") or {}).get("status") == 5
        for record in official_trials
    )
    compas_classification = compas_source["executor_classification"]["label"]
    lines = [
        "# XR2Act Decisive Evidence Summary",
        "",
        "## Decision",
        "",
        "- Final item decision: `WEAK / CASE-STUDY ONLY`.",
        f"- Track A: `{compas_classification}`; T_B reached the official handoff but final robot/executor input remains unconfirmed.",
        f"- Track B: official B cancel succeeded `{official_success}/{official_requested}`; post-handoff interference confirmed `{interference}/{official_requested}`.",
        f"- Ordering discriminator: cancel before A-result publication succeeded `{before_success}/{len(cancel_before_result)}`; cancel after publication succeeded `{after_success}/{len(cancel_after_result)}`.",
        f"- Exact-UUID rescue after official-path failure: `{exact_rescue}/{interference}`.",
        f"- Track C: `{scope['final_classification']}`; no synthetic roles or ACL omissions were introduced.",
        f"- Track D: safe-oracle discrimination `{negative['test_oracle_distinguishes_safe_behavior']}`.",
        "",
        "## Track A — COMPAS",
        "",
        f"- Fixed source audit: `{compas_source['verdict']}`.",
        f"- Credential-authenticated local broker: `{compas_runtime['broker_authentication']['enabled']}`.",
        f"- T_A normal handoff: `{compas_runtime['normal_handoff']['trajectory_received']}`.",
        f"- A1/A2 T_B official subscriber acceptance: `{compas_runtime['approval_to_execution_substitution']['T_B_reached_official_send_subscriber']}`.",
        f"- A3 cross-robot official subscriber acceptance: `{compas_runtime['cross_robot_substitution']['accepted_by_official_send_subscriber']}`.",
        f"- A4 stale approval official subscriber acceptance: `{compas_runtime['stale_approval_reuse']['accepted_by_official_send_subscriber']}`.",
        "- Final actuator/executor command: `UNCONFIRMED`; the shipped official example stops at a custom integration boundary.",
        "",
        "## Track B — HORUS",
        "",
        f"- Run ID: `{horus_summary['run_id']}`.",
        f"- Completed: `{horus_summary['trials_complete']}/{horus_summary['trials_requested']}`.",
    ]
    for name, item in horus_summary["aggregate"].items():
        lines.append(
            f"- `{name}`: complete `{item['complete']}/{item['requested']}`, "
            f"official success `{item['official_horus_cancel_success']}`, "
            f"direct exact success `{item['direct_exact_cancel_success']}`, "
            f"outcomes `{json.dumps(item['classifications'], sort_keys=True)}`."
        )
    lines.extend(
        [
            "",
            "## Track C — Authenticated Scope",
            "",
            f"- `{scope['final_classification']}`.",
            f"- Reason: {scope['reason']}",
            "",
            "## Negative Control",
            "",
            f"- COMPAS exact digest/robot/epoch/approver reference rejected all T_B variants: `{negative['compas_reference']}`.",
            f"- Direct exact Nav2 UUID cancellation: `{negative['horus_direct_exact_uuid']}`.",
            "",
            "## Evidence Integrity",
            "",
        ]
    )
    for path in (compas_path, horus_path, scope_path, negative_path):
        lines.append(f"- `{path}` SHA-256 `{sha256(path)}`")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "summary": str(summary_path),
                "negative_control": str(negative_path),
                "official_horus_cancel_success": official_success,
                "official_horus_cancel_requested": official_requested,
                "post_handoff_interference": interference,
                "before_result_official_success": before_success,
                "before_result_trials": len(cancel_before_result),
                "after_result_official_success": after_success,
                "after_result_trials": len(cancel_after_result),
                "exact_uuid_rescue": exact_rescue,
                "scope": scope["final_classification"],
                "negative_control_pass": negative["test_oracle_distinguishes_safe_behavior"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
