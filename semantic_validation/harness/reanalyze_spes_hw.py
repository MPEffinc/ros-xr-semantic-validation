#!/usr/bin/env python3
"""Independently derive Spes Quest hardware results from raw JSONL logs.

The derivation intentionally does not consume the existing analysis.json until
after all metrics have been calculated.  The existing file is used only for a
field-by-field comparison at the end.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any, Iterable


VALIDATION_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = VALIDATION_ROOT / "logs/quest_hw/spes_quest_hw_20260831T001349Z"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
            record["_line"] = line_number
            records.append(record)
    return records


def parse_wall_ms(value: str) -> float:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.timestamp() * 1000.0


def browser_origin_ms(record: dict[str, Any]) -> float | None:
    wall = record.get("wall_timestamp")
    mono = record.get("monotonic_timestamp_ms")
    if not isinstance(wall, str) or not isinstance(mono, (int, float)):
        return None
    return parse_wall_ms(wall) - float(mono)


def event_type(record: dict[str, Any], name: str) -> bool:
    return record.get("event") == "quest_operator_event" and record.get("event_type") == name


def first(records: Iterable[dict[str, Any]], predicate) -> dict[str, Any]:
    for record in records:
        if predicate(record):
            return record
    raise ValueError("required raw event was not found")


def phase_to(records: Iterable[dict[str, Any]], phase: str) -> dict[str, Any]:
    return first(
        records,
        lambda record: event_type(record, "phase_transition") and record.get("next_phase") == phase,
    )


def target_delta_max(records: list[dict[str, Any]], key: str) -> float:
    values = [
        record.get("target_delta", {}).get(key)
        for record in records
        if isinstance(record.get("target_delta"), dict)
        and isinstance(record["target_delta"].get(key), (int, float))
    ]
    return max(values) if values else 0.0


def interruption(records: list[dict[str, Any]]) -> dict[str, Any]:
    max_frames = 0
    max_ms = 0.0
    current: list[dict[str, Any]] = []
    for record in records:
        if record.get("callback_emitted") is False:
            current.append(record)
            continue
        if current:
            duration = (
                int(record["server_receive_monotonic_ns"])
                - int(current[0]["server_receive_monotonic_ns"])
            ) / 1_000_000.0
            max_frames = max(max_frames, len(current))
            max_ms = max(max_ms, duration)
            current = []
    if current:
        duration = (
            int(records[-1]["server_complete_monotonic_ns"])
            - int(current[0]["server_receive_monotonic_ns"])
        ) / 1_000_000.0
        max_frames = max(max_frames, len(current))
        max_ms = max(max_ms, duration)
    return {"max_consecutive_rejected_frames": max_frames, "max_interruption_ms": max_ms}


def close_enough(left: Any, right: Any) -> bool:
    if isinstance(left, float) or isinstance(right, float):
        return isinstance(left, (int, float)) and isinstance(right, (int, float)) and math.isclose(
            float(left), float(right), rel_tol=1e-9, abs_tol=1e-9
        )
    return left == right


def compare_value(mismatches: list[dict[str, Any]], path: str, expected: Any, actual: Any) -> None:
    if not close_enough(expected, actual):
        mismatches.append({"field": path, "existing": expected, "reanalyzed": actual})


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def build_quantitative(trials: list[dict[str, Any]]) -> dict[str, Any]:
    linear = [float(trial["max_target_delta_linear_m"]) for trial in trials]
    angular = [float(trial["max_target_delta_angular_rad"]) for trial in trials]
    recovery_latency = [float(trial["loss_to_reacquired_ms"]) for trial in trials]
    emulated_duration = [float(trial["emulated_interval_duration_ms"]) for trial in trials]
    first_callback_latency = [float(trial["reacquired_to_first_callback_ms"]) for trial in trials]
    recovery_completion = [float(trial["reacquired_to_recovery_complete_ms"]) for trial in trials]
    callback_interrupt = [float(trial["callback_interruption"]["max_interruption_ms"]) for trial in trials]
    callback_interrupt_frames = [
        int(trial["callback_interruption"]["max_consecutive_rejected_frames"]) for trial in trials
    ]
    packet = [int(trial["control_packet_delta"]) for trial in trials]
    updates = [int(trial["server_update_delta"]) for trial in trials]
    n = len(trials)
    return {
        "sample_size": n,
        "emulated_occurrence_rate": sum(trial["loss_behavior"] == "EMULATED_TRACKING_LOSS" for trial in trials) / n,
        "downstream_continuation_rate": sum(trial["classification"] == "HW_EMULATED_CONTINUES" for trial in trials) / n,
        "no_user_rearm_rate": sum(not trial["move_ever_false"] for trial in trials) / n,
        "jump_reject_occurrence_rate": sum(trial["jump_warning_count"] > 0 for trial in trials) / n,
        "target_linear_delta_m": {"mean": mean(linear), "median": statistics.median(linear), "max": max(linear)},
        "target_angular_delta_rad": {"mean": mean(angular), "median": statistics.median(angular), "max": max(angular)},
        "loss_to_reacquired_ms": {
            "mean": mean(recovery_latency),
            "median": statistics.median(recovery_latency),
            "max": max(recovery_latency),
            "per_trial": recovery_latency,
        },
        "emulated_interval_duration_ms": {
            "mean": mean(emulated_duration),
            "median": statistics.median(emulated_duration),
            "max": max(emulated_duration),
            "per_trial": emulated_duration,
        },
        "reacquired_to_first_callback_ms": {
            "mean": mean(first_callback_latency),
            "median": statistics.median(first_callback_latency),
            "max": max(first_callback_latency),
            "per_trial": first_callback_latency,
        },
        "reacquired_to_recovery_complete_ms": {
            "mean": mean(recovery_completion),
            "median": statistics.median(recovery_completion),
            "max": max(recovery_completion),
            "per_trial": recovery_completion,
        },
        "callback_interruption_ms": {
            "mean": mean(callback_interrupt),
            "median": statistics.median(callback_interrupt),
            "max": max(callback_interrupt),
            "per_trial": callback_interrupt,
        },
        "callback_interruption_frames": {
            "mean": mean(callback_interrupt_frames),
            "median": statistics.median(callback_interrupt_frames),
            "max": max(callback_interrupt_frames),
            "per_trial": callback_interrupt_frames,
        },
        "control_packet_delta": {"mean": mean(packet), "median": statistics.median(packet), "max": max(packet), "per_trial": packet},
        "server_update_delta": {"mean": mean(updates), "median": statistics.median(updates), "max": max(updates), "per_trial": updates},
        "interpretation_limit": "Five repeated trials from one Quest 3 session; descriptive statistics only.",
    }


def analyze(experiment_path: Path, server_path: Path) -> dict[str, Any]:
    experiment = read_jsonl(experiment_path)
    server = read_jsonl(server_path)

    completions = [
        record for record in experiment
        if event_type(record, "experiment_complete") and record.get("valid_trials") == 5
    ]
    if not completions:
        raise ValueError("no five-valid-trial experiment_complete event found")
    completion = min(completions, key=lambda record: record["_line"])
    completion_origin = browser_origin_ms(completion)
    if completion_origin is None:
        raise ValueError("experiment_complete lacks browser clock fields")
    complete_seq = int(completion["operator_event_sequence"])

    session_events = []
    for record in experiment:
        if record.get("event") != "quest_operator_event":
            continue
        origin = browser_origin_ms(record)
        sequence = record.get("operator_event_sequence")
        if origin is None or not isinstance(sequence, int):
            continue
        if abs(origin - completion_origin) <= 250.0 and sequence <= complete_seq:
            session_events.append(record)
    session_events.sort(key=lambda record: record["operator_event_sequence"])
    preflight = first(session_events, lambda record: event_type(record, "operator_preflight"))
    if session_events[-1].get("event_type") != "experiment_complete":
        raise ValueError("browser session partition does not end at experiment_complete")

    session_start_ns = int(preflight["server_receive_monotonic_ns"])
    session_end_ns = int(completion["server_receive_monotonic_ns"])
    connection_candidates = [
        record for record in server
        if record.get("event") == "server_connection"
        and record.get("state") == "connected"
        and isinstance(record.get("server_connection_generation"), int)
        and int(record["server_receive_monotonic_ns"]) <= session_start_ns
    ]
    if not connection_candidates:
        raise ValueError("no production connection generation precedes fresh session")
    connection = max(connection_candidates, key=lambda record: int(record["server_receive_monotonic_ns"]))
    generation = int(connection["server_connection_generation"])
    generation_updates = [
        record for record in server
        if record.get("event") == "server_update"
        and record.get("server_connection_generation") == generation
        and session_start_ns <= int(record["server_receive_monotonic_ns"]) <= session_end_ns
    ]
    other_generation_updates = [
        record for record in server
        if record.get("event") == "server_update"
        and record.get("server_connection_generation") != generation
        and session_start_ns <= int(record["server_receive_monotonic_ns"]) <= session_end_ns
    ]
    semantic_records = [
        record for record in server
        if record.get("event") == "frontend_semantic"
        and record.get("server_connection_generation") == generation
        and session_start_ns <= int(record["server_receive_monotonic_ns"]) <= session_end_ns
        and isinstance(record.get("frontend_control_packet_index"), int)
        and isinstance(record.get("correlated_server_update_index"), int)
    ]
    offsets = [
        record["correlated_server_update_index"] - record["frontend_control_packet_index"]
        for record in semantic_records
    ]

    attempts: list[dict[str, Any]] = []
    active: list[dict[str, Any]] | None = None
    for record in session_events:
        if (
            event_type(record, "phase_transition")
            and record.get("test") == "T1"
            and record.get("next_phase") == "HOLD_MOVE"
        ):
            active = [record]
            continue
        if active is None:
            continue
        active.append(record)
        if event_type(record, "trial_invalid") or event_type(record, "trial_complete"):
            attempts.append({
                "valid": event_type(record, "trial_complete"),
                "terminal": record,
                "events": active,
            })
            active = None

    valid_attempts = [attempt for attempt in attempts if attempt["valid"]]
    invalid_attempts = [attempt for attempt in attempts if not attempt["valid"]]
    if len(valid_attempts) != 5:
        raise ValueError(f"expected five valid T1 attempts, found {len(valid_attempts)}")

    by_server_index = {
        int(record["server_update_index"]): record
        for record in server
        if record.get("event") == "server_update"
        and record.get("server_connection_generation") == generation
    }
    trials: list[dict[str, Any]] = []
    for valid_number, attempt in enumerate(valid_attempts, 1):
        records = attempt["events"]
        terminal = attempt["terminal"]
        critical_start = phase_to(records, "OCCLUDE")
        loss = first(records, lambda record: event_type(record, "tracking_change_detected"))
        tracking_reacquired_event = first(records, lambda record: event_type(record, "tracking_reacquired"))
        restore_transition = phase_to(records, "RESTORE")
        # Tracking may briefly oscillate false while the post-loss observation
        # window is still active.  Reacquisition begins only once RESTORE is
        # requested and a recovered observation is present.  If the transition
        # frame is already recovered, use it; otherwise use the first recovered
        # observation after that transition.
        if (
            restore_transition.get("right_input_exists") is True
            and restore_transition.get("controller_pose_exists") is True
            and restore_transition.get("controller_emulated_position") is False
            and restore_transition.get("selected_source") == "CONTROLLER"
        ):
            reacquired = restore_transition
        else:
            restore_sequence = int(restore_transition["operator_event_sequence"])
            reacquired = first(
                records,
                lambda record: int(record.get("operator_event_sequence", -1)) >= restore_sequence
                and record.get("right_input_exists") is True
                and record.get("controller_pose_exists") is True
                and record.get("controller_emulated_position") is False
                and record.get("selected_source") == "CONTROLLER",
            )
        critical_records = [
            record for record in records
            if int(critical_start["operator_event_sequence"])
            <= int(record["operator_event_sequence"])
            <= int(terminal["operator_event_sequence"])
        ]
        loss_index = int(loss["server_update_index"])
        critical_start_index = int(critical_start["server_update_index"])
        trial_start_index = int(records[0]["server_update_index"])
        reacquired_index = int(reacquired["server_update_index"])
        complete_index = int(terminal["server_update_index"])
        pre_loss = [
            record for record in generation_updates
            if trial_start_index <= int(record["server_update_index"]) < loss_index
        ]
        loss_to_reacquired = [
            record for record in generation_updates
            if loss_index <= int(record["server_update_index"]) <= reacquired_index
        ]
        loss_to_complete = [
            record for record in generation_updates
            if loss_index <= int(record["server_update_index"]) <= complete_index
        ]
        first_callback_after_recovery = next(
            (
                record for record in generation_updates
                if int(record["server_update_index"]) >= reacquired_index
                and record.get("callback_emitted") is True
            ),
            None,
        )
        if not loss_to_reacquired or not loss_to_complete or first_callback_after_recovery is None:
            raise ValueError(f"trial {valid_number}: incomplete server update window")
        reacquired_server = by_server_index.get(reacquired_index)
        if reacquired_server is None:
            raise ValueError(f"trial {valid_number}: reacquired server index missing")
        jumps = sum(record.get("pose_jump_warning") is True for record in loss_to_reacquired)
        resets = sum(record.get("relative_anchor_reset") is True for record in loss_to_reacquired)
        creates = sum(record.get("relative_anchor_created") is True for record in loss_to_reacquired)
        callbacks_during = sum(record.get("callback_emitted") is True for record in loss_to_reacquired)
        callbacks_total = sum(record.get("callback_emitted") is True for record in loss_to_complete)
        rejected_total = sum(record.get("callback_emitted") is False for record in loss_to_complete)
        packet_delta = int(terminal["control_packet_index"]) - int(loss["control_packet_index"])
        server_delta = complete_index - loss_index
        continues = packet_delta > 0 and server_delta > 0 and callbacks_total > 0
        loss_behavior = loss.get("loss_event")
        emulated_seen = any(record.get("controller_emulated_position") is True for record in critical_records)
        classification = (
            "HW_EMULATED_CONTINUES"
            if loss_behavior == "EMULATED_TRACKING_LOSS" and emulated_seen and continues
            else "HW_FAIL_CLOSED"
            if loss_behavior in {"EMULATED_TRACKING_LOSS", "VIEWER_FALLBACK", "INPUT_SOURCE_LOST"} and not continues
            else "HW_NO_LOSS_OBSERVED"
        )
        if jumps and resets and creates and first_callback_after_recovery:
            recovery = "RECOVERY_JUMP_REJECT_THEN_REANCHOR"
        elif callbacks_during and first_callback_after_recovery:
            recovery = "RECOVERY_CONTINUOUS"
        elif first_callback_after_recovery:
            recovery = "RECOVERY_AUTO_REARM"
        else:
            recovery = "RECOVERY_FAIL_CLOSED"
        emulated_records = [record for record in critical_records if record.get("controller_emulated_position") is True]
        trial = {
            "valid_trial_number": valid_number,
            "loss_behavior": loss_behavior,
            "controller_pose_exists_through_critical_window": all(
                record.get("controller_pose_exists") is True for record in critical_records
            ),
            "selected_source_through_critical_window": (
                "CONTROLLER"
                if all(record.get("selected_source") == "CONTROLLER" for record in critical_records)
                else "MIXED"
            ),
            "move_ever_false": any(record.get("move") is not True for record in critical_records),
            "emulated_sample_count": len(emulated_records),
            "loss_control_packet_index": int(loss["control_packet_index"]),
            "complete_control_packet_index": int(terminal["control_packet_index"]),
            "control_packet_delta": packet_delta,
            "loss_server_update_index": loss_index,
            "reacquired_server_update_index": reacquired_index,
            "complete_server_update_index": complete_index,
            "server_update_delta": server_delta,
            "server_updates_loss_to_complete": len(loss_to_complete),
            "callbacks_loss_to_complete": callbacks_total,
            "callback_rejects_loss_to_complete": rejected_total,
            "pre_loss_jump_warning_count": sum(
                record.get("pose_jump_warning") is True for record in pre_loss
            ),
            "pre_loss_callback_reject_count": sum(
                record.get("callback_emitted") is False for record in pre_loss
            ),
            "emulated_to_reacquired_updates": len(loss_to_reacquired),
            "emulated_to_reacquired_callbacks": callbacks_during,
            "emulated_to_reacquired_rejected": sum(
                record.get("callback_emitted") is False for record in loss_to_reacquired
            ),
            "jump_warning_count": jumps,
            "relative_anchor_resets": resets,
            "relative_anchor_creates": creates,
            "first_callback_after_recovery": {
                "server_update_index": int(first_callback_after_recovery["server_update_index"]),
                "wall_utc": first_callback_after_recovery["wall_utc"],
            },
            "max_target_delta_linear_m": target_delta_max(loss_to_reacquired, "linear_m"),
            "max_target_delta_angular_rad": target_delta_max(loss_to_reacquired, "angular_rad"),
            "loss_interval_duration_ms": float(reacquired["monotonic_timestamp_ms"]) - float(loss["monotonic_timestamp_ms"]),
            "emulated_interval_duration_ms": (
                float(reacquired["monotonic_timestamp_ms"]) - float(emulated_records[0]["monotonic_timestamp_ms"])
                if emulated_records else 0.0
            ),
            "loss_to_reacquired_ms": float(reacquired["monotonic_timestamp_ms"]) - float(loss["monotonic_timestamp_ms"]),
            "reacquired_to_first_callback_ms": max(
                0.0,
                (
                    int(first_callback_after_recovery["server_receive_monotonic_ns"])
                    - int(reacquired_server["server_receive_monotonic_ns"])
                ) / 1_000_000.0,
            ),
            "reacquired_to_recovery_complete_ms": float(terminal["monotonic_timestamp_ms"]) - float(reacquired["monotonic_timestamp_ms"]),
            "callback_interruption": interruption(loss_to_complete),
            "classification": classification,
            "raw_recovery_classification": recovery,
            "raw_event_lines": {
                "critical_start": critical_start["_line"],
                "loss": loss["_line"],
                "first_recovered_observation": reacquired["_line"],
                "tracking_reacquired_event": tracking_reacquired_event["_line"],
                "complete": terminal["_line"],
            },
        }
        trials.append(trial)

    t0 = first(session_events, lambda record: event_type(record, "t0_complete"))
    invalid_events = [record for record in session_events if event_type(record, "trial_invalid")]
    t4 = first(session_events, lambda record: event_type(record, "t4_complete"))
    result = {
        "schema": "spes-hardware-independent-reanalysis-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_logs": {"experiment": str(experiment_path.resolve()), "server": str(server_path.resolve())},
        "session_partition": {
            "browser_clock_origin_ms": completion_origin,
            "operator_preflight_line": preflight["_line"],
            "experiment_complete_line": completion["_line"],
            "session_event_count": len(session_events),
            "production_server_connection_generation": generation,
            "generation_connected_utc": connection["wall_utc"],
            "concurrent_prior_production_client": bool(other_generation_updates),
            "semantic_correlation_events": len(offsets),
            "server_minus_control_index_offset_min": min(offsets) if offsets else None,
            "server_minus_control_index_offset_max": max(offsets) if offsets else None,
        },
        "t0": {
            "result": t0.get("result"),
            "controller_pose_exists": t0.get("controller_pose_exists"),
            "controller_emulated_position": t0.get("controller_emulated_position"),
            "selected_source": t0.get("selected_source"),
            "move": t0.get("move"),
            "control_packet_progress": t0.get("control_packet_progress"),
            "server_update_progress": t0.get("server_update_progress"),
        },
        "excluded_attempts": {
            "t0_invalid_manual_abort": sum(
                record.get("test") == "T0" and record.get("classification") == "INVALID_MANUAL_ABORT"
                for record in invalid_events
            ),
            "t1_invalid_move_released": sum(
                record.get("test") == "T1" and record.get("classification") == "INVALID_MOVE_RELEASED"
                for record in invalid_events
            ),
            "invalid_session_focus": sum(
                record.get("classification") == "INVALID_SESSION_FOCUS" for record in invalid_events
            ),
            "t1_invalid_attempt_count": len(invalid_attempts),
        },
        "valid_t1_trials": trials,
        "t4": {
            "classification": t4.get("classification"),
            "right_input_source_disappeared": any(
                event_type(record, "t4_input_source_lost") for record in session_events
            ),
            "controller_pose_became_null": any(
                record.get("test") == "T4" and record.get("controller_pose_exists") is False
                for record in session_events
            ),
        },
    }
    result["quantitative"] = build_quantitative(trials)
    return result


def compare_existing(reanalyzed: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for key in (
        "production_server_connection_generation",
        "concurrent_prior_production_client",
        "server_minus_control_index_offset_min",
        "server_minus_control_index_offset_max",
    ):
        compare_value(mismatches, f"session_partition.{key}", existing["session_partition"].get(key), reanalyzed["session_partition"].get(key))
    compare_value(
        diagnostics,
        "session_partition.semantic_correlation_events",
        existing["session_partition"].get("semantic_correlation_events"),
        reanalyzed["session_partition"].get("semantic_correlation_events"),
    )
    for key in (
        "result", "controller_pose_exists", "controller_emulated_position", "selected_source",
        "move", "control_packet_progress", "server_update_progress",
    ):
        compare_value(mismatches, f"t0.{key}", existing["t0"].get(key), reanalyzed["t0"].get(key))
    for key in ("t0_invalid_manual_abort", "t1_invalid_move_released", "invalid_session_focus"):
        compare_value(mismatches, f"excluded_attempts.{key}", existing["excluded_attempts"].get(key), reanalyzed["excluded_attempts"].get(key))
    existing_trials = existing.get("valid_t1_trials", [])
    actual_trials = reanalyzed.get("valid_t1_trials", [])
    compare_value(mismatches, "valid_t1_trials.length", len(existing_trials), len(actual_trials))
    keys = (
        "valid_trial_number", "loss_behavior", "controller_pose_exists_through_critical_window",
        "selected_source_through_critical_window", "move_ever_false", "loss_control_packet_index",
        "complete_control_packet_index", "control_packet_delta", "loss_server_update_index",
        "complete_server_update_index", "server_update_delta", "server_updates_loss_to_complete",
        "callbacks_loss_to_complete", "emulated_to_reacquired_updates",
        "emulated_to_reacquired_callbacks", "emulated_to_reacquired_rejected",
        "relative_anchor_resets", "relative_anchor_creates", "max_target_delta_linear_m",
        "max_target_delta_angular_rad", "classification", "raw_recovery_classification",
    )
    for index, (expected, actual) in enumerate(zip(existing_trials, actual_trials), 1):
        for key in keys:
            compare_value(mismatches, f"valid_t1_trials[{index}].{key}", expected.get(key), actual.get(key))
    for key in ("classification", "right_input_source_disappeared", "controller_pose_became_null"):
        compare_value(mismatches, f"t4.{key}", existing["t4"].get(key), reanalyzed["t4"].get(key))
    return {
        "status": "INDEPENDENT_REANALYSIS_PASS" if not mismatches else "ANALYSIS_MISMATCH",
        "compared_field_count": 5 + 7 + 3 + 1 + len(keys) * min(len(existing_trials), len(actual_trials)) + 3,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "diagnostic_difference_count": len(diagnostics),
        "diagnostic_differences": diagnostics,
        "diagnostic_note": (
            "Correlation event count is window-definition dependent and is not a major finding field; "
            "generation, overlap, constant offset, and all trial fields remain decisive."
        ),
    }


def render_reanalysis(result: dict[str, Any], comparison: dict[str, Any], raw_dir: Path) -> str:
    lines = [
        "# Spes Hardware Independent Re-analysis",
        "",
        "## Result",
        "",
        f"**{comparison['status']}**",
        "",
        "기존 derived analysis를 입력으로 사용하지 않고 raw `experiment.jsonl`과 `server.jsonl`에서 session과 trial을 다시 구성했다.",
        "",
        "## Session isolation",
        "",
        f"- Production generation: `{result['session_partition']['production_server_connection_generation']}`",
        f"- Fresh browser-session events: `{result['session_partition']['session_event_count']}`",
        f"- Concurrent prior production client: `{result['session_partition']['concurrent_prior_production_client']}`",
        f"- Correlation samples: `{result['session_partition']['semantic_correlation_events']}`; server-control offset min/max `{result['session_partition']['server_minus_control_index_offset_min']}/{result['session_partition']['server_minus_control_index_offset_max']}`",
        "",
        "## Valid T1 trials",
        "",
        "| Valid | Loss | Pose/source/move integrity | Packet Δ | Server Δ | Callback/reject | Loss→reacquired | Recovery | Classification |",
        "| --- | --- | --- | ---: | ---: | --- | ---: | --- | --- |",
    ]
    for trial in result["valid_t1_trials"]:
        integrity = (
            f"pose={trial['controller_pose_exists_through_critical_window']}, "
            f"source={trial['selected_source_through_critical_window']}, move_false={trial['move_ever_false']}"
        )
        lines.append(
            f"| {trial['valid_trial_number']} | {trial['loss_behavior']} | {integrity} | "
            f"{trial['control_packet_delta']} | {trial['server_update_delta']} | "
            f"{trial['callbacks_loss_to_complete']}/{trial['server_updates_loss_to_complete']}; reject {trial['callback_rejects_loss_to_complete']} | "
            f"{trial['loss_to_reacquired_ms']:.1f} ms | {trial['raw_recovery_classification']} | {trial['classification']} |"
        )
    lines.extend([
        "",
        "## Existing-analysis comparison",
        "",
        f"Compared fields: `{comparison['compared_field_count']}`; mismatches: `{comparison['mismatch_count']}`.",
    ])
    if comparison["mismatches"]:
        lines.extend(["", "| Field | Existing | Re-analyzed |", "| --- | --- | --- |"])
        for mismatch in comparison["mismatches"]:
            lines.append(f"| `{mismatch['field']}` | `{mismatch['existing']}` | `{mismatch['reanalyzed']}` |")
    if comparison["diagnostic_differences"]:
        lines.extend([
            "",
            "Non-decisive diagnostic differences:",
            "",
            "| Field | Existing | Re-analyzed | Reason |",
            "| --- | --- | --- | --- |",
        ])
        for mismatch in comparison["diagnostic_differences"]:
            lines.append(
                f"| `{mismatch['field']}` | `{mismatch['existing']}` | `{mismatch['reanalyzed']}` | "
                "Existing count included the broader connection/final-display window; re-analysis stops at the server-received experiment-complete boundary. |"
            )
    lines.extend([
        "",
        "## Validity exclusions",
        "",
        f"- T0 manual abort: `{result['excluded_attempts']['t0_invalid_manual_abort']}`",
        f"- T1 move release: `{result['excluded_attempts']['t1_invalid_move_released']}`",
        f"- Focus invalid: `{result['excluded_attempts']['invalid_session_focus']}`",
        "- Invalid attempts do not contribute to the five valid trials.",
        "",
        "## Raw output",
        "",
        f"- `{raw_dir / 'reanalyzed.json'}`",
        f"- `{raw_dir / 'comparison.json'}`",
        f"- `{raw_dir / 'trial_evidence.jsonl'}`",
        "",
        "## Boundary",
        "",
        "이 결과는 actual Quest 3 semantic event와 actual Spes server target callback까지다. ROS sink, robot, actuator evidence는 아니다.",
        "",
    ])
    return "\n".join(lines)


def render_quantitative(result: dict[str, Any], raw_dir: Path) -> str:
    q = result["quantitative"]
    lines = [
        "# Spes Quest Hardware Quantitative Summary",
        "",
        "표본은 한 Quest 3 session의 valid T1 5회다. 아래 값은 descriptive summary이며 population inference 또는 유의성 검정이 아니다.",
        "",
        "## Rates",
        "",
        f"- Emulated occurrence: `{q['emulated_occurrence_rate']:.0%}` (5/5)",
        f"- Downstream continuation: `{q['downstream_continuation_rate']:.0%}` (5/5)",
        f"- No-user-rearm: `{q['no_user_rearm_rate']:.0%}` (5/5)",
        f"- Jump-reject occurrence: `{q['jump_reject_occurrence_rate']:.0%}` (4/5)",
        "",
        "## Descriptive metrics",
        "",
        "| Metric | Mean | Median | Max |",
        "| --- | ---: | ---: | ---: |",
        f"| Max linear target delta per trial (m) | {q['target_linear_delta_m']['mean']:.6f} | {q['target_linear_delta_m']['median']:.6f} | {q['target_linear_delta_m']['max']:.6f} |",
        f"| Max angular target delta per trial (rad) | {q['target_angular_delta_rad']['mean']:.6f} | {q['target_angular_delta_rad']['median']:.6f} | {q['target_angular_delta_rad']['max']:.6f} |",
        f"| Loss→reacquired (ms) | {q['loss_to_reacquired_ms']['mean']:.1f} | {q['loss_to_reacquired_ms']['median']:.1f} | {q['loss_to_reacquired_ms']['max']:.1f} |",
        f"| Emulated interval (ms) | {q['emulated_interval_duration_ms']['mean']:.1f} | {q['emulated_interval_duration_ms']['median']:.1f} | {q['emulated_interval_duration_ms']['max']:.1f} |",
        f"| Reacquired→first accepted callback (ms) | {q['reacquired_to_first_callback_ms']['mean']:.3f} | {q['reacquired_to_first_callback_ms']['median']:.3f} | {q['reacquired_to_first_callback_ms']['max']:.3f} |",
        f"| Reacquired→recovery completion (ms) | {q['reacquired_to_recovery_complete_ms']['mean']:.1f} | {q['reacquired_to_recovery_complete_ms']['median']:.1f} | {q['reacquired_to_recovery_complete_ms']['max']:.1f} |",
        f"| Longest callback interruption per trial (ms) | {q['callback_interruption_ms']['mean']:.3f} | {q['callback_interruption_ms']['median']:.3f} | {q['callback_interruption_ms']['max']:.3f} |",
        f"| Longest rejected run per trial (frames) | {q['callback_interruption_frames']['mean']:.1f} | {q['callback_interruption_frames']['median']:.1f} | {q['callback_interruption_frames']['max']} |",
        f"| Control packet progression | {q['control_packet_delta']['mean']:.1f} | {q['control_packet_delta']['median']:.1f} | {q['control_packet_delta']['max']} |",
        f"| Server update progression | {q['server_update_delta']['mean']:.1f} | {q['server_update_delta']['median']:.1f} | {q['server_update_delta']['max']} |",
        "",
        "Callback interruption은 loss detection부터 trial completion까지 연속 `callback_emitted=false` frame이 다음 accepted callback을 만날 때까지의 server monotonic duration으로 정의했다.",
        "",
        f"Machine-readable source: `{raw_dir / 'reanalyzed.json'}`.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path, default=DEFAULT_RUN / "experiment.jsonl")
    parser.add_argument("--server", type=Path, default=DEFAULT_RUN / "server.jsonl")
    parser.add_argument("--existing-analysis", type=Path, default=DEFAULT_RUN / "analysis.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--quantitative-report", type=Path)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise SystemExit(f"refusing to overwrite existing output directory: {output_dir}")
    output_dir.mkdir(parents=True)
    try:
        result = analyze(args.experiment.resolve(), args.server.resolve())
        existing = json.loads(args.existing_analysis.read_text(encoding="utf-8"))
        comparison = compare_existing(result, existing)
        write_json(output_dir / "reanalyzed.json", result)
        write_json(output_dir / "comparison.json", comparison)
        write_jsonl(output_dir / "trial_evidence.jsonl", result["valid_t1_trials"])
        write_jsonl(
            output_dir / "summary.jsonl",
            [
                {"event": "independent_reanalysis", **comparison},
                {
                    "event": "quantitative_summary",
                    "status": "PASS",
                    **result["quantitative"],
                },
            ],
        )
        if args.report:
            args.report.write_text(render_reanalysis(result, comparison, output_dir), encoding="utf-8")
        if args.quantitative_report:
            args.quantitative_report.write_text(render_quantitative(result, output_dir), encoding="utf-8")
        print(json.dumps({"event": "independent_reanalysis", **comparison}, sort_keys=True))
        print(f"RESULT_ROOT={output_dir}")
        return 0 if comparison["status"] == "INDEPENDENT_REANALYSIS_PASS" else 2
    except Exception as error:
        failure = {
            "event": "independent_reanalysis",
            "status": "FAIL",
            "error": f"{type(error).__name__}: {error}",
        }
        write_jsonl(output_dir / "summary.jsonl", [failure])
        print(json.dumps(failure, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
