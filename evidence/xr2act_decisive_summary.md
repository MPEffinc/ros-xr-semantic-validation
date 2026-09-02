# XR2Act Decisive Evidence Summary

## Decision

- Final item decision: `WEAK / CASE-STUDY ONLY`.
- Track A: `Framework delegates final robot execution to custom integration`; T_B reached the official handoff but final robot/executor input remains unconfirmed.
- Track B: official B cancel succeeded `3/70`; post-handoff interference confirmed `67/70`.
- Ordering discriminator: cancel before A-result publication succeeded `3/7`; cancel after publication succeeded `0/63`.
- Exact-UUID rescue after official-path failure: `67/67`.
- Track C: `UNCONFIRMED_REAL_THREAT_BOUNDARY_UNAVAILABLE`; no synthetic roles or ACL omissions were introduced.
- Track D: safe-oracle discrimination `True`.

## Track A — COMPAS

- Fixed source audit: `PASS_CASE_C`.
- Credential-authenticated local broker: `True`.
- T_A normal handoff: `True`.
- A1/A2 T_B official subscriber acceptance: `True`.
- A3 cross-robot official subscriber acceptance: `True`.
- A4 stale approval official subscriber acceptance: `True`.
- Final actuator/executor command: `UNCONFIRMED`; the shipped official example stops at a custom integration boundary.

## Track B — HORUS

- Run ID: `xr2act-horus-20260827T044120Z`.
- Completed: `80/80`.
- `direct_result100`: complete `10/10`, official success `0`, direct exact success `10`, outcomes `{"NEGATIVE_CONTROL_DIRECT_EXACT_CANCEL_PASS": 10}`.
- `official_accept0`: complete `10/10`, official success `2`, direct exact success `8`, outcomes `{"B_OFFICIAL_CANCEL_SUCCEEDED": 2, "POST_HANDOFF_B_CANCEL_INTERFERENCE_CONFIRMED": 8}`.
- `official_accept5`: complete `10/10`, official success `1`, direct exact success `9`, outcomes `{"B_OFFICIAL_CANCEL_SUCCEEDED": 1, "POST_HANDOFF_B_CANCEL_INTERFERENCE_CONFIRMED": 9}`.
- `official_result0`: complete `10/10`, official success `0`, direct exact success `10`, outcomes `{"POST_HANDOFF_B_CANCEL_INTERFERENCE_CONFIRMED": 10}`.
- `official_result10`: complete `10/10`, official success `0`, direct exact success `10`, outcomes `{"POST_HANDOFF_B_CANCEL_INTERFERENCE_CONFIRMED": 10}`.
- `official_result100`: complete `10/10`, official success `0`, direct exact success `10`, outcomes `{"POST_HANDOFF_B_CANCEL_INTERFERENCE_CONFIRMED": 10}`.
- `official_result50`: complete `10/10`, official success `0`, direct exact success `10`, outcomes `{"POST_HANDOFF_B_CANCEL_INTERFERENCE_CONFIRMED": 10}`.
- `official_result500`: complete `10/10`, official success `0`, direct exact success `10`, outcomes `{"POST_HANDOFF_B_CANCEL_INTERFERENCE_CONFIRMED": 10}`.

## Track C — Authenticated Scope

- `UNCONFIRMED_REAL_THREAT_BOUNDARY_UNAVAILABLE`.
- Reason: No inspected public XR-ROS/shared-bridge implementation simultaneously provided verified distinct credentials, credential-bound Robot/Action scopes, and a shared downstream ROS authority. Creating roles or omitting an ACL would be an artificial testbed.

## Negative Control

- COMPAS exact digest/robot/epoch/approver reference rejected all T_B variants: `{'classification': 'TEST_ONLY_REFERENCE_EXECUTOR_NOT_COMPAS_FEATURE', 'normal_t_a_allowed': True, 'same_id_t_b_rejected': True, 'cross_robot_t_b_rejected': True, 'stale_epoch_t_b_rejected': True}`.
- Direct exact Nav2 UUID cancellation: `{'trials': 10, 'complete': 10, 'success': 10, 'classification': {'NEGATIVE_CONTROL_DIRECT_EXACT_CANCEL_PASS': 10}}`.

## Evidence Integrity

- `/home/cclab/ros_xr/evidence/compas_e2e_execution.log` SHA-256 `d37fe97ce0704316d5d4aa4d75f71a26bf8c83afeb8499827aaaad25a4d5d1e1`
- `/home/cclab/ros_xr/evidence/horus_post_handoff.log` SHA-256 `f3ebf9edcac191faf9b3cea71c125a93f81aa237f07a05a5f56f24c9a76f9380`
- `/home/cclab/ros_xr/evidence/bridge_scope_bypass.log` SHA-256 `36bc6182235df8d71a18c4a5110099cbddeef740dfd4efb0df1008bbdff81a36`
- `/home/cclab/ros_xr/evidence/negative_control.log` SHA-256 `36f16f781873baaf7011b2b7ea5d2c1e1cc95e84988e1331f7c736d1165461d6`
