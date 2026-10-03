# A05 — Docker_Teleop mapper/bridge code audit (read-only, @64cbdde, 2026-10-04)

**Scope.** This is a code audit only; nothing was built or run. Paths are relative to `ros_backend1.1/` of the pinned
checkout (read only). "Mapper" is `src/teleop_bridge/teleop_bridge/mapping/hand_pose_mapper.py`. Two items are
UNCONFIRMED: Servo's own stale-check semantics, and whether any launch loads `servo.yaml`.

## Pipeline

```
receiver ─▶ /received_pose_states ─▶ mapper ─▶ /target_twist_states ─┬─▶ servo_command_bridge ─▶ /servo_node/delta_twist_cmds ─▶ MoveIt Servo ─▶ /joint_group_velocity_controller/commands
                                                                      ├─▶ gripper bridge ─▶ /hande_position_controller/commands
                                                                      └─▶ reset_manager ─▶ both controller topics directly + Servo stop/start/reset services
```

- There are no teleop launch files. `scripts/backend11_lifecycle.sh` starts the nodes with `ros2 run` (L418–421 for
  single arm, L660–667 for dual arm). Servo loads `servo_gz.yaml`.

## Fields per hop

| Hop | Time | `source` / neutral reason | seq / session | Enable / buttons |
|---|---|---|---|---|
| receiver → mapper | input `header.stamp` ignored; arrival `time.monotonic()` (L736); output stamp = tick `now()` (L1059) | never read | none exist | `teleop_enable` consumed: rising edge → recenter (L765–767); falling edge → clear sessions, "disengaged by right grip release" (L768–772) |
| mapper → servo bridge | restamped `now()` (L136) | — (TargetTwistStates has no source/reason field) | — | `tracked`, `reset_enable` used; inactive → zero twist published at 60 Hz (L142–150) |
| mapper → gripper bridges | no header | — | — | `gripper_cmd`, `tracked`, `reset_enable` |
| Servo → controller | Float64MultiArray, no header | — | — | — |

**Neutral vs. release.** A stale-timeout neutral (`teleop_enable=False`, `tracked=False`, `source="*stale_timeout"`)
follows the **same branches** as a deliberate grip release (L768, L866). When fresh packets resume, the rising edge
re-anchors (L765). The mapper output has no neutral flag.

## Calibration and anchoring state

- **Owner:** private to the mapper process (L259–289).
- **Position anchor:**
  - `ee_ref` comes from the latest tf `base_link←tool0` (L1529–1559, `Time()`, no age check);
  - `hand_ref` comes from the pending recenter sample;
  - target = `ee_ref + (hand − hand_ref)·scale + offset`, clipped (L1247–1248).
- **Re-anchor triggers:**
  - enable edges;
  - reset_robot;
  - recenter clutch;
  - mode/attachment changes carried in the input message;
  - `tracked=False`;
  - stale tick;
  - reset latch;
  - runtime parameter changes.
- **No services are exposed** by the mapper or the bridges. Any process can:
  - publish `/received_pose_states` or `/target_twist_states`;
  - set mapper parameters;
  - call Servo's start/stop/reset services.

## Freshness checks

All use local arrival time (`time.monotonic()`); none reads a message stamp.

| Component | Check |
|---|---|
| mapper / servo bridge / gripper bridges | stale 0.25 s |
| reset_manager | home 8 s, interval 2.5 s |
| Servo (`servo_gz.yaml`) | `incoming_command_timeout` 0.25 s |

The bridge publishes `now()`-stamped zero twists continuously, so Servo's timeout fires only if the bridge process dies.

## Writers to the final topics (no mux or arbitration)

| Topic | Writers |
|---|---|
| `/servo_node/delta_twist_cmds` | servo_command_bridge, keyboard_servo_override, test fake_hand_publisher |
| `/joint_group_velocity_controller/commands` | Servo, reset_manager (Servo is stopped first, but a failed stop does not abort) |
| `/hande_position_controller/commands` | gripper bridge, reset_manager (concurrent during reset) |
| upstream inputs | `/target_twist_states` and `/received_pose_states` also have optional/debug writers |

The only "arbitration" is that the lifecycle script kills one node before starting another.

## Where a minimal fix would go

- **(a) Receipt time, producer seq and session:**
  - add the fields to `ReceivedPoseStates.msg` and `TargetTwistStates.msg`;
  - fill them in the receiver;
  - store and copy them in the mapper `_on_pose_states` / `_publish_loop` (L1058–1076) instead of using `now()`;
  - stamp in `servo_command_bridge._publish_loop` (L135–150).
  - Past Servo, the Float64MultiArray has no header, so end-to-end transport needs a side topic or another
    `command_out_type`.
- **(b) Neutral vs. motion:**
  - branch on `source` or an explicit reason in mapper L764–772 / L866–870;
  - carry a reason/neutral field in TargetTwistStates through the bridges.
  - Whether a timeout should re-anchor is a separate policy decision.
- **(c) Single writer:** a mux, or an explicit hand-off in reset_manager (`_run_reset_sequence` L545–616) and
  keyboard_servo_override.

## Consequence for R20

R20 fixed only the receiver hop. On this backend the provenance would be lost again at the mapper. The neutral
reason is lost at the mapper as well. The arm and gripper controller topics each have more than one writer, so the
R22-style single-writer premise does not hold here.
