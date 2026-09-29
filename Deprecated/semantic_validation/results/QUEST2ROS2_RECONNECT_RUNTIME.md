# Quest2ROS2 reconnect/session runtime

- Framework: `Taokt/Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef`
- Path: synthetic ROS publisher process -> pinned production `right_arm_controller` -> `/bh_robot/right_arm_clik_controller/target_frame`
- Environment: isolated ROS 2 Humble container, `ROS_DOMAIN_ID=211`, static base-to-EEF TF fixture; no Quest, CLIK consumer, robot, gripper server, or actuator.

## Executed sequence

The production controller remained alive throughout.  Separate source processes established a baseline at input x=0.50, moved to x=0.60, disconnected for 2.5 s, then reconnected at x=0.70.  A second sequence toggled `button_lower` to disable streaming, replaced the source while disabled, then sent release and a new rising edge before publishing x=0.90.

## Observed production behavior

- After filter warm-up, the controller anchored at robot x=0.4000.
- Before disconnect, input x=0.60 produced target x=0.5000.
- After the 2.5 s publisher absence and a newly created publisher at input x=0.70, the unchanged controller produced target x=0.6000.  The original anchor/filter lineage therefore survived this ROS source disconnect/reconnect equivalent; no connection-generation reset exists at this boundary.
- The first `button_lower=true` rising edge disabled pose streaming.  Replacing the publisher while it continued sending `true` did not re-enable output because the controller's edge latch persisted.
- A `false` release followed by a new `true` rising edge re-enabled streaming, cleared the filter, and forced a new anchor.  Logs show filter fill `1/3`, `2/3`, then `Anchored robot pose` before output resumed.
- No production watchdog event altered the controller during the 2.5 s gap; the separate `CheckTCPconnection` watchdog was not part of this executed control path.

## Evidence boundary

This is `E2 SYNTHETIC_RUNTIME`.  It demonstrates production host-side session behavior under an actual ROS publisher disconnect/reconnect, not Quest app reconnection semantics and not native downstream controller acceptance.  The harness is `semantic_validation/harness/quest2ros2_reconnect_runtime.py`.

Strongest defensible claim: at the pinned production controller boundary, ROS source replacement alone does not reset anchor/filter or button-edge state; explicit operator-equivalent release/rising-edge input is required to re-enable and re-anchor after the latch is disabled.
