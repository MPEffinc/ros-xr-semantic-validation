# PickNik Quest 3 Feasibility Result — 2026-09-17

## Scope and safety

- Framework: `PickNikRobotics/meta_quest_teleoperation@bbaef0762fdb0b429b8ea12a4ca65040748b41dd`
- Path exercised:

```text
Quest 3 OpenXR input
→ staged side-band observer (independent of ROS payload)
→ byte-identical production ROSPublishers.cs
→ ROS-TCP Endpoint
→ /left_controller_odom, /right_controller_odom, /tf
→ robot-free picknik_ros_observer.py
```

- No physical robot, robot driver, MoveIt Pro, actuator, Pi consumer, or
  production `ROSPublishers.cs` modification was used.
- The Unity staging manifest records `publisher_byte_identical=true` and
  `logger_ros_payload_independent=true`.

## Runtime setup

- Quest 3 wireless ADB: `192.168.0.178:5555`.
- Quest application: `com.unity.template.vr`.
- Desktop Wi-Fi endpoint: `192.168.0.3:10000`.
- ROS 2 Humble host-network container: `ROS_DOMAIN_ID=71`,
  `rmw_fastrtps_cpp`, `ros_tcp_endpoint default_server_endpoint` plus
  `picknik_ros_observer.py`.
- Baseline topic rates observed before the transition analysis: left/right
  Odometry and `/tf` each approximately 60 Hz.

## Actual Quest result

The final side-band/observer correlation classified 22 left/right loss
intervals. Sixteen intervals overlapped an application focus, pause, or XR
session condition and are excluded. For the right controller, three remaining
intervals all had:

```text
isTracked=true, trackingState=15
→ isTracked=false, trackingState=0
→ reacquired=true
```

and were classified by `picknik_hw_analyze.py` as
`HW_PICKNIK_UNTRACKED_ROS_CONTINUES`:

| Right-controller invalid interval | Odometry during interval | TF during interval | ROS stamp progression | Distinct ROS transforms |
| --- | ---: | ---: | ---: | ---: |
| 7.917 s | 669 | 952 | 7.911612 s | 1 |
| 3.874 s | 342 | 464 | 3.838758 s | 1 |
| 21.302 s | 1,744 | 2,555 | 21.278419 s | 1 |

This establishes Quest feasibility for the bounded claim: in this actual
Quest/Unity/ROS-TCP run, side-band-observed invalid right-controller tracking
state coincided with continued production `/right_controller_odom` and `/tf`
publication to the robot-free observer.

## Claim boundary

- This is native Quest-to-ROS evidence at the project observer boundary
  (`E5 NATIVE_XR_TO_ROS` scope), not physical robot, driver, or actuator
  evidence.
- It does not establish that a user-performed optical occlusion alone caused
  any particular interval. The result is framed as an actual side-band-recorded
  device state transition, not as a controlled occlusion effect.
- It does not claim that a continuing ROS stream is inherently unsafe; the
  downstream equivalence/revalidation policy remains the research question.
- The full run must retain focus/pause/XR-session exclusions. The 16 excluded
  intervals are not usable as tracking-only evidence.

## Local raw evidence (not committed)

Run root:
`semantic_validation/results/runs/hw_picknik_native_20260917T074600Z/`

| Artifact | SHA-256 |
| --- | --- |
| `hardware_analysis_final.json` | `c0ca90cd480df69f7912452fd12ce958c0f92a6c0eb430ead1248e744c0a3f2d` |
| `sideband_final.jsonl` | `313eaa39ebd4c07df4e3791e943d7bf2fc983971d34ea0de55c0b74bc91de062` |
| `ros_observer.jsonl` | `7e1fdcfd05cd8a85145b33ac9ca1b1b57e852d8852f7383910e0f7bdb171c43c` |

The Quest app and the robot-free endpoint/observer were stopped cleanly after
collection.
