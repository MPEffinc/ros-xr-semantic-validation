# CP20 D4-L Q2 determination: 15/15 qualified on retained D4LQ1 raw

The analyzer-only freeze was pushed at `f8a0324b0a6fe2bc37b44c19daec3ed9d79e5105`. `analysis/reaudit_d4lq1_raw.py` re-audited all 15 retained D4LQ1 cells. No Gazebo cell was repeated, because the runtime is byte-identical.

Result: **D4L_SETUP_COMPLETE, 15/15 MEASUREMENT_QUALIFIED.**

- **Reconnects:** each of the 10 L750 cells has exactly one reconnect. Each came after 1.744–1.749 s with no bytes and matches the original receiver's single `idle no bytes` disconnect. Delays L000, L150 and L350 have none.
- **B0/shim pairs:** L750 PASS (0.053117 ms, 0.002853 rad) and L000 PASS (0.051746 ms, 0.003285 rad).

Evidence is in `runs/s4b_cp20_d4lq2_20260928T104414Z/analysis/d4l_setup_summary_q2.json` (`reaudit_evidence_manifest.sha256`). D4LQ1's frozen 5/15 verdict is unchanged. This is setup qualification only.
