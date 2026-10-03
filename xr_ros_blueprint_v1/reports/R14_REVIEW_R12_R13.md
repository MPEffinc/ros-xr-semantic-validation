# R14 — ChatGPT review of R12/R13 and A02 (2026-10-03)

This is a review of repository documents and code at `b9c920cc7d6bc3ad6e47de85c67c502c8db268ae`. No new experiment was executed by ChatGPT. Host raw data and local Git state were not independently inspected; the execution report provides those checks.

## Findings supported in the reported scope

- R12 records the applied collision scale directly (minimum 0.8945), resolving the earlier magnitude-observation limit for these conditions. A bound on EE travel or latency without collision scaling is not established.
- Existing measured-state hold and an external implementation of the JTC constant-deceleration formula met P_stop at two speeds. DECEL_TOPIC is an external implementation, not the native JTC action cancel feature.
- R12's B1 I3 replication has one actual S2 threshold failure (0.0104 vs 0.01 rad/s). R04's earlier 3/3 result remains valid as historical data; a general failure-free full-contract guarantee is unsupported.
- R13's A2 blocked 255/255 delayed/cache/inactive-cache messages with 0/4508 fresh-message blocks. Source stall was not solved: 84/84 and, in the separate long-stall follow-up, 294/294 were admitted.
- A02 is a code/literature audit, not an executed M7/M8/M9 comparison.

## Distinctions needed for interpretation

### App read freshness and source freshness

A2's `acq_ns` is recorded immediately after the OpenVR pose read; its sequence increments per app read. Neither is a sensor observation time or a source-update sequence. Calling it acquisition provenance is acceptable only with this boundary stated.

The source-stall failure is an information-availability limit at the current app/gate boundary. It is not evidence that every upstream component lacks a usable observation: the remote driver's receive callback already receives each packet, but does not retain its time. A standard source receive watchdog is a strongest-baseline candidate. That would establish freshness of receipt for a configured periodic source, not freshness or truth of physical sensing.

Information acquisition is a legitimate system research question, although a standard watchdog or metadata-preservation patch alone does not establish novelty. Distinguish:
- new decision method needed under identical usable information;
- needed evidence missing from the consumer boundary;
- known root fix available but not deployed;
- deployment/resources still unverified.

M12's KNOWN_METHOD and X024's sufficient-in-reported-scope verdict must remain limited to the solved classes and trusted-app assumption. Source stall and S2 are not covered by that verdict.

### Carrier and comparisons

R11 A2 uses `frame_id` as a local experimental metadata carrier. `m12_gate.py` parses it and restores `base_link` before Servo. This is not a portable ROS message contract and has not been tested through a real republisher. The gate carries but does not inspect `eTrackingResult`; inferred or valid-but-untracked poses were not tested.

A0 uses Servo's 500 ms timeout, whereas A1/A2 use a 100 ms age policy. A0's 250 ms transport-delay admission is not evidence that an equal-policy generic age checker fails. The meaningful equal-policy contrast is A1 vs A2 on cache/keepalive.

### Stop request, acknowledgement and continued writers

R12 logs show that the first hold is sent before the pause acknowledgement, and that pre-pause Servo trajectories sometimes arrive afterward. Re-holds at acknowledgement and +0.1 s closed the sampled cases. This does not establish that pause completion precedes the first hold or that arbitrary delayed trajectories cannot replace it.

A stop guarantee therefore needs a stated writer/queue assumption or mediation at the final command boundary. Acknowledgement alone must not be assumed to drain all DDS/application queues. An exclusive writer or existing command multiplexer is a strongest baseline before claiming a new integration method.

### Integrity incident

The restored hash proves end-state equality, not by itself the code executed during the incident. The inspected runner defines its BRIDGE mapping once at process startup and does not reload its own source; the report's explanation is consistent with that code. Confirm the process start/edit timeline and whether any child reread the edited file before treating incident impact as established. Future campaigns should execute an immutable snapshot of frozen code while working copies remain editable.

## Follow-up judgment

Prioritize the information path over additional stop-distance tuning:
1. source receive watchdog / source evidence feasibility on the synthetic driver, with a strongest known root fix;
2. evidence preservation through actual Docker_Teleop receiver code, explicitly a backend/component result without a real frontend;
3. M7 dynamic-transform verification with declared historical-sample semantics and a time-indexed ground truth;
4. only a small conditional stop-ordering check if needed to resolve the queue/writer assumption.

Do not rerun the known Quest/Linux blockers without new resources. A Quest remains necessary for the identified real frontend paths, and a watchdog result on Monado remote must not be generalized to a headset.

The next executable scope, budgets and branch conditions are supplied separately in the user-facing Claude Code prompt, not by this review.
