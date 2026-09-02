# Decisive Follow-up Evidence Summary

## Scope

- Test date: 2026-08-26 (Asia/Seoul)
- Decision: **CONDITIONAL GO**
- Runtime: ROS 2 Jazzy, Docker 29.1.3, image `ros-xr-horus-jazzy:local` (`sha256:77e3a03de666...`)
- Isolation: Docker `--network none`; bridge, backend, dummy action server, and MQTT broker bound to container loopback; no privileged mode, public port, Quest, or physical robot
- HORUS configuration: 32 s dummy `NavigateToPose`, revocation after 2 s, 1200 ms lease TTL, checkpoints at 0.5/1/3/5/10 s, 0.25 s feedback, software-only 0.1 m/s distance model

## Fixed revisions

| Component | Revision |
|---|---|
| HORUS ROS 2 | `eca75cbf559f09ff793d8993338b2f1ffed1adfd` |
| HORUS | `819cdfdc74f1a0c2bd73946dc14897a533f68b61` |
| HORUS SDK | `f4f00dab41910676519d545515531ec243414044` |
| COMPAS XR | `b86e6fbbacdc8e84183fc08c846176a1c79304ca` |
| COMPAS XR Unity Assembly | `f1516ca568b101447507aebc28a594bdc358df3e` |

## Unmodified HORUS runtime

| Case | Complete | Cancel callbacks | State at 10 s | Post-revocation active time | Modeled additional distance | Outcome |
|---|---:|---:|---|---:|---:|---|
| Explicit cancel | 5/5 | 5 | `CANCELED` | n/a | n/a | Same Goal UUID canceled; callback 1.403–18.571 ms, terminal 10.052–57.937 ms |
| R1 release | 5/5 | 0 | `EXECUTING` | 10.000063–10.002296 s lower bound | 1.000006–1.000230 m | Continued at every checkpoint |
| R2 TTL expiry | 5/5 | 0 | `EXECUTING` | 10.000068–10.000172 s lower bound | 1.000007–1.000017 m | Continued at every checkpoint |
| R3 disconnect | 5/5 | 0 | `EXECUTING` | 10.000044–10.000076 s lower bound | 1.000004–1.000008 m | Continued at every checkpoint |
| R4 handoff | 5/5 | 0 | A and B both `EXECUTING` | A: 10.000059–10.000643 s lower bound | A: 1.000006–1.000064 m | B accepted in 62.712–70.274 ms; max active goals 2 |

All 25 unmodified trials completed with clean action/lease cleanup and successful backend robot unregistration. The distance values are a constant-speed software model, not physical motion.

## Test-only minimal hook

The temporary source copy published robot-wide `/robot1/goal_cancel` on release, TTL expiry, and disconnect. It was never applied to the fixed checkout.

- Nominal R1/R2/R3: immediate cancel in 5/5 each.
- Nominal R4: A canceled and B remained executing in 5/5.
- Selectivity challenge: **5/5 `WRONG_LATEST_GOAL_CANCELLED`**. The later unrelated ROS-side Goal UUID was canceled, while A's lease-owned Goal received zero cancels and remained active for at least 10 s.
- Conclusion: a robot-wide/latest-handle hook demonstrates cancel coverage but is not an ownership-safe fix. A production fix needs connection/owner, lease epoch, robot, command, and Goal UUID binding plus pending/active lifecycle handling.

## Second action

Not run. The fixed public HORUS backend contains one action adapter, `NavigateToPose`. Waypoint/path and takeoff/land are topics, and `ExecuteCommand` is not a long-running action executor. Inventing another vulnerable adapter would not test the official path.

## COMPAS XR executor boundary

- Probe verdict: `PASS_CASE_C`.
- Official packaged component and shipped GHX subscribe to `SendTrajectory` but expose only element/robot outputs; the GHX leaves RRC/RTDE/UR Script control as a user placeholder.
- T_A and T_B had different canonical digests but the same element-derived `trajectory_id`; `SendTrajectory` carried no approval digest, version, approver set, or authorization epoch.
- No reproducible public official/representative executor was found in the searched repository, documentation, organization, and paper-artifact paths.
- Classification: **Case C — Framework Guarantee Missing / Physical Execution Unconfirmed / Main Item Secondary Evidence Only**. T_A→T_B robot-input execution was deliberately not fabricated.

## Integrity and cleanup

- HORUS revocation log SHA-256: `5131d0052686767f8554538221a3b3dffd74a0b2264f06457e80abefa9677619`
- HORUS handoff/fix log SHA-256: `c1159375057c1be3e448635995d85da37d9dc70aecd785ea5e79b27961128ba5`
- COMPAS validation log SHA-256: `56bd843ce780c16f3b34b014a09bfcee8e40e6b35b9b1d5cc6981ec65f5fa17b`
- All retained suites ended with `rc=0`; no `ros-xr-followup-*` container remained.

## Evidence

- [Full follow-up report](/home/cclab/ros_xr/DECISIVE_FOLLOWUP_RESULTS.md)
- [HORUS revocation log](/home/cclab/ros_xr/evidence/horus_revocation_longrun.log)
- [HORUS handoff and fix log](/home/cclab/ros_xr/evidence/horus_action_handoff.log)
- [COMPAS executor validation log](/home/cclab/ros_xr/evidence/compas_executor_validation.log)
- [Reproduction runner](/home/cclab/ros_xr/authorization_env/run_decisive_followup.sh)
