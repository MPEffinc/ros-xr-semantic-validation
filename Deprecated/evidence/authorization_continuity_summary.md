# Authorization Continuity Evidence Summary

## Scope and boundary

- Test date: 2026-08-26 (Asia/Seoul)
- Question: whether XR-side authorization preserves **Identity**, **Lifetime / Revocation**, and **Exact Action Binding** through a bridge and downstream robot action path.
- Track A: fixed-source HORUS ROS 2 runtime with the real bridge, backend/Nav2 adapter, a HorusLink-compatible local client, and a dummy `NavigateToPose` action server.
- Track B: fixed-source COMPAS XR message classes and `compas_eve` MQTT transport, a loopback-only Mosquitto broker, source-faithful Unity state assertions, and an inert audit sink.
- No Quest, physical robot, public broker, external port, privileged container, SROS2 bypass, or defense implementation was used.

## Fixed revisions

| Component | Repository | Branch | Revision | Commit date |
|---|---|---|---|---|
| HORUS ROS 2 | `https://github.com/RICE-unige/horus_ros2.git` | `main` | `eca75cbf559f09ff793d8993338b2f1ffed1adfd` | 2026-07-26 17:58:10 +0200 |
| HORUS app artifacts/docs | `https://github.com/RICE-unige/horus.git` | `main` | `819cdfdc74f1a0c2bd73946dc14897a533f68b61` | 2026-08-07 12:51:12 +0200 |
| HORUS SDK | `https://github.com/RICE-unige/horus_sdk.git` | `main` | `f4f00dab41910676519d545515531ec243414044` | 2026-07-26 17:58:04 +0200 |
| COMPAS XR | `https://github.com/compas-dev/compas_xr.git` | `main` | `b86e6fbbacdc8e84183fc08c846176a1c79304ca` | 2026-03-27 11:45:46 -0400 |
| COMPAS XR Unity Assembly | `https://github.com/compas-dev/compas_xr_unity_assembly.git` | `main` | `f1516ca568b101447507aebc28a594bdc358df3e` | 2024-11-01 15:54:11 +0100 |

## Evidence labels

- **CONFIRMED BY RUNTIME**: asserted by the isolated executable probe and retained log.
- **CONFIRMED BY SOURCE CODE**: directly traced in the fixed source revision.
- **REASONABLE INFERENCE**: follows from runtime and source together, but the exact target deployment was not executed.
- **UNCONFIRMED HYPOTHESIS**: requires Quest, Unity binary, official downstream executor, or physical/simulation validation not present here.

## HORUS results

| Test | Expected / question | Observed | Verdict | Evidence class |
|---|---|---|---|---|
| HORUS-A1 normal lease | A acquire and publish ALLOW; B publish during A lease BLOCK; release then B acquire/publish ALLOW | All four assertions passed. ROS graph exposed one `/horus_unity_bridge` publisher endpoint, not one ROS node per client. | PASS | CONFIRMED BY RUNTIME |
| HORUS-A2 no active lease | Determine ALLOW or BLOCK on a catalog-protected command topic | Command `0.31` was delivered when the topic was protected but no lease existed. Source returns true when no lease entry exists. | ALLOW | CONFIRMED BY RUNTIME + SOURCE CODE |
| HORUS-A3 identity metadata | Determine whether `app_id`, `role`, and `session_id` are authenticated authorization principals | Arbitrary values `self-asserted-app`, `self-asserted-admin`, and `fake-session` were accepted/reflected. Command ownership was keyed by the bridge-issued logical HorusLink connection. | SELF-ASSERTED METADATA; CONNECTION-OWNED LEASE | CONFIRMED BY RUNTIME + SOURCE CODE |
| HORUS-A4 protected catalog | A's lease should block B unless an authoritative catalog source changes protection | B was blocked, then B self-asserted `role=host` with `op=clear`; the same B command `0.44` was delivered. Catalog handler ignores `client_fd` and checks the JSON role string. | CONTROL-PLANE TRUST GAP | CONFIRMED BY RUNTIME + SOURCE CODE |
| HORUS-A5 in-flight action | Determine whether release, TTL expiry, or disconnect cancels an already accepted goal | Three goals were accepted. For explicit release, TTL expiry, and disconnect, the goal remained active during respectively 1.0 s, 0.7 s, and 1.0 s observation windows; the dummy action server saw zero cancel requests. B could acquire afterward. | AUTHORITY LIFETIME NOT PROPAGATED TO ACCEPTED GOAL IN TEST WINDOW | CONFIRMED BY RUNTIME + SOURCE CODE |
| HORUS-A6 OpenXR focus | Determine whether actual focus/session loss revokes control and in-flight action | Public current app repository contains artifacts/docs rather than the matching Unity implementation; no current OpenXR focus-to-lease/action trace could be established. | NOT VERIFIED | UNCONFIRMED HYPOTHESIS |

