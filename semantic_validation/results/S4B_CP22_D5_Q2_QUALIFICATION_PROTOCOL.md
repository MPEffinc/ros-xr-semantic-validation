# XRROS-S4B-D5Q2-1.0.0 — targeted D5 integration corrections and requalification

The research policy XRROS-S4-1.0.0 and the D5 fixture, thresholds and registered recovery rules are unchanged. D5Q1's 12/14 verdicts are immutable. `preflight/d5q1_to_d5q2_input_delta.txt` lists the changed inputs.

## Corrections, each with a causal hypothesis tied to retained D5Q1 raw

1. **B3 re-arm event logging** (`d1_nodes.py`). Event keys `kind` and `monotonic_ns` are renamed `event_kind` and `event_monotonic_ns`. Under D5Q1 they collided with `trace.log()` and crashed the B3 node before the barrier.
2. **Disconnect semantics** (`d1_nodes.py` B3 branch, `d3_tloracle_property.py`). Only a drop of an **accepted** connection (receiver connection index ≥ 1) counts as a disconnect. The startup neutral published before the first client exists does not. Under D5Q1 this produced a spurious pre-trial fault.
3. **Setup retry decision** (`run_qualification.py`). Only the start barrier decides whether an outcome exists, so a pre-barrier failure is retried up to twice, as registered. `run_owned.py` returns 0 even when the launch fails. Container prefix `s4cp22d5q2_`.

## Preflight

- **Host tests:** 16/16 PASS. They reproduce the D5Q1 `TypeError` with the old logging expression and assert the renamed form. They also check the index ≥ 1 rule in both components and the barrier-only retry.
- **Genuine official monitor + TLOracle component tests:** both PASS, under R_EXPLICIT and R_AUTO. They start with a pre-connection startup neutral (index 0, open false). The oracle stays ARMED and the next gen-1 active sample is forwarded, whereas D5Q1 code would have disarmed and blocked it. The rest of the D5 sequence is unchanged.

## Targeted requalification

The schedule covers 6 cells: B2-native, B2-composed and B3 under I_FULL, with R_EXPLICIT and R_AUTO. These are the configurations whose code changed.

The following are reused from D5Q1 without being re-run, because their code path is unchanged: B0, the shim, B1 I_FULL, and every I_NATIVE arm. The B3 and B2 native branches have no re-arm machine.

Each cell allows at most two pre-barrier retries. The formal D5 campaign must be frozen separately, after all cells qualify.
