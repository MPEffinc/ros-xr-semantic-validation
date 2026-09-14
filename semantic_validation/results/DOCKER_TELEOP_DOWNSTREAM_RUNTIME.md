# Docker_Teleop simulator downstream runtime

## Run boundary

Pinned `Noah727/Docker_Teleop@64cbdde88bc52c6a80d37f994752e50f95ba537e` was run in the documented isolated x86_64 Gazebo-only environment.  The chain was:

```text
synthetic newline JSON TCP
-> quest_controller_receiver
-> /received_pose_states
-> hand_pose_mapper
-> /target_twist_states
-> servo_command_bridge
-> /servo_node/delta_twist_cmds
-> MoveIt Servo -> joint_group_velocity_controller -> gz_ros2_control
```

`joint_group_velocity_controller` was active and `servo_command_bridge` received a successful `/servo_node/start_servo` response.  The source tree and semantic/control logic were not modified.

## D1/D2 controlled pair

The sender first held a tracked reference pose, then held a position delta with grip/teleop true.  D1 produced mapper linear velocity `0.092 m/s` and production servo-bridge output `0.098 m/s`, with `tracked=true` and `active=true`.

D2 retained the pose and teleop fields but set only `isTracked=false`.  The mapper reported `tracked=false` and zero linear/angular output; the servo bridge reported `active=false` and zero twist.  This confirms the production tracking gate through the bridge and MoveIt Servo input boundary in the simulator session.

## D3-D5

- D3: a 0.60 s sender stall exceeds the 0.25 s receiver timeout.  Receiver neutralization made mapper/bridge `tracked=false`, `active=false`, and zero twist; a later valid input re-engaged and recaptured the mapper reference.
- D4: a fresh arrival with `timestamp=1.0` re-engaged normally.  No source-time field or age gate is present after the receiver, so this run does not distinguish old source time from current source time.
- D5: first-client close and second-client acceptance were observed.  The mapper emitted a new reference capture for the accepted second input.  This is evidence of a first post-reconnect reference capture, not proof of every internal session state reset.

## Evidence and limits

Evidence is `E2 SYNTHETIC_RUNTIME` / `UPSTREAM_FAITHFUL_REPLAY` for ROS-side logic.  The raw bag contains 1,067 `/received_pose_states`, 1,042 `/target_twist_states`, 1,067 `/servo_node/delta_twist_cmds`, and 934 `/joint_states` messages: `semantic_validation/results/runs/docker_teleop_e2e_20260914/bag/`.

This supports a simulator-native downstream consequence claim, not native Quest behavior, Pi reception, or physical actuator execution.  The highest-value remaining Docker_Teleop test is targeted joint/end-effector displacement extraction from the bag, then a final integrated evidence update.
