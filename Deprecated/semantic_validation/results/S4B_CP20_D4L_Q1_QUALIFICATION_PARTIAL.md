# CP20 D4-L Q1 setup result: 5/15 qualified; all L750 cells flagged for pre-roll reconnect

This campaign was frozen at `b1ab8bff08d55647b878e16d2876434e09642d1d` and run only after D4 formal completed, at `fd0cfdd`, with no concurrent load. All 15 frozen first attempts ran once: every one reached the barrier, exited 0 and needed no retry. Evidence is in `runs/s4b_cp20_d4lq1_20260928T053735Z/` (`raw/`, frozen `analysis/d4_setup_summary.json`, `runtime_evidence_manifest.sha256` verified).

**5 MEASUREMENT_QUALIFIED** under the frozen analyzer:

- the B0/shim pair at L000/F250, which PASSES (0.053 ms, 0.0029 rad);
- B3 I_FULL at L000/F250 (moved);
- B2-composed I_FULL at L150/F100 (at rest, which is the expected rejection);
- B3 I_FULL at L350/F500 (moved).

**10 BLOCKED_MEASUREMENT.** Every L750 configuration was blocked, and only for `UNEXPLAINED_SENDER_RECONNECT`. The sender connects about 1.0 s before the barrier, and at L750 its first FIFO release comes 0.75 s after it. The connection therefore sits idle for 1.744–1.749 s. The original receiver logged `TCP client disconnected (idle no bytes)` after 1.5 s, and the sender reconnected exactly once, before index 0.

At L000, L150 and L350 the idle time was 0.99–1.35 s and no reconnect happened. In every L750 cell:

- 120/120 samples were received, in FIFO order, with no early release (lateness ≤ 0.16 ms) and unchanged stamps;
- exact callbacks were 371–372;
- B0, the shim, the native arms and B1 I_FULL moved about 0.28 rad, and B2/B2-composed/B3 I_FULL stayed at rest;
- the L750 B0/shim pair was within the frozen limits (0.052 ms, 0.0033 rad).

The frozen D4Q2 transport rule treated a reconnect as legal **only** after at least 1.5 s of B1 withholding. It did not encode the actual cause, which is the original receiver's idle disconnect, from whatever source. That is an analyzer-rule gap, not a runtime or policy failure.

These verdicts stay as they are. XRROS-S4B-D4LQ2-1.0.0 (`S4B_CP20_D4L_Q2_QUALIFICATION_PROTOCOL.md`) re-audits the retained raw with an idle-time rule. No Gazebo cell is repeated, because the runtime is byte-identical.
