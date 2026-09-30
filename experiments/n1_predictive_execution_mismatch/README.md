# N1 pilot — predictive/twin display vs. executed ROS state

Kill-first simulation pilot for candidate N1 from
`../crossflow_gap_validation_2026-09-30/docs/08_new_gap_search.md`. It tests whether the normal
combination of existing techniques keeps an operator-side prediction consistent with what the ROS 2
pipeline actually executes.

Stack: pinned `openvr_ur5e_jazzy@170dad5` (UR5, Gazebo + ros2_control + MoveIt Servo), image
`openvr-jazzy-sim:local`. It is mounted read-only; the build goes to a scratch workspace, and no original
asset is edited. Added nodes (operator script, delay, shared-autonomy blend, safety barrier, recorder)
live in `scripts/`. Predictors are evaluated offline, causally, from logged streams, so every predictor
sees identical inputs.

Provenance: robot, controller and Servo = UPSTREAM (real software, simulated plant); operator and XR
predictor = SYNTHETIC.

Docs: `docs/01`–`06`; decision: `DECISION.md`; progress: `STATUS.md`.
