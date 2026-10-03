# R31 — Minimum semantic contract from R13–R30 and A04/A05 (requirements table; no new framework)

**Status.** This is a requirements and conformance table derived from executed results and audits. It is **not** a
system contribution, and no shared implementation was built.

**Evidence labels:**

- **EXEC**: executed in this project (level in brackets);
- **AUDIT**: code audit only;
- **UNVERIFIED**: neither.

## 1. Requirement → produced at → preserved through → checked at → enforced at → trust premise

| # | Requirement | Produced at | Must survive | Checked at | Enforced at | Trust premise | Evidence |
|---|---|---|---|---|---|---|---|
| C1 | **Receipt time** (per hop) and **observation/sensing time** kept apart | sensing: sensor/driver (not exposed on Monado remote/xrizer; R13). Receipt: driver (R19 variant), receiver (R20). | every republisher; Docker_Teleop loses it at the mapper, the Servo bridge and Servo (A05) | gate / verifier with its own clock | before the final writer | the driver or receiver is honest (A-rt false) | EXEC: R19 [real app, synthetic source], R20 [backend]. Sensing time UNVERIFIED (no headset). |
| C2 | **App read / generation time** distinct from the transport `header.stamp` | app | separate field (`represented_at`) through bridges; restamping destroys `header.stamp` meaning (R21) | consumer that transforms or ages | consumer | honest app (A-app can set it) | EXEC: R13, R21, R24/R26 [configured, command level] |
| C3 | **seq / session / source identity** | producer or receiver (not sent by the current Unity sender) | every hop; Docker_Teleop: no field after the receiver (A05) | gate (duplicates, reorder, reconnect) | before the final writer | producer and receiver honest; under A-app only meaningful if independently observed (R30) | EXEC: R13, R20 [backend]; the missing-seq trade-off (fail-closed 506 fresh blocked / fail-open 35/35 duplicates) |
| C4 | **Neutral/stop vs. motion** (timeout neutral ≠ user release ≠ motion) | receiver (`*stale_timeout`), app | mapper and bridges; Docker_Teleop treats a timeout neutral like a release and re-anchors on resume (A05) | gate / mapper | stop path | receiver honest | EXEC: R20 (neutral passed only as stop) [backend]; downstream AUDIT (A05) |
| C5 | **Task time semantics** (H: hold the world target at the representation time; F: follow the frame now) | task/app declaration | carried with the command or fixed per interface | converter (tf time choice) | converter | the declaration is correct | EXEC: R21, R26 [configured command level]. Freshness admission ≠ time-correct transform (R26). |
| C6 | **Freshness policy per hop** (τ, clock domain) | deployment | — | each hop with its own clock | gate / consumer | clocks mapped (sim vs. wall; R07, R13) | EXEC: R13, R19, R24 |
| C7 | **Re-authorization and calibration/anchor state** (engage, recenter, reset) | app (UR5e) or mapper (Docker_Teleop): private state | must be owned or reproduced by any verifier | verifier / mapper | mapper | owner honest; under A-app only if the verifier owns it (R30) | EXEC: R04 (M39), R30 [synthetic]; Docker_Teleop AUDIT (A05) |
| C8 | **Final writer and permission** (exactly one mediated writer per actuator topic; app identities denied) | deployment (mux + SROS2 permissions + uids) | — | DDS access control at writer creation | DDS participant / controller | keys unreadable by the app's uid; other paths (action, services, IPC) closed separately | EXEC: R22, R25/R26 [Gazebo], R27/R29 [SROS2, mock JTC]; Docker_Teleop has several writers per controller topic (A05) |
| C9 | **Command ↔ source binding** (a command is derived from a cited, recent source sample via the declared mapping) | app cites a sample id; the verifier has an independent source copy | sample id through every hop | trusted verifier / mapper | before the final writer | independent source tap (on Monado: unauthenticated IPC, A04 §3); reproducible mapping (the smoothing probe lost 95 %) | EXEC: R30 [synthetic]; real-path premise UNVERIFIED / not available unmodified |
| C10 | **Late-message handling at the controller** | controller (JTC rejects a stamped trajectory that ends in the past) | stamps on trajectories (start-now stamps bypass it) | controller | controller | writers stamp honestly | EXEC: R25 pre-flight (n = 1) + JTC log; formal R26 with zero-stamp writer |

## 2. Where the current real paths stand (conformance, not a score)

| Requirement | UR5e Servo path (R04–R30) | Docker_Teleop backend @64cbdde (R20 + A05) |
|---|---|---|
| C1 receipt / sensing | sensing absent; receipt only in the patched driver | receipt internal to the receiver; dropped at the mapper |
| C2 representation time | app generation stamp; Servo-level stamp | mapper restamps `now()`; the Servo output has no header |
| C3 seq / session | app copy only (A2) | none |
| C4 neutral vs. release | app-specific (B1) | conflated in the mapper |
| C5 task semantics | not declared (frames equal; M7 not exercised natively) | latest tf for the anchor (`Time()`) |
| C7 anchor ownership | app | mapper; retriggered by input fields and parameters |
| C8 final writer | hold writers + Servo on one topic unless a mux is added | several writers per controller topic; no mux |
| C9 command ↔ source | not available (legacy API has no sample id) | not available |

## 3. Necessity vs. cost benefit (kept separate)

- **Necessity (supported).** The same ten requirements recur on both backends and on every hop examined. Each
  executed failure traced to one of them being absent, not to a missing algorithm. That supports a **minimum contract
  / conformance-test question**.
- **Benefit of a shared implementation (not measured).** No result shows that a common component reduces the total
  cost below the strongest per-app or deployment baseline. The baselines are:

  | Requirement | Strongest baseline so far |
  |---|---|
  | C1–C3 | per-hop typed fields: app 6 lines (A2); receiver +21 lines, producer +2 fields (R20); driver patch (R19) |
  | C8 | mux plus a policy file, enclave keys and uids (R29) |
  | C9 | a trusted verifier that owns calibration (R30) |

  The two-heterogeneous-real-paths condition for a broad system claim stays in force: the second real frontend is
  BLOCKED_ENV.

## 4. Measurable questions for a possible system contribution

1. **Integration cost.** For the same requirement set C1–C9, how many changed lines, files, components and deployment
   artifacts does it take to retrofit each path?
   - per-path, baseline by baseline (as in R13, R19, R20, R27, R30);
   - versus one conformance kit (typed envelope + gate + policy generator).
2. **Coverage per unit TCB.** Which of C1–C10 does each design enforce?
   - per-app fixes;
   - trusted mapper;
   - SROS2/mux deployment;
   - a common contract layer.

   And with which trusted components, under A-net, A-app and A-rt separately?
3. **Functional loss.** How many legitimate app features fail verification, or must move into the TCB? (Smoothing:
   95 % blocked under TV.)
4. **Conformance detectability.** Can a static/dynamic conformance check identify the missing requirements that A05
   found by hand (the mapper restamp, the neutral/release conflation, multiple writers) before deployment?

None of these is answered by the present data.
