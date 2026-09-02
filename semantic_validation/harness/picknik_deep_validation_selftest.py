#!/usr/bin/env python3
"""Small deterministic tests for PickNik source-analysis helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).with_name("picknik_deep_validation.py")
SPEC = importlib.util.spec_from_file_location("picknik_deep_validation", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

HW_MODULE_PATH = Path(__file__).with_name("picknik_hw_analyze.py")
HW_SPEC = importlib.util.spec_from_file_location("picknik_hw_analyze", HW_MODULE_PATH)
assert HW_SPEC is not None and HW_SPEC.loader is not None
HW_MODULE = importlib.util.module_from_spec(HW_SPEC)
HW_SPEC.loader.exec_module(HW_MODULE)


class PickNikDeepValidationSelfTest(unittest.TestCase):
    def test_method_extraction_is_brace_balanced(self) -> None:
        source = "public void Update() { if (true) { Call(); } }\nvoid Other() {}"
        self.assertEqual(
            MODULE.extract_method(source, r"public\s+void\s+Update\s*\(\s*\)"),
            "public void Update() { if (true) { Call(); } }",
        )

    def test_stripped_unity_object_is_supported(self) -> None:
        source = "--- !u!1 &42 stripped\nGameObject:\n  value: 1\n--- !u!4 &43\nTransform:\n"
        self.assertIn("value: 1", MODULE.unity_object(source, 1, 42))
        self.assertNotIn("Transform", MODULE.unity_object(source, 1, 42))

    def test_source_model_has_no_tracking_field(self) -> None:
        pose = (1.0, 2.0, 3.0, 0.0, 0.0, 0.0, 1.0)
        modeled = MODULE.source_publish_model(pose=pose, stamp_ns=123)
        self.assertEqual(modeled["odom"]["pose"], list(pose))
        self.assertNotIn("tracking_state", str(modeled))
        self.assertNotIn("is_tracked", str(modeled))

    def test_future_hw_classifier_requires_real_loss_transition(self) -> None:
        def sample(ms: int, tracked: bool, state: int) -> dict[str, object]:
            return {
                "event_type": "raw_sample",
                "side": "right",
                "wall_unix_ms": ms,
                "unity_frame": ms,
                "input_present": True,
                "game_object_present": True,
                "is_tracked": tracked,
                "tracking_state": state,
                "application_focused": True,
                "application_paused": False,
                "xr_display_running": True,
            }

        sideband = [sample(1000, True, 3), sample(1010, False, 0), sample(1020, False, 0), sample(1030, True, 3)]
        ros = []
        for ms in (1010, 1020):
            for event_type in ("ros_receive_odometry", "ros_receive_tf"):
                ros.append(
                    {
                        "event_type": event_type,
                        "topic": "/right_controller_odom" if event_type.endswith("odometry") else "/tf",
                        "child_frame_id": "right_controller_odom",
                        "ros_stamp_ns": ms * 1_000_000,
                        "position": [1.0, 2.0, 3.0],
                        "orientation": [0.0, 0.0, 0.0, 1.0],
                    }
                )
        result = HW_MODULE.analyze(sideband, ros)
        self.assertEqual(result["trial_count"], 1)
        self.assertEqual(result["trials"][0]["classification"], "HW_PICKNIK_UNTRACKED_ROS_CONTINUES")


if __name__ == "__main__":
    unittest.main()
