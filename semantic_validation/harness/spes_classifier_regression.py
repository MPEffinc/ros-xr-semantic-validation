#!/usr/bin/env python3
"""Regression checks for the Quest recovery classifier and trial isolation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from reanalyze_spes_hw import DEFAULT_RUN, analyze


VALIDATION_ROOT = Path(__file__).resolve().parents[1]
OPERATOR = VALIDATION_ROOT / "instrumentation/quest-operator.js"
SELFTEST = VALIDATION_ROOT / "harness/spes_quest_operator_selftest.mjs"


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def render_report(result: dict[str, Any], output_dir: Path) -> str:
    rows = []
    for trial in result["actual_raw_trials"]:
        rows.append(
            f"| {trial['valid_trial_number']} | {trial['pre_loss_jump_warning_count']} | "
            f"{trial['loss_window_jump_warning_count']} | {trial['recovery_classification']} | "
            f"{'PASS' if trial['matches_expected'] else 'FAIL'} |"
        )
    return "\n".join([
        "# Spes Classifier Regression",
        "",
        "## Result",
        "",
        f"**{result['status']}**",
        "",
        "Recovery jump evidence is now counted from semantic loss detection through recovery completion. "
        "A reject observed while preparing/baselining a trial cannot set its recovery label.",
        "",
        "## Actual Quest raw-log regression",
        "",
        "| Valid T1 | Pre-loss jump/reject | Loss-window jump/reject | Derived recovery | Result |",
        "| ---: | ---: | ---: | --- | --- |",
        *rows,
        "",
        "The actual first valid trial contains one pre-loss jump/reject but no loss-window jump; it is "
        "therefore `RECOVERY_CONTINUOUS`. Trials 2–5 retain their raw-evidence "
        "`RECOVERY_JUMP_REJECT_THEN_REANCHOR` labels.",
        "",
        "## Valid/invalid and session isolation",
        "",
        f"- Valid T1 count: `{result['actual_valid_trial_count']}`.",
        f"- Excluded `INVALID_MOVE_RELEASED`: `{result['invalid_move_released_count']}`.",
        f"- Raw `INVALID_SESSION_FOCUS`: `{result['raw_focus_invalid_count']}`; the synthetic focus-invalid "
        f"path exclusion test is `{result['synthetic']['invalid_focus_excluded']}`.",
        f"- Production connection generation: `{result['session_partition']['production_server_connection_generation']}`; "
        f"prior-generation overlap: `{result['session_partition']['concurrent_prior_production_client']}`.",
        f"- Server/control correlation offset min/max: "
        f"`{result['session_partition']['server_minus_control_index_offset_min']}/"
        f"{result['session_partition']['server_minus_control_index_offset_max']}`.",
        "",
        "## Synthetic boundary regression",
        "",
        f"- Pre-loss reject excluded: `{result['synthetic']['pre_loss_jump_reject_excluded']}`.",
        f"- Post-loss reject retained: `{result['synthetic']['post_loss_jump_reject_included']}`.",
        f"- Move-release invalid attempt excluded: `{result['synthetic']['invalid_move_excluded']}`.",
        f"- Focus-invalid attempt excluded: `{result['synthetic']['invalid_focus_excluded']}`.",
        f"- Operator selftest: `{result['synthetic']['result']}`.",
        "",
        "## Artifacts",
        "",
        f"- Operator SHA-256: `{result['operator_sha256']}`",
        f"- Machine-readable result: `{output_dir / 'result.json'}`",
        f"- Event summary: `{output_dir / 'summary.jsonl'}`",
        "",
        "## Evidence boundary",
        "",
        "The recovery labels are reconstructed from one actual Quest 3 run plus deterministic classifier tests. "
        "They do not establish population rates or robot actuation.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path, default=DEFAULT_RUN / "experiment.jsonl")
    parser.add_argument("--server", type=Path, default=DEFAULT_RUN / "server.jsonl")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise SystemExit(f"refusing to overwrite existing output directory: {output_dir}")
    output_dir.mkdir(parents=True)

    raw = analyze(args.experiment.resolve(), args.server.resolve())
    completed = subprocess.run(
        ["node", str(SELFTEST)],
        check=False,
        capture_output=True,
        text=True,
    )
    synthetic = json.loads(completed.stdout.strip().splitlines()[-1]) if completed.stdout.strip() else {}
    expected_recovery = [
        "RECOVERY_CONTINUOUS",
        "RECOVERY_JUMP_REJECT_THEN_REANCHOR",
        "RECOVERY_JUMP_REJECT_THEN_REANCHOR",
        "RECOVERY_JUMP_REJECT_THEN_REANCHOR",
        "RECOVERY_JUMP_REJECT_THEN_REANCHOR",
    ]
    trials = []
    for trial, expected in zip(raw["valid_t1_trials"], expected_recovery, strict=True):
        trials.append({
            "valid_trial_number": trial["valid_trial_number"],
            "pre_loss_jump_warning_count": trial["pre_loss_jump_warning_count"],
            "pre_loss_callback_reject_count": trial["pre_loss_callback_reject_count"],
            "loss_window_jump_warning_count": trial["jump_warning_count"],
            "loss_window_callback_reject_count": trial["callback_rejects_loss_to_complete"],
            "recovery_classification": trial["raw_recovery_classification"],
            "expected": expected,
            "matches_expected": trial["raw_recovery_classification"] == expected,
        })

    source = OPERATOR.read_text(encoding="utf-8")
    source_boundary_ok = (
        "loss_jump_reject_count_start" in source
        and re.search(r"(?m)^\s*jump_reject_count_start:\s*", source) is None
    )
    checks = {
        "operator_selftest": completed.returncode == 0 and synthetic.get("result") == "PASS",
        "source_loss_boundary": source_boundary_ok,
        "five_valid_trials": len(trials) == 5,
        "actual_recovery_labels": all(trial["matches_expected"] for trial in trials),
        "actual_continuation_labels": all(
            trial["classification"] == "HW_EMULATED_CONTINUES"
            for trial in raw["valid_t1_trials"]
        ),
        "invalid_move_excluded": raw["excluded_attempts"]["t1_invalid_move_released"] == 1,
        "previous_generation_excluded": not raw["session_partition"]["concurrent_prior_production_client"],
        "constant_packet_server_offset": (
            raw["session_partition"]["server_minus_control_index_offset_min"]
            == raw["session_partition"]["server_minus_control_index_offset_max"]
        ),
        "synthetic_focus_invalid_excluded": synthetic.get("invalid_focus_excluded") is True,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    result = {
        "schema": "spes-classifier-regression-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "checks": checks,
        "operator_sha256": hashlib.sha256(OPERATOR.read_bytes()).hexdigest(),
        "actual_valid_trial_count": len(trials),
        "invalid_move_released_count": raw["excluded_attempts"]["t1_invalid_move_released"],
        "raw_focus_invalid_count": raw["excluded_attempts"]["invalid_session_focus"],
        "session_partition": raw["session_partition"],
        "actual_raw_trials": trials,
        "synthetic": synthetic,
        "selftest_stderr": completed.stderr,
    }
    write_json(output_dir / "result.json", result)
    write_jsonl(output_dir / "summary.jsonl", [
        {"event": "classifier_regression", "status": status, "checks": checks},
        *({"event": "actual_trial", **trial} for trial in trials),
    ])
    if args.report:
        args.report.write_text(render_report(result, output_dir), encoding="utf-8")
    print(json.dumps({"event": "classifier_regression", "status": status, "checks": checks}, sort_keys=True))
    print(f"RESULT_ROOT={output_dir}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
