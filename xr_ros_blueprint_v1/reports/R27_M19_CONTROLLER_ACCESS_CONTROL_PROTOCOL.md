# R27 — M19: direct controller-topic writes and SROS2 access control (protocol; frozen before formal runs)

**Question.** Can an XR-app process holding a **valid key** write the final controller topic directly, bypassing the
mapper/mux? Does a restricted DDS-Security permission prevent this, while the approved path and the trusted writer
keep working?

**Scope.** Access control on the **final controller topic only**. Actions, services, runtime management and source
paths are outside this test. This is not a full S2 defense.

## 1. Installed support (checked before running)

- Image `m3-ordering-mux:v1` (the existing research image; no new image, no host change) contains:
  - ROS 2 Jazzy, `rmw_fastrtps_cpp`, Fast DDS 2.14.6 with the builtin security plugins (PKI-DH, Access-Permissions
    strings present);
  - `sros2`;
  - `controller_manager` 4.48.0, `joint_trajectory_controller`, `joint_state_broadcaster`;
  - `mock_components/GenericSystem`, `topic_tools`, `setpriv`.
- Reference: ROS 2 DDS-Security integration design (L05).
- **Controller:** real JTC on **mock hardware** (6 UR joints; the mock state follows the commanded positions). There is
  no Gazebo or robot. The question concerns topic reachability, not dynamics.

## 2. Roles, identities and uids (each process: its own enclave, its own uid, `ROS_SECURITY_ENABLE=true`, `ROS_SECURITY_STRATEGY=Enforce`)

| Role | Enclave | uid | What it does |
|---|---|---|---|
| XR app | `/m19/app` | 2001 | publishes the declared frontend input `/m19/app_cmd` |
| mapper/mux (trusted writer) | `/m19/mux` | 2002 | `topic_tools mux` `/m19/app_cmd` → `/ur5_arm_controller/joint_trajectory` |
| controller | `/m19/controller` | 2003 | robot_state_publisher, ros2_control_node, JTC `ur5_arm_controller`, joint_state_broadcaster |
| observer (trusted) | `/m19/observer` | 2004 | records the controller topic, the app topic, JTC `controller_state` and `/joint_states` |

**Keystores** (`harness/keys.sh`; one per deployment). They are created once per snapshot in the ignored
`run_snapshot/<sha>/keys` directory and never printed.

- Each enclave directory is owned by its process uid with mode 0700, and `key.pem` has mode 0600.
- The CA private keys are root-only.

| Deployment | App permissions |
|---|---|
| **D_OPEN** | the sros2 default enclave permissions (allow `rt/*`, `rq/*`, `rr/*`): a valid app key that may publish anywhere |
| **D_RESTRICT** | generated from `policies/app_restricted.xml`: publish only `m19/app_cmd`, `rosout`, `parameter_events`; subscribe `parameter_events`; reply on its own `get_type_description` service. Everything else is denied by default. |

The other enclaves use the default permissions in both deployments.

**Transport.**

- DDS domain 0, because the sros2 permissions are generated for domain 0.
- `FASTDDS_BUILTIN_TRANSPORTS=UDPv4` with discovery range SUBNET, inside `--network none` (loopback only).
- Pre-flight probe: the default shared-memory transport delivered **0 messages between different uids** (same uid:
  49/49). A uid-separated deployment therefore needs a transport choice.

## 3. Checks (same payload in every check)

**Payload:** one JointTrajectory point equal to the start pose + 0.20 rad on `shoulder_pan_joint`, with
`time_from_start` 1.0 s. It is repeated at 10 Hz for 2 s after the first match, because `topic_tools mux` subscribes
only after it discovers the input type.

| Check | Publisher |
|---|---|
| APPROVED | app (uid 2001, `/m19/app`) on `/m19/app_cmd` → mux → controller |
| APP_DIRECT | app (uid 2001, `/m19/app`) directly on `/ur5_arm_controller/joint_trajectory` |
| MUX_DIRECT | the trusted writer identity (uid 2002, `/m19/mux`) directly on the controller topic. This is the **positive control** with the identical payload. |

2 deployments × 3 checks × 3 = **18 formal trials** (`schedule_acl.csv`).

## 4. Evidence and measures (`analysis/analyze_acl.py`)

- **Enforcement probe (every trial):** a node with security enabled but no enclave must fail to initialise.
  Otherwise the trial is invalid (`security_not_enforced`). A Permissive or disabled run is never counted as access
  control.
- **Key access probe:** whether uid 2001 can read the mux key, the controller key and the CA private keys.
- **Publisher API result:**
  - create_publisher ok/failed, matched readers, messages sent.
  - This is **not** delivery evidence.
- **Delivery and effect, from the trusted traces:**
  - payload seen on the controller topic by the observer;
  - JTC `controller_state` reference reaching the payload;
  - `/joint_states` reaching it (within 0.01 rad).
  - `reached_controller` = reference or joints.

**Invalid:** setup failure, no joint states, or security not enforced. Reruns: invalid only, at most 2.

**Expected reading (fixed):**

- APP_DIRECT reaches the controller under D_OPEN but not under D_RESTRICT.
- APPROVED and MUX_DIRECT reach it under both.
- Any other pattern is reported as observed.

## 5. Pre-flight (excluded; snapshots 6ae3d38 → 8bd6465; 07:44–08:01)

| Runs | Problem found → change before freeze |
|---|---|
| PF1 | the sros2 permissions grant domain 0 only (trial used domain 91) → domain 0 |
| PF2–PF4 | controller_manager 4.48 waits for the `robot_description` topic → robot_state_publisher added; the spawner hung → `timeout`; two leftover trial containers stopped; runners now kill timed-out containers by name |
| PF5–PF7 | under D_RESTRICT the app node failed to start (Jazzy type-description service) → service reply allowed for the app's own node; the observer received nothing |
| PF8–PF11, probes d1–d4 | cross-uid delivery over the default SHM transport = 0 → UDPv4 + SUBNET range (probe: cross-uid 49/49) |
| PF12–PF15 | a single payload message was missed by late-matching readers or the mux → repeat 10 Hz × 2 s |
| PF16–PF19 | D_RESTRICT APP_DIRECT: `create_publisher() could not create data writer` and joints unchanged. D_RESTRICT MUX_DIRECT, D_OPEN APP_DIRECT and D_RESTRICT APPROVED: payload on the controller topic, JTC reference and joints at +0.20 rad. |

In every run, uid 2001 was denied reading the mux key, the controller key and the CA private keys.

## 6. Limits

- Topic ACL at one boundary on mock hardware.
- **Not tested:**
  - JTC action/services;
  - Servo or controller_manager services;
  - parameters;
  - other DDS domains;
  - non-ROS paths (hardware drivers, the Monado IPC socket, the remote-driver port).
- A process running as the trusted uid, or root, could use the trusted keys. The result holds only while key files
  stay outside the app's uid.
- **A restricted app can still send arbitrary content on its permitted topic.** Authentication does not establish
  semantic correctness (M17, R28).
