# CP18 Docker D4Q2 targeted requalification: 5/5 qualified; D4 setup complete

The freeze was pushed at `e7bcb266e446d847b561f244568b16bc3c98ef94`. Each of the five frozen cells ran once, reached the start barrier and exited 0, with no retry. Evidence is in `runs/s4b_cp18_d4q2_20260928T052627Z/` (`raw/`, `analysis/d4_setup_summary.json`, `runtime_evidence_manifest.sha256` verified). Result: **D4_SETUP_COMPLETE**, all five MEASUREMENT_QUALIFIED.

- **Fresh B0/shim pair at A750/F250:** PASS, 0.054561 ms and 0.000989 rad. Both B0 and the shim moved about 0.283 rad on 750 ms-old stamps.
- **B1 I_FULL at A750/F250 and A150/F100:** exactly teleop samples 20–55 were withheld. The sender reconnected once, before sample 56, after the original receiver's idle close. 84/84 real samples were received with stamps preserved, callbacks were complete, and the robot stayed at rest (≤3.8e-10 rad).
- **B1 I_FULL at A000/F250:** no withholding, no reconnect, and 0.287 rad of motion.

Together with D4Q1's 18 qualified cells, every D4 configuration has qualified setup evidence. The D4Q1 blocked cells are preserved unchanged. This is not a freshness-policy result; the formal campaign is `S4B_CP19_D4_FORMAL_FREEZE.md`.
