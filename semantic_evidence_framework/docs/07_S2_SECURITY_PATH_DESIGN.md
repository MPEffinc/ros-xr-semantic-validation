# 07 — Design: what defending against a compromised app (S2) would require (design only, 2026-10-02)

**Status.** This is a design document. Nothing here is implemented.

- No large security framework is built until two things are confirmed: real-app applicability, and
  the linkage premises (`results/F2_TIMESTAMP_REVIEW.md`).
- **Adversary S2** is an app with legitimate ROS send rights on its command topic and a normal
  OpenXR runtime connection (`experiments/F1_independent_evidence/SECURITY_SCOPE.md`).

**Principle.** No single patch establishes the defense. Each of the five requirements below closes a
different bypass, and the guarantee holds only if all of them hold together.

## R1 — Runtime control authority

| | |
|---|---|
| **Gap** | libmonado's state-changing calls (`set_client_focused`, `toggle_client_io_active`, `set_client_io_blocks`, `set_reference_space_offset`, `recenter_local_spaces`, …) travel over the same IPC socket that every OpenXR app uses. They are unauthenticated: any app can change its own IO blocks and focus. |
| **Needed** | Split the IPC endpoint into an *app* endpoint (OpenXR only) and a *control/observe* endpoint. The control endpoint is reachable only by an administrative uid, enforced by socket permissions or by checking `SO_PEERCRED` in the service. The read-only observe calls used by the collector are separated from setters. |
| **Cost** | A runtime modification, reported separately from unmodified-runtime results. |
| **Residual** | A compromised app can still *lose* focus or IO on purpose. That is a safe direction. It can also misuse legitimate OpenXR calls (e.g. request exit). |

## R2 — Unforgeable client ↔ sender binding

| | |
|---|---|
| **Gap** | The runtime client's name and pid are self-reported (`ipc_client_connection.c` L333–340). The ROS publisher identity, i.e. node name or DDS GUID, is not tied to an OS identity unless SROS2 is used. |
| **Needed** | (a) The service records the **kernel-attested** peer credentials (`SO_PEERCRED`: pid/uid/gid) of each client connection and exposes them on the observe endpoint. (b) The ROS sender is authenticated with SROS2 (per-identity certificates and topic permissions), and the identity is mapped by the deployment to the uid that runs the XR client. (c) The gate admits commands on topic *T* only while the runtime client with the *configured uid* (not a configured name) satisfies the evidence predicate. |
| **Residual** | Two processes under the same uid cannot be told apart, so one app per uid is a deployment requirement. |

## R3 — Trust range of command time and provenance

| | |
|---|---|
| **Gap** | A compromised app chooses `header.stamp`, so interval checks bound nothing against S2. |
| **Achievable without app trust** | **Receive-time state only.** The gate checks runtime evidence at its own receive time R, using its own clock. Commands arriving while the bound client is inactive are blocked. Commands minted while active are admitted whatever their content. |
| **Beyond that** | Sample-level provenance would need the runtime to *attest* samples: for example, the runtime signs (sample time, client id, sequence) for poses and actions it hands to the client, and the app must forward that token in the command. A compromised app can still replay a valid token inside its validity window, or apply its own transform to the pose. A token proves "a sample existed", not "this command was derived from it". This is **not** proposed as solved. |

## R4 — Evidence channel and process privilege separation

| | |
|---|---|
| **Needed** | The collector, gate and consumer run under uids that differ from the app's. The evidence channel (FIFO or unix socket) is writable only by the collector's uid. The gate fails closed when evidence is stale (> 50 ms), as F1/F2 already do. The app's uid has no access to the collector, gate or consumer processes (no ptrace, no shared files). |
| **Pilot status** | Everything runs in one container under one uid, so this is **not** enforced. |
| **Availability** | A local IPC client can crash `monado-service` with one libmonado query (F1 bring-up §1). Under fail-closed that is a denial of service, not an unsafe pass. Fixing it is a runtime robustness change. |

## R5 — Gate bypass prevention

| | |
|---|---|
| **Gap** | If the app can publish to the consumer's input topic, for example `/servo_node/pose_target_cmds`, or call consumer services (`pause_servo`, `switch_command_type`) or controller topics directly, the gate is bypassed. |
| **Needed** | SROS2 permissions: the app may publish only to the gate's input topic, and only the gate may publish to the consumer. Controller-level topics and services are denied to the app. Latched or `TRANSIENT_LOCAL` overrides of the kind seen in OpenArmX (A6) are denied by permission. |
| **Residual** | Any other path to the actuators, such as a direct hardware or driver interface, must be outside the app's reach. That is an OS/deployment property. |

## Order of work, if this direction is pursued

1. First establish one functional real app, under the receive-time-state claim (S1).
2. Then add R4 and R5. Both are deployment-only: uids and SROS2.
3. Then R1 and R2, which are runtime modifications.
4. R3 beyond receive time stays a research question.
