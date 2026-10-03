# A04 — Trust-boundary map for M12D / M17 / M18 / M19, and the M18 code audit (2026-10-04)

**Basis.** This audit draws on:

- pinned Monado 045931d (read inside the research image `f3-xrizer-bgpump:0989a7f-v3`, `/src/monado`);
- the Docker_Teleop audit A05;
- R13/R19/R20/R22/R25;
- a socket-permission probe (`A04_probe/`; own echo server, not Monado; no DoS);
- the design I05 (`semantic_evidence_framework/docs/07`).

**Not executed against Monado:** no libmonado control call, no crash reproduction.

**Naming.** "S2" below always means the *threat class* (a compromised component with legitimate rights). The R19 arm
called "S2" was a gate placement, not a defense against this class.

## 1. Attacker capabilities (kept separate; no result is extended across rows)

| ID | Capability | Controls | Does not control (premise) |
|---|---|---|---|
| A-net | **network attacker without keys** | packets on reachable networks: the remote-driver TCP port, DDS without security, the Docker_Teleop TCP receiver | process memory, keys, local files |
| A-app | **compromised app with the normal app key and app-process rights** (threat class S2) | everything the app process can do: its OpenXR/IPC connection to the runtime, its ROS topics and permissions, its claimed metadata (stamps, seq, session, provenance, names), any file or socket its uid can open | other uids' keys and files; root |
| A-rt | **compromised runtime/driver** | everything the runtime reports: poses, validity, sample times, client state, receipt evidence | — (no observation from the runtime can be trusted) |

## 2. Components, evidence and who can modify it

| Component (trusted?) | Evidence it produces | Who can modify it under A-net | under A-app | under A-rt |
|---|---|---|---|---|
| Source / headset (trusted only if the sensor is) | the physical sensing | — | — | yes |
| Monado remote driver | `latest` pose and receipt time (R19 variant) | **yes**: the driver binds `INADDR_ANY:4242` (`r_hub.c` L189–202) with no authentication, so any reachable peer can feed poses | yes, if it can reach the port | yes |
| monado-service (runtime) | client state flags, poses at a predicted time, IO blocks | via A-net's driver input | **yes, state**: see §3. Setters and observers share one socket with no authorization. | yes |
| App (A-app) | app read time, generation time, seq, `represented_at`, the command target | — | yes (all of it) | indirectly (its inputs) |
| Receiver / mapper (Docker_Teleop) | receipt time and count (R20 edit); mapper anchor, scale and mode | A-net via the unauthenticated TCP receiver | A-app if it can publish `/received_pose_states` or `/target_twist_states`, or set mapper parameters (A05) | — |
| Gate / verifier (trusted, separate uid) | admit/deny decisions; its own receipt clock | — | only through its inputs | through the runtime inputs |
| Final writer (mux) and controller | the last command; the controller state | — | only if the app can write the controller topic (M19) | — |

## 3. M18 — runtime identity and control authority (pinned code facts)

| Question | Fact (045931d) | Consequence |
|---|---|---|
| Client name/PID | **Self-reported.** The client fills `desc.info` and `desc.pid = getpid()` (`ipc_client_connection.c` L330–341). The server copies them (`ipc_server_handler.c` L339–343). | A process can claim any application name. libmonado itself announces the name `"libmonado"` (`monado.c` L235). |
| Kernel peer identity | **Not used.** There is no `SO_PEERCRED`/`ucred` in `src/xrt/ipc`. | Nothing binds the runtime client to an OS identity. Probe: `SO_PEERCRED` returns the true uid even when the client claims "monado-ctl-admin". Across PID namespaces the pid reads 0, so **uid is the usable identity**. |
| Observe vs. control separation | **None.** libmonado read calls (`mnd_root_get_*`) and setters (`mnd_root_set_client_primary`, `toggle_client_io_active`, `set_client_io_blocks`, `recenter_local_spaces`, `set_reference_space_offset`, `set_tracking_origin_offset`, `set_device_brightness`, …) all connect through `ipc_client_connection_init` (`monado.c` L237) to the **same app socket**. The server handlers `ipc_handle_system_toggle_io_client`, `set_client_io_blocks`, `set_primary_client`, `space_set_*_offset` and `space_recenter_local_spaces` have **no authorization check** (`ipc_server_handler.c` L1563–1606, L916–965). `set_focused_client` is UNIMPLEMENTED in this version (L1573–1578). | Any process that can open the app socket can change other clients' IO state, the primary client and the space offsets. Under A-app this means **the runtime state is not an independent source of truth**. |
| Socket permissions | `bind()` on `$XDG_RUNTIME_DIR/monado_comp_ipc` with **no chmod** (`ipc_server_mainloop_linux.c` L92–124). The mode follows the service's umask. | Access is decided by the file mode and the uid only. |
| Does a read-only mount block control RPC? | **No.** Probe: with the socket directory mounted `:ro`, root (owner) connected (0755 and 0777), and uid 2001 connected when the mode was 0777. uid 2001 was refused (`EACCES`) only when the mode was 0755. | `connect()` needs write permission on the socket inode, not a writable mount. A read-only mount is **not** a control boundary. A separate uid plus the socket mode is. That blocks the app from the runtime entirely, because the same socket carries OpenXR. |
| Remote driver input | TCP on `INADDR_ANY:4242`, no authentication (`r_hub.c` L189–202; port `target_builder_remote.c` L130–133). | A-net (where reachable) and A-app can inject poses. A source-side trust premise is required. |

