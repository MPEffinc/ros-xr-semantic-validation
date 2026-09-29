#!/usr/bin/env python3
"""Post-handoff ownership probe for fixed HORUS and actual Nav2.

The probe reuses the already-audited XR/HorusLink/Nav2 harness but measures a
different property: whether B, the current lease holder, can cancel its own
accepted Goal after A's late preemption result has run through the fixed HORUS
Nav2ActionAdapter.  It never creates an ActionServer and never patches HORUS.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import rclpy
from action_msgs.msg import GoalStatus
from action_msgs.srv import CancelGoal
from rclpy.executors import MultiThreadedExecutor

from xr_mock_client import (
    ACTIVE_STATUSES,
    ControlState,
    STATUS_NAMES,
    TERMINAL_STATUSES,
    Nav2Observer,
    TimelineRecorder,
    XRNav2TrialRunner,
    json_safe,
    parse_args as parse_base_args,
)


FIXED_HORUS_REVISION = "eca75cbf559f09ff793d8993338b2f1ffed1adfd"

MODES: dict[str, dict[str, Any]] = {
    "official_accept0": {"anchor": "b_accept", "offset_ms": 0, "path": "horus"},
    "official_accept5": {"anchor": "b_accept", "offset_ms": 5, "path": "horus"},
    "official_result0": {"anchor": "a_result", "offset_ms": 0, "path": "horus"},
    "official_result10": {"anchor": "a_result", "offset_ms": 10, "path": "horus"},
    "official_result50": {"anchor": "a_result", "offset_ms": 50, "path": "horus"},
    "official_result100": {"anchor": "a_result", "offset_ms": 100, "path": "horus"},
    "official_result500": {"anchor": "a_result", "offset_ms": 500, "path": "horus"},
    "direct_result100": {"anchor": "a_result", "offset_ms": 100, "path": "direct_exact"},
}


def parse_cli(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="XR2Act HORUS post-handoff timing matrix")
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--modes", default=",".join(MODES))
    parser.add_argument("--revocation-delay-sec", type=float, default=0.5)
    parser.add_argument("--lease-ttl-ms", type=int, default=1200)
    parser.add_argument("--official-observation-sec", type=float, default=0.75)
    parser.add_argument("--timeline-log", default="/tmp/xr2act_horus_timeline.log")
    parser.add_argument("--output-log", default="/workspace/evidence/horus_post_handoff.log")
    args = parser.parse_args(argv)
    args.modes = [item.strip() for item in args.modes.split(",") if item.strip()]
    unknown = [item for item in args.modes if item not in MODES]
    if unknown:
        parser.error(f"unknown modes: {unknown}")
    if args.trials < 1:
        parser.error("--trials must be >= 1")
    if args.official_observation_sec < 0.25:
        parser.error("--official-observation-sec must be >= 0.25")
    return args


def base_args(cli: argparse.Namespace) -> argparse.Namespace:
    return parse_base_args(
        [
            "--trials", str(cli.trials),
            "--cases", "F5",
            "--revocation-delay-sec", str(cli.revocation_delay_sec),
            "--observation-sec", "1",
            "--lease-ttl-ms", str(cli.lease_ttl_ms),
            "--timeline-log", cli.timeline_log,
            "--revocation-log", "/tmp/xr2act_horus_unused_revocation.log",
            "--handoff-log", "/tmp/xr2act_horus_unused_handoff.log",
            "--summary-md", "/tmp/xr2act_horus_unused_summary.md",
            "--start-x", "-2.0",
            "--start-y", "-0.5",
            "--goal-a-x", "1.5",
            "--goal-a-y", "-0.5",
            "--goal-b-x", "-1.5",
            "--goal-b-y", "1.0",
        ]
    )


class PostHandoffRunner(XRNav2TrialRunner):
    def direct_cancel_exact(self, goal_uuid: str, ctx: Any) -> dict[str, Any]:
        if not self.node.cleanup_cancel_client.wait_for_service(timeout_sec=2.0):
            return {"success": False, "error": "cancel service unavailable"}
        request = CancelGoal.Request()
        request.goal_info.goal_id.uuid = list(bytes.fromhex(goal_uuid))
        request.goal_info.stamp.sec = 0
        request.goal_info.stamp.nanosec = 0
        sent = self.recorder.emit(
            "negative_control",
            "DIRECT_EXACT_GOAL_CANCEL_SENT",
            case_id=ctx.case_id,
            trial_id=ctx.trial_id,
            actor="test_oracle",
            data={"goal_uuid": goal_uuid, "service": f"{self.args.nav2_action}/_action/cancel_goal"},
        )
        future = self.node.cleanup_cancel_client.call_async(request)
        try:
            self.wait(future.done, 4.0, "direct exact cancel response", ctx=ctx)
            response = future.result()
            if response is None:
                return {"success": False, "sent_at": sent, "error": "no response"}
            canceling = [self.node._uuid(item.goal_id) for item in response.goals_canceling]
            return {
                "success": goal_uuid in canceling,
                "sent_at": sent,
                "return_code": int(response.return_code),
                "goal_ids_canceling": canceling,
            }
        except Exception as exc:
            return {"success": False, "sent_at": sent, "error": f"{type(exc).__name__}: {exc}"}

    def wait_terminal(self, ctx: Any, goal_uuid: str, after_ns: int, timeout_s: float) -> dict[str, Any] | None:
        try:
            return self.wait(
                lambda: self.node.first_status_event(goal_uuid, TERMINAL_STATUSES, after_ns=after_ns),
                timeout_s,
                f"terminal state for {goal_uuid}",
                ctx=ctx,
            )
        except Exception:
            return None

    def run_timing(self, mode: str, trial_number: int, official_observation_sec: float) -> dict[str, Any]:
        config = MODES[mode]
        case_id = f"B_{mode.upper()}"
        ctx, setup = self.setup_trial(case_id, trial_number, need_b=True)
        result = self.common_result(
            ctx,
            setup,
            "POST_HANDOFF_OWNERSHIP_INTEGRITY",
            "B's valid cancel must terminate B Goal even after A's late result callback",
        )
        try:
            a = ctx.clients["A"]
            b = ctx.clients["B"]
            self.set_heartbeat(ctx, "A", False)
            a.state.lose_focus("A yields authority for post-handoff test")
            authority = a.state.set_control(
                ControlState.RELEASED,
                "A control released before B handoff",
            )
            a_release = self.release(ctx, "A")
            b.state.boot_to_focused()
            b_acquire = self.acquire(ctx, "B")
            self.set_heartbeat(ctx, "B", True)

            backend_since = self.node.backend_status_count()
            b_goal = self.send_goal(
                ctx,
                "B",
                "B",
                (self.args.goal_b_x, self.args.goal_b_y, self.args.goal_b_yaw),
            )
            a_uuid = ctx.goal_ids["A"]
            b_uuid = ctx.goal_ids["B"]
            b_accept = b_goal["accepted_observed_at"]

            a_result_status = self.node.first_status_event(
                a_uuid,
                {GoalStatus.STATUS_ABORTED},
                after_ns=b_goal["sent_at"]["monotonic_ns"],
            )
            if config["anchor"] == "a_result":
                a_backend_result = self.wait(
                    lambda: self.node.first_backend_status(backend_since, "goal_failed"),
                    2.0,
                    "A late result published by HORUS adapter",
                    ctx=ctx,
                )
                anchor = a_backend_result["at"]
            else:
                a_backend_result = None
                anchor = b_accept

            target_ns = anchor["monotonic_ns"] + int(config["offset_ms"] * 1_000_000)
            self.wait_until_ns(ctx, target_ns)
            official: dict[str, Any] | None = None
            direct: dict[str, Any] | None = None
            official_terminal: dict[str, Any] | None = None

            if config["path"] == "horus":
                cancel_since = self.node.cancel_event_count()
                cancel_sent = self.recorder.emit(
                    "horuslink",
                    "B_OFFICIAL_CANCEL_SENT",
                    case_id=ctx.case_id,
                    trial_id=ctx.trial_id,
                    actor="B",
                    data={"goal_uuid_expected": b_uuid, "payload": "cancel"},
                )
                b.client.publish_cancel()
                cancel_topic = self.wait(
                    lambda: self.node.first_cancel_event(cancel_since),
                    2.0,
                    "B cancel topic observation",
                    ctx=ctx,
                )
                official_terminal = self.wait_terminal(
                    ctx,
                    b_uuid,
                    cancel_sent["monotonic_ns"],
                    official_observation_sec,
                )
                official_worked = bool(
                    official_terminal is not None
                    and official_terminal["status"] == GoalStatus.STATUS_CANCELED
                )
                official = {
                    "sent_at": cancel_sent,
                    "topic_observed": cancel_topic,
                    "terminal": official_terminal,
                    "worked": official_worked,
                }
                if not official_worked:
                    direct = self.direct_cancel_exact(b_uuid, ctx)
            else:
                cancel_sent = self.recorder.emit(
                    "negative_control",
                    "DIRECT_EXACT_CANCEL_TRIGGER",
                    case_id=ctx.case_id,
                    trial_id=ctx.trial_id,
                    actor="test_oracle",
                    data={"goal_uuid": b_uuid},
                )
                direct = self.direct_cancel_exact(b_uuid, ctx)

            if a_backend_result is None:
                a_backend_result = self.wait(
                    lambda: self.node.first_backend_status(backend_since, "goal_failed"),
                    2.0,
                    "A late result observation",
                    ctx=ctx,
                )
            if a_result_status is None:
                a_result_status = self.wait(
                    lambda: self.node.first_status_event(
                        a_uuid,
                        {GoalStatus.STATUS_ABORTED},
                        after_ns=b_goal["sent_at"]["monotonic_ns"],
                    ),
                    2.0,
                    "A Nav2 ABORTED state",
                    ctx=ctx,
                )

            direct_terminal: dict[str, Any] | None = None
            if direct is not None and direct.get("sent_at") is not None:
                direct_terminal = self.wait_terminal(
                    ctx,
                    b_uuid,
                    direct["sent_at"]["monotonic_ns"],
                    3.0,
                )
            effective_cancel_at = (
                official["sent_at"]
                if official is not None and official.get("worked")
                else None if direct is None else direct.get("sent_at")
            )
            robot_stop = None
            if effective_cancel_at is not None:
                try:
                    robot_stop = self.wait(
                        lambda: self.node.robot_stop_candidate(effective_cancel_at["monotonic_ns"]),
                        4.0,
                        "robot stop after effective B cancel",
                        ctx=ctx,
                    )
                except Exception:
                    robot_stop = None

            measurement_end_ns = time.monotonic_ns()
            official_path = self.node.odom_metric(
                cancel_sent["monotonic_ns"],
                (
                    measurement_end_ns
                    if direct is None or direct.get("sent_at") is None
                    else direct["sent_at"]["monotonic_ns"]
                ),
            )
            sent_before_backend_result = (
                cancel_sent["monotonic_ns"] < a_backend_result["at"]["monotonic_ns"]
            )
            direct_pass = bool(
                direct is not None
                and direct.get("success")
                and direct_terminal is not None
                and direct_terminal["status"] == GoalStatus.STATUS_CANCELED
            )
            if config["path"] == "direct_exact":
                classification = (
                    "NEGATIVE_CONTROL_DIRECT_EXACT_CANCEL_PASS"
                    if direct_pass
                    else "NEGATIVE_CONTROL_DIRECT_EXACT_CANCEL_FAIL"
                )
            elif official is not None and official.get("worked"):
                classification = "B_OFFICIAL_CANCEL_SUCCEEDED"
            elif direct_pass:
                classification = "POST_HANDOFF_B_CANCEL_INTERFERENCE_CONFIRMED"
            else:
                classification = "B_CANCEL_INCONCLUSIVE"

            result.update(
                {
                    "mode": mode,
                    "mode_config": config,
                    "authority_event": authority,
                    "a_lease_release": a_release,
                    "b_lease_acquire": b_acquire,
                    "goal_uuid_a": a_uuid,
                    "goal_uuid_b": b_uuid,
                    "b_goal": b_goal,
                    "a_nav2_aborted": a_result_status,
                    "a_adapter_result_published": a_backend_result,
                    "b_cancel_sent_at": cancel_sent,
                    "cancel_ordering": {
                        "sent_before_a_adapter_result_publish": sent_before_backend_result,
                        "delta_cancel_minus_a_result_publish_ms": self.elapsed_ms(
                            cancel_sent,
                            a_backend_result["at"],
                        ),
                        "source_ordering_note": (
                            "fixed adapter resets active_goal_handle before publishing goal_failed; "
                            "a cancel after this event is definitely post-reset"
                        ),
                    },
                    "official_horus_cancel": official,
                    "direct_exact_cancel": direct,
                    "direct_exact_terminal": direct_terminal,
                    "robot_stop": robot_stop,
                    "post_official_cancel_before_direct": official_path,
                    "b_final_goal_record": self.node.goal_record(b_uuid),
                    "metrics_ms": {
                        "b_send_to_accept": self.elapsed_ms(b_accept, b_goal["sent_at"]),
                        "a_release_to_b_grant": self.elapsed_ms(
                            b_acquire["observed"]["at"],
                            a_release["observed"]["at"],
                        ),
                        "b_cancel_to_b_terminal": self.elapsed_ms(
                            official_terminal["at"] if official_terminal is not None else None,
                            cancel_sent,
                        ),
                        "effective_cancel_to_robot_stop": self.elapsed_ms(
                            None if robot_stop is None else robot_stop["detected_at"],
                            effective_cancel_at,
                        ),
                    },
                    "classification": classification,
                    "evidence_level": "CONFIRMED_BY_RUNTIME",
                    "security_meaning": (
                        "SECURITY_PROPERTY_VIOLATION"
                        if classification == "POST_HANDOFF_B_CANCEL_INTERFERENCE_CONFIRMED"
                        else "CONFIRMED_SAFE_BEHAVIOR"
                        if classification.startswith("NEGATIVE_CONTROL")
                        or classification == "B_OFFICIAL_CANCEL_SUCCEEDED"
                        else "INCONCLUSIVE"
                    ),
                    "physical_robot": False,
                    "measurement_verdict": "MEASURED",
                }
            )
            return self.finish_result(ctx, result)
        except Exception:
            self.cleanup_trial(ctx)
            raise


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for mode in MODES:
        selected = [item for item in results if item.get("mode") == mode]
        classifications: dict[str, int] = {}
        deltas: list[float] = []
        official_success = 0
        direct_success = 0
        for item in selected:
            label = str(item.get("classification", "ERROR"))
            classifications[label] = classifications.get(label, 0) + 1
            delta = item.get("cancel_ordering", {}).get("delta_cancel_minus_a_result_publish_ms")
            if isinstance(delta, (int, float)):
                deltas.append(float(delta))
            official_cancel = item.get("official_horus_cancel") or {}
            official_success += int(bool(official_cancel.get("worked")))
            direct_terminal = item.get("direct_exact_terminal") or {}
            direct_success += int(
                direct_terminal.get("status") == GoalStatus.STATUS_CANCELED
            )
        output[mode] = {
            "requested": len(selected),
            "complete": sum(bool(item.get("trial_complete")) for item in selected),
            "classifications": classifications,
            "official_horus_cancel_success": official_success,
            "direct_exact_cancel_success": direct_success,
            "cancel_minus_a_result_ms": (
                None
                if not deltas
                else {
                    "min": round(min(deltas), 6),
                    "median": round(statistics.median(deltas), 6),
                    "max": round(max(deltas), 6),
                }
            ),
        }
    return output


def main() -> int:
    cli = parse_cli(sys.argv[1:])
    args = base_args(cli)
    run_id = datetime.now(timezone.utc).strftime("xr2act-horus-%Y%m%dT%H%M%SZ")
    recorder = TimelineRecorder(cli.timeline_log, run_id)
    output_path = Path(cli.output_log)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = output_path.open("w", encoding="utf-8", buffering=1)
    results: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "schema": "xr2act-horus-post-handoff/v1",
        "run_id": run_id,
        "fixed_horus_revision": FIXED_HORUS_REVISION,
        "actual_horus": True,
        "actual_nav2": True,
        "simulation": "nav2_loopback_sim",
        "physical_robot": False,
        "modes": cli.modes,
        "trials_per_mode": cli.trials,
    }
    started = recorder.emit("probe", "RUN_BEGIN", data=report)
    rclpy.init(args=sys.argv)
    node = Nav2Observer(args, recorder)
    executor = MultiThreadedExecutor(num_threads=12)
    executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    runner = PostHandoffRunner(node, recorder, args)
    unregistered = False
    exit_code = 1
    try:
        report["preflight"] = runner.preflight()
        for mode in cli.modes:
            for trial_number in range(1, cli.trials + 1):
                print(
                    f"[HORUS post-handoff] {mode} trial {trial_number}/{cli.trials}",
                    file=sys.stderr,
                    flush=True,
                )
                try:
                    trial = runner.run_timing(mode, trial_number, cli.official_observation_sec)
                except Exception as exc:
                    trial = {
                        "mode": mode,
                        "trial_id": f"B_{mode.upper()}-T{trial_number:02d}",
                        "trial_complete": False,
                        "classification": "HARNESS_ERROR",
                        "error": f"{type(exc).__name__}: {exc}",
                        "traceback": traceback.format_exc(),
                    }
                results.append(trial)
                output.write(json.dumps(json_safe(trial), sort_keys=True) + "\n")
        report["aggregate"] = aggregate(results)
        report["trials_complete"] = sum(bool(item.get("trial_complete")) for item in results)
        report["trials_requested"] = len(results)
        report["errors"] = len(results) - report["trials_complete"]
        report["measurement_valid"] = report["errors"] == 0
        if runner.robot_id is not None:
            report["robot_unregistration"] = node.unregister_robot(runner.robot_id, runner.wait)
            unregistered = True
        report["completed_at"] = recorder.emit(
            "probe",
            "RUN_COMPLETE",
            data={"measurement_valid": report["measurement_valid"], "errors": report["errors"]},
        )
        output.write(json.dumps({"record_type": "RUN_SUMMARY", **json_safe(report)}, sort_keys=True) + "\n")
        print("XR2ACT_HORUS_JSON_BEGIN")
        print(json.dumps(json_safe(report), indent=2, sort_keys=True))
        print("XR2ACT_HORUS_JSON_END")
        exit_code = 0 if report["measurement_valid"] else 1
    finally:
        if runner.robot_id is not None and not unregistered:
            try:
                node.unregister_robot(runner.robot_id, runner.wait)
            except Exception:
                pass
        runner.close()
        executor.shutdown(timeout_sec=4.0)
        node.destroy_observer()
        rclpy.shutdown()
        spin_thread.join(timeout=4.0)
        recorder.close()
        output.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
