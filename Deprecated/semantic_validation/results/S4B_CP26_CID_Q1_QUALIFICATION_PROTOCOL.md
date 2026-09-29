# XRROS-S4B-CIDQ1-1.0.0 — prospective Docker C-ID binding-integrity setup qualification and design report

This campaign instantiates XRROS-S4-1.0.0 C-ID without changing it. The research protocol's SHA-256 is `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`.

The registered C-ID case is: "Each stack I_FULL: absent required field, missing/duplicate binding ID, state-command mismatch and old generation → reject or classify unobservable before actuation; retain every log; no nearest-neighbor causal claim". A related rule in §6 says that replaying a previously consumed source-event ID as a new source update is the C-ID duplicate case, while repeated commands from one cached sample are **not** duplicates. The results for D1 through D6 are unchanged and are not pooled with this campaign.

## Binding contract (`inputs/cid_binding.py`), identical for B1, B2 (official oracle) and B3

**Reference.** At source capture, the sender computes `binding_sha256` over the source-event ID, the generation, the original stamp, the native state, and the **intended** command projection. It carries the result unmodified in `_qualification`. The command projection consists of the fields the pinned receiver copies from the wire into the ROS command:

- right-hand tracked;
- pose position and orientation;
- teleop, using `right_teleop_enable` first, as the receiver does;
- grip.

**Check.** Each defense recomputes the projection from the command it is about to forward, never from its own copy of the reference:

- B1 uses the outgoing wire.
- B2 uses the envelope's `original_payload`, which holds the receiver's ROS fields.
- B3 uses the ROS message.

The recomputed projection is combined with the metadata's ID, generation, stamp and state, then compared with the reference.

**Reason codes.** A failed check is reported as one of `MISSING_SOURCE_EVENT_ID`, `MISSING_REQUIRED_FIELD` (a missing generation, stamp, state or binding), `STATE_COMMAND_MISMATCH` or `UNBOUND_REQUIRED_STATE`.

**Duplicates.** Duplicate detection runs on **new ingestion** only (`Ingestion`), and the ingestion key depends on where the check runs:

- B1: each capture.
- B2/B3: the original receiver's receipt time for that ID.

A cached republication of an accepted sample has the same key, so it is not a duplicate. A previously ingested ID arriving with a different key is `DUPLICATE_SOURCE_EVENT_ID`.

**On a failed check.** A failure latches the shared D5 R_EXPLICIT state machine, the primary recovery policy. The common stop adapter uses its ordinary single-stop mode. Mechanisms are attributed separately, and B2-native keeps its filter-only behavior.

**Information regimes.** I_NATIVE has no ID, generation or binding, so it is UNOBSERVABLE by construction.

## Fixture (`inputs/cid_fixture.py`)

The fixture uses the registered D1 motion shape: 20 Hz, 120 slots, 6 s, with the active phase at x = .35 in slots 36–55. Every sample is bound at capture. Exactly one fault is injected at slot 50, while the arm is moving and the defense is armed:

| Kind | Fault |
| --- | --- |
| MISSING_FIELD | No `generation_id` |
| MISSING_ID | No `sample_id` |
| DUPLICATE_ID | A well-formed, self-consistently bound sample that reuses `docker:40` |
| MISMATCH | The bound state/command says x = .35, but the command payload says x = .65 |

**Old generation.** This is the D5 formal evidence, in which the gen-1 replay was rejected at every evaluation by B1, B2-composed and B3 under both policies. The injection point and claim are identical, since the sample's generation in I_FULL is older than the current one. It is **reused and not counted** as a C-ID trial.

## Declared delta versus the D6Q1 inputs (`preflight/d6q1_to_cidq1_input_delta.txt`)