Important boundary: no-lease ALLOW and catalog behavior are implementation semantics, not by themselves proof of a vulnerability. The strongest result is narrower: the tested lease release paths removed future lease ownership but did not emit cancellation for goals already accepted through the official Nav2 adapter during the bounded observation windows.

## COMPAS XR results

| Test | Expected / question | Observed | Verdict | Evidence class |
|---|---|---|---|---|
| COMPAS-B1 schema / identifier | Determine whether `trajectory_id` uniquely binds content and whether `SendTrajectory` carries approval proof | `trajectory_id` is `trajectory_id_ + element_id`. Different trajectories T_A/T_B had different SHA-256 digests but the same ID. `SendTrajectory` contains header, element, robot, trajectory ID, and trajectory; no approval proof/digest/version/approvers. | NO EXACT-CONTENT IDENTIFIER OR APPROVAL PROOF | CONFIRMED BY RUNTIME + SOURCE CODE |
| COMPAS-B2 official execution path | Trace the object that reaches a robot executor | The public official component is an MQTT `SendTrajectory` handoff subscriber and outputs element/robot metadata; the example leaves controller integration to the user. No fixed-revision ROS/MoveIt/RTDE robot executor exists in the inspected repositories. | CUSTOM-INTEGRATION BOUNDARY | CONFIRMED BY SOURCE CODE |
| COMPAS-B3 T_A approval to T_B handoff | Determine whether framework rejects substituted content | Normal T_A reached the inert sink. After T_A approval, T_B with the same element-derived ID reached the official message/transport subscriber; no automatic digest/equality rejection occurred. This is category C: the framework handoff did not decide, and no robot executed T_B. | SUBSTITUTION REACHES HANDOFF, PHYSICAL EXECUTION NOT VERIFIED | CONFIRMED BY RUNTIME; downstream impact UNCONFIRMED |
| COMPAS-B4 identity / duplicate vote | Determine whether distinct authenticated devices and unique votes are enforced | Two repeated approvals and counter results from one decoded device incremented the source-faithful model by two each; no deduplication. Python `Header.parse` also failed to preserve the encoded identity fields. | IDENTITY / VOTE BINDING ABSENT IN TESTED LOGIC | RUNTIME for official messages and Python parse; SOURCE-FAITHFUL MODEL for Unity counters |
| COMPAS-B5 reconnect/direct handoff | Determine whether prior approval proof is required after producer replacement | A new local MQTT client sent T_B and the inert subscriber received it. The broker was intentionally loopback-only and anonymous, demonstrating lack of framework-level binding, not an official deployment vulnerability. | HANDOFF ACCEPTED; DEPLOYMENT SECURITY UNKNOWN | CONFIRMED BY RUNTIME with explicit limitation |

## Cross-framework finding

The evidence supports a shared research question but not yet a two-framework end-to-end exploit claim:

1. HORUS provides an actual ROS action consequence: lease lifetime and already accepted action lifetime were separate in the tested runtime.
2. COMPAS XR provides an exact-action binding gap at the official messaging handoff: approval state is not carried as verifiable evidence in `SendTrajectory`, but downstream execution is custom and was not run.
3. Quest2ROS2 remains a weaker identity-collapse baseline: external clients share the bridge-side ROS principal, while no authenticated Viewer/Operator boundary exists.
4. The defensible residual invariant is: **an external authority decision must remain bound to an authenticated origin, a live revocation epoch, and one canonical robot action at the final enforcement point**.

Overall decision: **CONDITIONAL GO**. Rename the item away from the generic “Authorization Continuity” claim and focus on **Revocable Exact-Action Authorization for Shared XR–ROS Bridges**.

## Reproduction and integrity

- Reproduce both tracks: `authorization_env/run_authorization_continuity.sh`
- Network isolation: both containers run with `--network none`; HORUS and MQTT listeners bind only to `127.0.0.1` inside the container.
- HORUS runtime log SHA-256: `38e2d19cba27995ca9dbe69e7d39b0a2b93836931679c8ce2f0c9032640832af`
- COMPAS runtime log SHA-256: `cb4a332fc4df464cf3218cbd2cba508b25738c493e6cc1e7aae86ba7204ca829`
- Both retained logs end in `verdict=PASS`.

## Evidence files

- [HORUS runtime log](/home/cclab/ros_xr/evidence/authorization_continuity_horus_runtime.log)
- [COMPAS XR runtime log](/home/cclab/ros_xr/evidence/authorization_continuity_compas_runtime.log)
- [Combined runner](/home/cclab/ros_xr/authorization_env/run_authorization_continuity.sh)
- [HORUS probe](/home/cclab/ros_xr/authorization_env/horus_runtime_probe.py)
- [COMPAS XR probe](/home/cclab/ros_xr/authorization_env/compas_runtime_probe.py)
