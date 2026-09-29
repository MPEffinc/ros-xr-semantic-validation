#!/usr/bin/env python3

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


HARNESS_DIR = Path(__file__).resolve().parent
VALIDATION_ROOT = HARNESS_DIR.parent
TARGET_ROOT = VALIDATION_ROOT / "targets" / "spes_teleop"
sys.path.insert(0, str(TARGET_ROOT))

import numpy as np  # noqa: E402
from teleop import Teleop  # noqa: E402


def make_message(label: str, x: float, y: float, z: float) -> dict:
    return {
        "label": label,
        "move": True,
        "position": {"x": x, "y": y, "z": z},
        "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
        "scale": 1.0,
        "device": "VR",
    }


def vector(matrix: np.ndarray) -> list[float]:
    return [round(float(value), 9) for value in matrix[:3, 3]]


def read_git_head(repository_root: Path) -> str:
    git_dir = repository_root / ".git"
    head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref: "):
        return head
    ref = head[5:]
    loose_ref = git_dir / ref
    if loose_ref.exists():
        return loose_ref.read_text(encoding="utf-8").strip()
    for line in (git_dir / "packed-refs").read_text(encoding="utf-8").splitlines():
        if not line.startswith("#") and line.endswith(f" {ref}"):
            return line.split(" ", 1)[0]
    raise RuntimeError(f"cannot resolve Git ref {ref}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    commit = read_git_head(TARGET_ROOT)
    records = [
        {
            "event": "run_start",
            "harness": "spes_server_replay",
            "target_commit": commit,
            "executed_source": "teleop.Teleop._Teleop__update",
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "python": sys.version.split()[0],
            "numpy": np.__version__,
        }
    ]

    teleop = Teleop(natural_phone_orientation_euler=[0.0, 0.0, 0.0])
    teleop.set_pose(np.eye(4))
    callbacks: list[dict] = []

    def callback(pose: np.ndarray, message: dict) -> None:
        callbacks.append(
            {
                "input_label": message["label"],
                "target_translation": vector(pose),
                "device": message.get("device"),
                "source_field_present": "source" in message,
            }
        )

    teleop.subscribe(callback)
    sequence = [
        make_message("controller_P1", 0.00, 0.00, 0.00),
        make_message("controller_P2", 0.00, 0.02, 0.00),
        make_message("viewer_Q1", 1.00, 0.00, 0.00),
        make_message("viewer_Q2", 1.02, 0.00, 0.00),
        make_message("viewer_Q3", 1.04, 0.00, 0.00),
    ]

    per_step = []
    for message in sequence:
        before = len(callbacks)
        teleop._Teleop__update(message)
        emitted = len(callbacks) - before
        record = {
            "event": "input_result",
            "input_label": message["label"],
            "callback_emitted": emitted == 1,
            "callback_count_delta": emitted,
            "target_translation": vector(teleop._Teleop__pose),
            "relative_anchor_present": teleop._Teleop__relative_pose_init is not None,
            "previous_received_pose_present": (
                teleop._Teleop__previous_received_pose is not None
            ),
        }
        records.append(record)
        per_step.append(record)

    assert [step["callback_count_delta"] for step in per_step] == [1, 1, 0, 1, 1]
    assert per_step[2]["relative_anchor_present"] is False
    assert per_step[2]["previous_received_pose_present"] is True
    assert per_step[3]["callback_emitted"] is True
    assert per_step[3]["target_translation"] == per_step[1]["target_translation"]
    assert per_step[4]["callback_emitted"] is True
    assert per_step[4]["target_translation"] != per_step[3]["target_translation"]
    assert all(not event["source_field_present"] for event in callbacks)

    records.append(
        {
            "event": "summary",
            "first_viewer_pose_rejected": True,
            "nearby_viewer_pose_accepted": True,
            "viewer_trajectory_changed_target": True,
            "callback_labels": [event["input_label"] for event in callbacks],
            "result": "PASS",
        }
    )

    rendered = "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