**Judgment.** On this unmodified runtime the "trusted runtime evidence" premise does not hold against A-app. The app
can reach the control calls on the socket it must use for OpenXR, and the service cannot tell the clients apart beyond
self-reported names.

- **The I05 R1/R2 remedies remain unimplemented** here:
  - a separate admin endpoint gated by uid;
  - `SO_PEERCRED`-based binding.
- **The trusted-mapper and ACL results (R28, R29) assume these are fixed or out of reach.** They do not establish a
  full S2 defense.
- No crash or DoS was re-run.

## 4. What authentication vs. semantic validation guarantees

| Mechanism | Guarantees | Does not guarantee |
|---|---|---|
| SROS2 / DDS-Security (R27/R29) | only identities holding a permitted key can create a writer on a topic, so **who may write where** | that what a permitted writer sends is true or derived from the input (A-app keeps its key and its permitted topic) |
| Freshness / seq / validity checks on app fields (R13, R28 AP) | an honest app's message is fresh and ordered | anything against A-app: the fields are the app's own claims |
| Trusted verifier / mapper outside the app (R28 TV) | the admitted target equals the declared mapping of a recent source sample that the verifier itself received | correctness of the source (A-rt, A-net on the driver port); the verifier's own calibration/task state; replay of a different recent sample within τ |
| Runtime attestation of samples (I05 R3, not implemented) | "a sample existed" | "this command was derived from it" |

## 5. Times and identifiers (what each one actually is)

| Quantity | Produced by | Means | Modifiable by A-app |
|---|---|---|---|
| sensing time | sensor/driver (not exposed on this path; R13) | the physical observation | no (A-rt yes) |
| driver receipt time | driver (R19 variant) | when a packet arrived | no |
| app read time / generation time (`represented_at`) | app | when the app read or produced the value | **yes** |
| transport `header.stamp` | the last publisher | when the message was (re)published | **yes**, and any republisher |
| seq / session | producer or app | order and identity, as claimed | **yes**, if the app produces them |
| receiver receipt time / count (R20) | receiver | packet arrival at that hop | no, if the receiver is trusted |

## 6. Ownership of the source↔command link and the task state

- **Source → command link.**
  - On the Monado/xrizer path the app alone holds it: the sample → command mapping happens inside the app, and the
    legacy API exposes no sample id.
  - A verifier outside the app needs:
    - an independent copy of the source stream. On Monado that means the same unauthenticated IPC (§3) or a
      separate driver tap.
    - a sample identifier the app must echo;
    - the declared mapping.
- **Calibration / anchors / task mode.**
  - Docker_Teleop: private to the mapper, retriggered by input fields, parameters and enable edges (A05).
  - UR5e app: private to the app.
  - A trusted verifier must **own or independently reproduce** this state, or else the check reduces to the app's
    word.

## 7. Bypassable final execution paths (UR5e Servo path / Docker_Teleop)

| Path | Who can use it today | Mediation tested |
|---|---|---|
| Controller trajectory topic | any ROS participant without security (R22: direct hold writers; A05: several writers) | R27/R29: SROS2 topic ACL blocks the app's writer when restricted |
| JTC action `follow_joint_trajectory` | any participant | not tested |
| Servo services (pause, start/stop, command type) | any participant (A05: reset_manager and others call them) | not tested |
| controller_manager services (switch/load controllers) | any participant | not tested |
| Docker_Teleop velocity/gripper controller topics | Servo, reset_manager, gripper bridge (A05) | none (no mux) |
| Runtime control over the IPC socket (§3) | any process that can open the socket | none |
| Remote-driver TCP port 4242 | any reachable peer | none |
