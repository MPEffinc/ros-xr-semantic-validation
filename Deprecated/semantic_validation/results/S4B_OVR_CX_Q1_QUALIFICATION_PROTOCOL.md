# XRROS-S4B-OVRCXQ1-1.0.0 — prospective OpenVR C-ID / C-MON coverage setup qualification and design

This applies XRROS-S4-1.0.0 (SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`) without changing it.

- **Root:** `runs/s4b_ovr_cx_q1_20260928T220949Z/`.
- **Code base:** the OpenVR Q1 inputs. The full delta is in `preflight/ovrq1_to_cxq1_input_delta.txt`. The official monitor build and trial-local deps are the frozen OpenVR Q1 ones.
- **Registration:** C-ID is registered for each stack with I_FULL. C-MON's B2 conditions are not restricted by stack.
- **Evidence scope:** fake OpenVR API only.

## Changes from OpenVR Q1

**C-ID fixture** (`openvr.py`, `OVR_CID_KIND`):

- Every poll is bound at acquisition, using the Docker `cid_binding.binding_hash` over ID, generation, stamp, native state, and the projection of the raw 3×4 pose plus grip.
- One fault is injected at **poll 150**, while the arm is moving and armed:
  - **DUPLICATE_ID:** a well-formed, self-consistently bound sample that reuses the already-ingested `openvr:140`.
  - **MISMATCH:** the bound state says the scheduled pose, but the pose actually acquired from the API is raw z + 0.05.

**Checks** (`ovr_policy.py`, only when `CASE_ID=CID`):

- The ordinary Docker `cid_binding.check` compares the bound metadata against the projection **actually acquired** in the same poll.
- Duplicate detection runs on new ingestion; the key is this acquisition's time.
- A failure latches DISARMED under R_EXPLICIT.
- The same code serves B1 (before use), B3 (publish point) and the official B2 oracle.
- For B2, the production sidecar transports the acquired projection and the ingestion time in the envelope. This is transport only, with no decision.

**C-MON:**

- The Docker C-MON Q3 trial-owned injector (`cmon_fault.py`) is reused. Its ownership check is adapted to the OpenVR oracle property module.
- The injection offset is registered per fault: 2.91 s for oracle faults (the injector first proves 100 ms of health), and 3.01 s for gate faults. Both land at poll 150, while moving.
- B1/B3 gate-crash markers make the gate stop producing decisions and pass input through (the fail-open crash model); the common 250 ms heartbeat reacts.

**Setup audit** (`analysis/cx_setup_audit.py`):

- The frozen OpenVR Q1 checks apply.
- A record missing because of the injected fault is not a recorder failure:
  - a killed oracle's post-kill resource target;
  - post-fault property rows.
- Fault proof is required.
- Envelopes without an official status (the known Jazzy official-monitor stall) are a B2 outcome.

## Host / component preflight

- `analysis/test_ovr_cid.py`: 3/3 pass after one retained first attempt (`preflight/test_ovr_cid_and_policy_attempt1.*`). That attempt's test expected `DISARMED_HELD_GRIP` during the 500 ms dwell, but the shared `Rearm` correctly reports `DISARMED_DWELL`. The fix was to the test expectation only.
- `test_ovr_policy.py`: still 8/8.
- Components in `preflight/component_*`:
  - B1 MISMATCH and B3 DUPLICATE_ID reject exactly poll 150 with the registered reason, then latch.
  - The official B2 detects MISMATCH at poll 150 but shows the known Jazzy STALE decisions.

## Design (minimum-sufficient)

**Candidate matrix:** C-ID 4 kinds × {B0, shim, B1, B2-native, B2-composed, B3, B2-ST} × 2 regimes, plus C-MON as in Docker.

**Essential cells:**

| Case | Cells |
| --- | --- |
| C-ID MISMATCH | B0, shim, B1, B2-composed, B3, B2-ST-composed |
| C-ID DUPLICATE_ID | B0, shim, B1, B2-composed, B3, B2-ST-composed |
| C-MON | B0, shim, B2-composed × {ABSENT, DISCONNECT, NONRESPONSIVE}, B2-native × DISCONNECT, B1 gate crash, B3 gate crash |

The proposed formal campaign is 20 cells × 5 = **100 trials**, about 80 minutes, run sequentially.

**Registered NOT_RUN:**

- **C-ID MISSING_FIELD and MISSING_ID.** They are field-presence checks in the identical shared function over the same bound metadata record. The OpenVR-specific state transport to every placement is exercised by the two run kinds and by the W campaign.
- **C-ID B2-native.** It has no stop integration, which is already established.
- **I_NATIVE.** OpenVR's native pose message carries no ID or binding, so this is UNOBSERVABLE by construction.
- **C-MON native-regime cells.** The health path is regime-independent, as in Docker.

## Q1 setup cells (16) and gate

| Case | Cells |
| --- | --- |
| C-ID MISMATCH | B0, shim, B1, B2-composed, B3, B2-ST-composed |
| C-ID DUPLICATE_ID | B1, B2-composed, B3, B2-ST-composed |
| C-MON B2-composed | ABSENT, DISCONNECT, NONRESPONSIVE |
| C-MON other | B2-native DISCONNECT, B1 gate crash, B3 gate crash |

**Gate:**

- Every cell is MEASUREMENT_QUALIFIED.
- The fresh B0/shim pair (MISMATCH fixture) is PASS.
- At most two setup retries are allowed, and only when no barrier was reached.
