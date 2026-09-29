# Docker_Teleop bag joint-state extraction

## Method

The existing SQLite3 ROS bag was read directly, without playback or a new runtime trial.  `extract_joint_state.py` decodes the CDR payloads for all four recorded types and segments them using the exact receiver signatures emitted by `docker_teleop_tcp_trials.py`: `(tracked, pose.x, teleop)`.

The end-effector calculation uses the fixed and actuated chain from the pinned generated `UnityApp/Assets/Robots/ur5e.urdf`, ending at `robotiq_hande_end`.  It is derived from the recorded joint positions; no `/tf` topic was present in this bag.

Reproduction:

```bash
python3 semantic_validation/results/runs/docker_teleop_e2e_20260914/extract_joint_state.py \
  semantic_validation/results/runs/docker_teleop_e2e_20260914/bag/docker_teleop_e2e_bag_0.db3 \
  semantic_validation/results/runs/docker_teleop_e2e_20260914/joint_state_extraction.json
```

Input DB SHA-256: `43537a60d205cefc3d95a9f751eb02010ce852b27c3c8b099ccb5379270a1fea`.

## Quantitative result

| Phase | Bag-relative receiver interval (s) | Joint samples | Arm consequence | URDF-derived Hand-E end displacement |
|---|---:|---:|---|---:|
| D1 reference (`tracked=true`, `x=0.10`) | 2.594444–3.177738 | 36 | maximum arm `|delta q|` `4.24e-11 rad` | `1.88e-11 m` |
| D1 active (`tracked=true`, `x=0.35`) | 3.194349–5.177652 | 119 | lift `+0.375777 rad`; elbow `-0.553998 rad`; wrist 1 `+0.178478 rad` | `0.134070 m` |
| D2 tracked false (`tracked=false`, `x=0.35`) | 5.194357–6.577724 | 83 | maximum arm `|delta q|` `1.52e-10 rad` | `8.19e-11 m` |
| D3 stall neutral (`tracked=false`, `x=0`, `teleop=false`) | 6.594472–6.977709 | 25 | maximum arm `|delta q|` `4.46e-11 rad` | `2.40e-11 m` |
| D4 old source time (`tracked=true`, `x=0.45`) | 6.994658–7.894328 | 55 | maximum arm `|delta q|` `1.00e-10 rad` | `5.39e-11 m` |
| D5 second client (`tracked=true`, `x=0.55`) | 8.061005–8.944337 | 53 | maximum arm `|delta q|` `9.67e-11 rad` | `5.19e-11 m` |

D1 arm peak recorded velocities were `+0.640782 rad/s` (shoulder lift), `-0.848557 rad/s` (elbow), and `+0.208054 rad/s` (wrist 1).  Its end displacement vector in the URDF base frame was `[+0.13406954, -2.9e-12, -7.19e-05] m`.

The first D2 joint sample is shared with the command transition and still reports deceleration (`0.0563`, `-0.0939`, and `0.0375 rad/s` on the three moving joints).  After excluding the first six samples (approximately 0.1 s), maximum absolute arm velocity was `1.09e-10 rad/s`.  The same guarded maximum was `1.09e-10 rad/s` during the D3 neutral window.  Thus D2/D3 are supported as halt/neutral consequences after transition settling, rather than an instantaneous zero-inertia claim.

D4 and D5 each captured a new mapper reference and emitted no non-zero servo command in the bag.  Their stationary joint results therefore show the observed reference-capture consequence; they are not tests of motion after the new reference.

## Evidence boundary

This is quantitative `E2 SYNTHETIC_RUNTIME` evidence from the native Gazebo/MoveIt Servo joint-state output already recorded in the run.  It establishes simulated actuation for D1 and simulated halt for D2/D3.  The end position is a deterministic offline FK reconstruction from recorded joints and the pinned URDF, not a directly recorded TF sample.  It does not add Quest hardware or physical-robot evidence.