- New files: `cid_binding.py`, `cid_fixture.py`, `cid_sender.py` (dispatched when `CASE_ID=CID`) and `cid_monitor_preflight.py`.
- `d1_nodes.py`: a B3 C-ID branch.
- `d3_tloracle_property.py`: an oracle C-ID branch. Neutral detection keys on `origin == ORIGINAL_NEUTRAL`, never on ID presence.
- `d1_probe.py`: a C-ID schedule check.
- `receiver_coverage.py` and `servo_callback_drain.py`: now keyed on the transmitted wire (ID, stamp). This is identical to the previous behavior whenever the ID equals `docker:{index}`.
- Runner and scheduler: `--kind`, and the `s4cp26cidq1_` container prefix.

## Preflight

**`analysis/test_cid.py`: 10/10 PASS.** The tests cover:

- valid binding at the wire and at the receiver-generated ROS fields;
- each command-field mutation, and the state-claim mutation, detected as mismatch;
- a non-command field change correctly **not** reported as a mismatch;
- each missing field reported with its correct code;
- a documented anti-pattern: regenerating the reference from the modified downstream payload would hide the mismatch;
- cached repeats not treated as duplicates, while a new ingestion with a reused ID is;
- a sender loopback for all four kinds × {B0, B1 I_NATIVE, B1 I_FULL}: B1 I_FULL withholds slot 50 and then 51–55, which is the R_EXPLICIT latch, and every other sample binds;
- coverage and drain with reused or absent IDs.

Attempt 1 failed one assertion because the test assumed `teleop_enable` alone changes the command. The receiver takes `right_teleop_enable` first, so the check's `BOUND` verdict was correct. The attempt is retained in `preflight/test_cid_attempt1.*`.

**Official monitor + TLOracle component test (`preflight/official_full_cid/`): PASS.** The results were:

- a valid event and its cached repeat on the same ingestion were forwarded;
- MISMATCH, MISSING_ID, MISSING_REQUIRED_FIELD and DUPLICATE (new ingestion) were blocked with the correct reasons;
- a valid event afterwards stayed latched (blocked);
- the release neutral was forwarded.

## Design report (minimum-sufficient scaling)

**Candidate matrix.** 4 kinds × 10 arms (B0, shim, 4 I_NATIVE, 4 I_FULL) × 5 repetitions = 200 trials. Old generation is reused from D5.

**Essential per repetition (24 trials):**

- B1, B2-native, B2-composed and B3 I_FULL × 4 kinds (16). This checks rejection before actuation, the stop, whether any injected sample reaches Servo, and mechanism attribution.
- B0 and the shim × 4 kinds (8). These provide the pair gate and the original's consequence. The fixtures differ by kind, so the pairs cannot be shared across kinds.

**Omitted or redundant:**

- I_NATIVE × 4 kinds × 5 repetitions. There is no ID, generation or binding in the native interface, so these are UNOBSERVABLE by construction. They are run once in setup (B2-composed and B3 native, MISMATCH) to document the consequence and marked NOT_RUN for formal.
- Old generation: reused from D5.

**Host versus Gazebo.** Broad negative and boundary coverage runs on the host and at the official component level. Gazebo is reserved for real consumer acceptance, stop behavior and joint motion.

**Proposed formal campaign.** 120 trials (24 × 5), about 1.9 h, run sequentially.

**Claims.**

- Supported: the ordinary binding and duplicate checks, the I_FULL behavior of all four existing defenses per kind, B2-native versus B2-composed, and the original's consequence.
- Unsupported: formal native repetitions; adversarial sources that forge the binding (the trust assumption is a trusted source); OpenVR; and actual Quest.

## Setup schedule and gate

`qualification_schedule.csv` lists 20 cells:

- a B0/shim pair (MISMATCH);
- B1, B2-native, B2-composed and B3 I_FULL × 4 kinds;
- B2-composed and B3 I_NATIVE (MISMATCH).

All cells must move before slot 50. Each cell allows at most two retries, and only before the barrier. The pair gate is 5 ms and 0.02 rad, and every cell must be MEASUREMENT_QUALIFIED under `analysis/cid_setup_audit.py`. This is not a policy score.
