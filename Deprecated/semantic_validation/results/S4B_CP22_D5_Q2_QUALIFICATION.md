# CP22 Docker D5Q2 targeted requalification: 6/6 qualified; D5 setup complete

The freeze was pushed at `247d4d25ccb43ce2392b9e003eb0139cd0109462`. Each of the six cells (B2-native, B2-composed and B3 under I_FULL, with R_EXPLICIT and R_AUTO) ran once, reached the barrier and exited 0, with no retry. All six are MEASUREMENT_QUALIFIED.

`d5_setup_audit.main()` assumes a B0 row, so the cells were audited with the frozen `inspect()` through `analysis/run_d5q2_audit.py`. Evidence is in `runs/s4b_cp22_d5q2_20260928T132939Z/`, and `runtime_evidence_manifest.sha256` verifies.

The raw data shows the following timeline for B3:

- There is no pre-trial fault.
- After the source closes the connection at 2.800 s, the first `DISCONNECTED` fault comes at 2.813 s and the stop at 2.815–2.818 s.
- R_EXPLICIT re-arms at 4.713 s (slot 94, the edge), and the resume reply arrives at 4.724 s.
- R_AUTO re-arms at 4.164 s, 500 ms after the replay reset, with the resume at 4.174 s.

B2-composed stops at 2.812 s and, under R_AUTO, resumes at 4.162 s.

Together with the D5Q1 cells, every D5 configuration is setup-qualified: B0, the shim, B1 I_FULL and the four I_NATIVE arms from D5Q1, with the B0/shim pair at PASS. This is not a policy score.
