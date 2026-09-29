# CP18 Docker D4Q1 setup result: 18/20 qualified; B1 I_FULL rejection transport gap

Frozen at `d2ae0ed0fe7cdd0825d9c14e610330b57a842aea` before any Gazebo cell. All 20 first-attempt cells were run once (20 attempts, all reached the start barrier; no setup retry). Evidence: `runs/s4b_cp18_d4q1_20260928T050614Z/` (`raw/`, `attempts.jsonl`, `commands.jsonl`, frozen `analysis/d4_setup_audit.py` → `analysis/d4_setup_summary.json`; `runtime_evidence_manifest.sha256`, 1,486 files, verified). This is setup qualification, **not** a freshness-policy result.

**18 MEASUREMENT_QUALIFIED.**

- **A000/F250:** all ten configurations (B0, shim, B1/B2-native/B2-composed/B3 × I_NATIVE/I_FULL) moved 0.282–0.287 rad, with 358–361 exact source-parent→Servo callbacks per instrumented cell.
- **B0/shim pairs:** A000 PASS (0.054827 ms, 0.004238 rad); A750 PASS (0.031311 ms, 0.001166 rad). Both B0 and shim moved under 750 ms-old stamps, because the original path does not read the source timestamp.
- **Cells that stayed at rest (≤3.8e-10 rad):** B2-native, B2-composed and B3 I_FULL at A750/F250; B2-composed at H1P0/F250; B2-native at FUT1S/F250. Their exact callback and official-association coverage was complete.
- **B3 I_FULL A350/F500** moved 0.284 rad, which is fresh under F500.

These observations are setup evidence only; policy is scored in a separately frozen formal analyzer.

**2 BLOCKED_MEASUREMENT: B1 I_FULL A750/F250 and A150/F100.** Both cells are ones where B1 correctly withholds teleop samples 20–55 for 1.8 s. The original receiver logged `client_idle_disconnect_sec=1.50` and `TCP client disconnected (idle no bytes)`. When sample 56 was due, the D4 sender raised `BrokenPipeError`: only 57 of 120 slots were recorded, and the launch exited 14 (`source_incomplete`).

This is a harness transport-integration gap exposed only by D4's 1.8 s withholding; D3 withheld only 1.0 s. It is not a B1 policy failure, and it occurred after the barrier, so it was not retried.

Correction: the separately versioned D4Q2 (`S4B_CP18_D4_Q2_QUALIFICATION_PROTOCOL.md`) reconnects before the next real transmission, and only after a detected peer close. It then requalifies the affected configurations. These D4Q1 records remain as they are.
