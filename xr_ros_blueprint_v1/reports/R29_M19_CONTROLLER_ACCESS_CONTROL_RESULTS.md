# R29 — M19 controller-topic access control: results (R27; 18/18 valid, 2026-10-04)

| | |
|---|---|
| Protocol | R27, frozen 7462f76; `git archive` snapshot with per-trial hash checks |
| Raw data | `experiments/M19_acl/raw/` (ignored, 15 MB, 416 files); sha256 in `results/ACL_RAW_SHA256.txt`; measures in `results/acl_trials.json`; keys under the ignored `run_snapshot/<sha>/keys` (never printed or committed) |
| Level | SROS2 Enforce on Fast DDS 2.14.6, real JTC on mock hardware, per-process uids; **final controller topic only** |
| Validity | 18/18 valid; the enforcement probe failed as required in every trial (no node without an enclave) |

## Results (3 trials per cell; "reached" = JTC `controller_state` reference **and** `/joint_states` at the payload)

| Deployment | APPROVED (app → `/m19/app_cmd` → mux) | APP_DIRECT (app key on the controller topic) | MUX_DIRECT (trusted identity, same payload; positive control) |
|---|---|---|---|
| D_OPEN (default sros2 permissions for the app) | reached 3/3 | **reached 2/3**; 1/3 not reached (see below) | reached 3/3 |
| D_RESTRICT (app may publish only its input topic) | reached 3/3 | **0/3**: `create_publisher() could not create data writer` (3/3); nothing on the topic; joints unchanged | reached 3/3 |

- **The D_OPEN APP_DIRECT miss (C07)** was not access control.
  - The payload appeared on the controller topic: the observer received all 20 messages.
  - The app's writer matched only one reader (the observer) during its 2 s burst. The JTC reader had not finished the
    secure discovery/handshake, so the controller never received the message.
  - It is reported as observed, not as a block.
- **Key isolation (every trial).** uid 2001 (app) was denied reading:
  - the mux and controller `key.pem`;
  - the identity-CA, permissions-CA and CA private keys.
- **Transport premise (pre-flight).** The default Fast DDS shared-memory transport delivered nothing between
  different uids. The runs used UDPv4 on loopback.

## Reading

**What this result covers.**

- With DDS-Security enforced and a restricted permission file, **an XR app that holds a valid key cannot become a
  writer on the final controller topic**.
- The approved path (app → mux → controller) and the trusted writer still work.
- Under the default sros2 permissions, the same key **can** write the controller topic directly, and the controller
  executes it.
- So the mediation premise of R22/R25 (a single writer at the final boundary) can be enforced for this topic **by
  existing deployment tooling**:
  - per-enclave permissions;
  - separate uids;
  - key files unreadable by the app's uid.

**What it does not cover.** The restricted app could still:

- send any content on its permitted topic (R30);
- use paths not tested here:
  - the JTC action and services;
  - Servo and controller_manager services;
  - parameters;
  - the Monado IPC control calls;
  - the remote-driver port (A04 §3, §7).

A process that runs as the trusted uid or as root holds the trusted keys.

**Classification.** M19 (topic level, for the app's ROS identity) is **solved by an existing method in the tested
scope**. Its cost:

- a policy file;
- enclave keys;
- per-process uids;
- a transport choice for uid separation.

This is not complete mediation of all execution paths.
