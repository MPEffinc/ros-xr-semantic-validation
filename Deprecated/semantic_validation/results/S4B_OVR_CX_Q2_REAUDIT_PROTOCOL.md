# XRROS-S4B-OVRCXQ2-1.0.0 — analyzer-only C-X setup re-audit (registered before running)

This protocol re-audits the C-X Q1 setup raw data without running any new trial. The Q1 raw data and the Q1 result stay unchanged. The analyzer is `runs/s4b_ovr_cx_q1_20260928T220949Z/analysis/cx_setup_audit_q2.py`.

It adds two rules on top of the frozen Q1 C-X audit.

## Rule Q2-a: B2 association under oracle faults

- **Real oracle verdicts:** a property row is required exactly for envelopes that received a real oracle verdict (`currently_true` or `currently_false`).
- **Unknown statuses:** an official `unknown` status without a property row is the fault's own record. It is allowed only for envelopes published no earlier than 1 s before the proven fault. That 1 s is the bound on monitor-queue lag. Under ABSENT such statuses are always allowed.
- **No status at all:** envelopes that never received any official status remain a recorded B2 outcome.

## Rule Q2-b: gate-crash cells

- **Before the stop request:** every Servo-input publication before the common adapter's first stop request must join exactly one Servo callback, and no callback may be unjoined.
- **From the stop request on:** publications with no callback are a consequence of the fault response, not an observation gap.

## Gate and carry-over

The gate is unchanged: every cell must be MEASUREMENT_QUALIFIED and the B0/shim pair must be PASS. The OpenVR C-X formal campaign will use this Q2 audit as its validity rule.
