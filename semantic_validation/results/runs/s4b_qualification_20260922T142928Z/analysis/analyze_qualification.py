#!/usr/bin/env python3
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fields(path: Path) -> list[str]:
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(("geometry_msgs/", "std_msgs/", "builtin_interfaces/")):
            continue
        match = re.match(r"\S+\s+(\w+)", line)
        if match:
            result.append(match.group(1))
    return result


probe = json.loads((ROOT / "rosmonitoring/humble/edge_probe_03.json").read_text(encoding="utf-8"))
target_fields = fields(ROOT / "inputs/teleop_bridge_msgs_src/msg/TargetTwistStates.msg")
received_fields = fields(ROOT / "inputs/teleop_bridge_msgs_src/msg/ReceivedPoseStates.msg")
official = {}
for distro, name in (("humble", "rosmonitoring_humble_official_test_retry.log"),
                     ("jazzy", "rosmonitoring_jazzy_official_test.log")):
    text = (ROOT / "stdout" / name).read_text(encoding="utf-8")
    official[distro] = {"passed": "1 passed" in text, "python": re.search(r"platform .*? -- Python ([^,]+)", text).group(1)}

summary = {
    "official_rosmonitoring": official,
    "edge_assertions": probe["assertions"],
    "lineage_schema": {
        "received_pose_states_fields": received_fields,
        "target_twist_states_fields": target_fields,
        "source_sample_id_preserved": "source_sample_id" in received_fields and "source_sample_id" in target_fields,
        "source_generation_id_preserved": "source_generation_id" in received_fields and "source_generation_id" in target_fields,
        "native_state_preserved_to_target": "native_state" in target_fields,
        "source_timestamp_preserved_to_target": False,
        "finding": "Original schemas do not carry sample/generation IDs; exact source-to-repeated-command lineage cannot be established without an observational overlay/schema channel.",
    },
}
(ROOT / "analysis/qualification_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

