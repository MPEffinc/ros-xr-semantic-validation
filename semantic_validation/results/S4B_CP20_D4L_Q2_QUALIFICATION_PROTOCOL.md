# XRROS-S4B-D4LQ2-1.0.0 — D4-L reconnect-legality correction (analyzer only)

The research policy XRROS-S4-1.0.0 is unchanged. So are the D4-L runtime and fixture: `inputs/` is byte-identical to D4LQ1 (`preflight/runtime_unchanged_check.txt`). The D4LQ1 frozen 5/15 verdicts are immutable.

## Causal hypothesis

The original Docker receiver disconnects a TCP client after more than 1.5 s without bytes. The sender connects about 1.0 s before the barrier. Under L750 the FIFO holds the first sample until 0.75 s after the barrier, so the connection idles for about 1.75 s. The sender's qualified D4Q2 peer-close detection then reconnects once, before index 0.

The D4Q2 legality rule accepted that reconnect only after B1 withholding. D4-L's pre-roll idle is a second, equally original-receiver-driven cause.

## Correction (`analysis/d4_setup_audit.py` only)

A reconnect is legal for any arm when both of the following hold:

- **Idle time:** it follows at least 1.5 s with no transmission on the connection, measured from the connect, the previous reconnect, or the release/send of an **earlier** sample;
- **Receiver log:** the original receiver's own `TCP client disconnected (idle no bytes)` count equals the reconnect count.

Otherwise the trial gets `UNEXPLAINED_SENDER_RECONNECT` or `RECONNECT_WITHOUT_MATCHING_ORIGINAL_IDLE_DISCONNECT`.

## Tests

The test suite (`preflight/host_regression.*`) passes 19/19. Its new tests cover:

- the retained D4LQ1 L750 pre-roll reconnect, now legal;
- the D4Q2 B1-withholding reconnect, still legal and still qualified;
- a synthetic reconnect 60 ms after a transmission, now rejected on both rules.

An earlier draft of the rule wrongly counted the transmission that the reconnect itself precedes. The new tests caught this before the freeze, and it was fixed.

## Determination

After this freeze is pushed, `analysis/reaudit_d4lq1_raw.py` re-audits all 15 **retained** D4LQ1 cells and both B0/shim pairs, and writes `analysis/d4l_setup_summary_q2.json`. This is not a new runtime trial and does not replace D4LQ1's verdicts.

The re-audit's outcome is **not** blind. The cause of the flags and the other checks' status are already known from the D4LQ1 audit, and are stated here in advance. No cell is excluded, and every check other than the reconnect rule is unchanged.

The D4-L formal analyzer inherits this rule.
