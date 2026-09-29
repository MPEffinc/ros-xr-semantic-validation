# Docker_Teleop production receiver runtime

## Scope

- Framework: `Noah727/Docker_Teleop`
- Pinned revision: `64cbdde88bc52c6a80d37f994752e50f95ba537e`
- Evidence: `E2 SYNTHETIC_RUNTIME`; replay class `UPSTREAM_FAITHFUL_REPLAY` for the ROS-side receiver.
- Environment: isolated `ros-xr-humble:local` ROS 2 Humble container.  No Quest, robot driver, actuator, MoveIt Servo, or Gazebo process was started for this checkpoint.

## Injection and production boundary

`semantic_validation/harness/docker_teleop_tcp_trials.py` serializes the newline-framed JSON schema used by `UnityApp/Assets/Scripts/HandPoseSender.cs:249-261,325-336` and sends it to the unmodified production `receiver.quest_controller_receiver` TCP listener.  The listener is therefore downstream of the synthetic source but upstream of all production ROS-side semantic decisions.

The receiver and `teleop_bridge_msgs` packages built successfully in the isolated container.  The receiver published `/received_pose_states` at 60 Hz with `stale_timeout_sec=0.25`.

## D1-D5

| Trial | Input | Observed boundary result | Scope |
| --- | --- | --- | --- |
| D1 | `isTracked=true`, valid pose, grip/teleop true | `/received_pose_states` carried `tracked: true`, pose `x: 0.35`, `grip_value: 1.0`, and `teleop_enable: true`. | Production receiver to ROS publication confirmed. |
| D2 | Only `isTracked=false` with pose/control fields retained | Production ROS output contained `tracked: false` (380 samples captured). | Receiver propagation only; not a downstream control result. |
| D3 | Sender paused for 0.60 s (>0.25 s receiver timeout) | Receiver selected its neutral stale state and ROS output was `tracked: false`. | Receiver stale policy confirmed. |
| D4 | Fresh TCP arrival with Unity JSON `timestamp=1.0` | `ReceivedPoseStates` has no source-timestamp field and the receiver creates `header.stamp` from `self.get_clock().now()` in `_publish_loop`; the old input timestamp is neither read nor copied. | Source time is not preserved at this boundary. |
| D5 | Second client connected while the first remained open, then first closed | Log records first peer close followed by second client acceptance. | Connection acceptance only. No session, anchor, or downstream state carry-over claim. |

Raw receiver-topic capture: `semantic_validation/results/runs/docker_teleop_receiver_smoke_20260914/received_pose_states.log` (`sha256=0fb328b210f514181ac77f4189c5aed9fd3a4f382be49a910d19c930359549c9`).

## D4 exact interpretation

The sender's native schema contains `Packet.timestamp` (`HandPoseSender.cs:87-93`) and assigns it from `Time.time` (`:249-250`).  The production receiver parses hand/control fields in `_parse_payload` but has no `timestamp` access; it creates the ROS header with `self.get_clock().now().to_msg()` in `_publish_loop`.  Thus a fresh packet carrying deliberately old `timestamp=1.0` is accepted according to arrival age, and its ROS header represents receiver publication time, not source sample time.  This is a transformation/drop observation, not a claim that any particular downstream clock contract is violated.

## Environment-only adaptation

The pending full simulator image uses a disposable x86_64 copy of the upstream Dockerfile.  It adds `DEBIAN_FRONTEND=noninteractive` and workspace ownership for `noah`; upstream application and semantic/control logic remain unchanged.  These are build/testbed adaptations only.

## Strongest claim and next step

This checkpoint proves production receiver behavior under synthetic wire input: tracking and stale state reach `/received_pose_states`, while Unity source timestamp does not.  It does **not** prove mapper/Servo/Gazebo acceptance or physical actionability.  Next: safely bring up only `run_tabletop_sim.sh` plus `servo_gz.launch.py`, then the production mapper and servo bridge; never launch `servo_test.launch.py`.
