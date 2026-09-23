# CP1 OpenVR hold-fast setup variant — frozen before execution

Variant ID: OPENVR_PAUSE_HOLD_FAST_01. Qualification only, not a B0–B3 comparison arm. Protocol XRROS-S4-1.0.0 remains unchanged.

The 2026-09-22 `openvr_hold_01` trial used Servo pause plus one current-position JointTrajectory point with 50 ms `time_from_start`; it settled at 1203.14 ms and moved during `new_reference`. This failure remains part of the record.

This separate variant copies that Gazebo-only launcher and fake-API fixture into a new trial-owned directory. It uses the same original `QuestTeleop` and vendor binaries without source edits. The recorder subscribes to `/ur5_arm_controller/controller_state`, checks DDS publisher/subscriber matches, and after Servo pause publishes five measured-current-position hold trajectories at 20 ms intervals, each with a 10 ms point duration. It never sends zero absolute pose. Stop request, pause reply, every hold publication, controller state, trajectory and named `/joint_states` are logged. The existing reference-release/repress sequence is unchanged. It is an ordinary stop/hold integration variant, not a source validity decision.

No previous failed attempt is overwritten. Trial parameters and code are committed before first execution. A successful service reply or trajectory publication is not a stop PASS; the 1 s joint settle and safe re-arm criteria remain frozen.
