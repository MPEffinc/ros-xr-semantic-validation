#!/usr/bin/env python3
"""Qualification-only exact lineage carrier; not a production controller."""
import json
import time
from pathlib import Path


OUT = Path("/home/cclab/ros_xr/semantic_validation/results/runs/s4b_qualification_20260922T142928Z/lineage/contract_probe.jsonl")


def emit(row: dict) -> None:
    with OUT.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")


generation = "generation-0001"
samples = [
    {"source_sample_id": "sample-0001", "source_generation_id": generation,
     "native_state": {"api": "DOCKER_SYNTHETIC", "tracked": True},
     "source_timestamp_ns": 1_000_000_000},
    {"source_sample_id": "sample-0002", "source_generation_id": generation,
     "native_state": {"api": "DOCKER_SYNTHETIC", "tracked": False},
     "source_timestamp_ns": 1_020_000_000},
    {"source_sample_id": "sample-0003", "source_generation_id": "generation-0002",
     "native_state": {"api": "DOCKER_SYNTHETIC", "tracked": True},
     "source_timestamp_ns": 2_000_000_000},
]

command_sequence = 0
for sample in samples:
    emit({"record_type": "source_sample", "observed_monotonic_ns": time.monotonic_ns(), **sample})
    repeat = 3 if sample["source_sample_id"] == "sample-0001" else (0 if not sample["native_state"]["tracked"] else 2)
    for child_index in range(repeat):
        emit({
            "record_type": "command_lineage",
            "command_sequence": command_sequence,
            "source_sample_id": sample["source_sample_id"],
            "source_generation_id": sample["source_generation_id"],
            "source_timestamp_ns": sample["source_timestamp_ns"],
            "native_state": sample["native_state"],
            "repeat_index": child_index,
            "command_monotonic_ns": time.monotonic_ns(),
        })
        command_sequence += 1

rows = [json.loads(line) for line in OUT.read_text(encoding="utf-8").splitlines()]
source_ids = {row["source_sample_id"] for row in rows if row["record_type"] == "source_sample"}
commands = [row for row in rows if row["record_type"] == "command_lineage"]
assert all(row["source_sample_id"] in source_ids for row in commands)
assert not any(row["source_sample_id"] == "sample-0002" for row in commands)
assert [row["repeat_index"] for row in commands if row["source_sample_id"] == "sample-0001"] == [0, 1, 2]

