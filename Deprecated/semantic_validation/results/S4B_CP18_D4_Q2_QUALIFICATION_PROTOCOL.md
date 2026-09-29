# XRROS-S4B-D4Q2-1.0.0 — prospective D4 B1 transport correction and targeted requalification

This protocol amends only the D4 source-sender transport of XRROS-S4B-D4Q1-1.0.0. Research policy XRROS-S4-1.0.0 (SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`) is unchanged. So are the D4 fixture, conditions, profiles, thresholds, uncertainty rules, predicate, official monitor/oracle, receiver/mapper/bridge wrappers, stop adapter, drain and the rest of the analyzer. D4Q1's 18 qualified and 2 blocked cells remain immutable.

## Causal hypothesis

The original Docker receiver closes a TCP client after 1.5 s with no bytes. D4 B1 I_FULL correctly withholds all 36 teleop samples in the rejection cells, which is 1.8 s. The D4Q1 sender then wrote into the closed socket and crashed (`BrokenPipeError`). The tail samples were never delivered, and the source record was incomplete.

## Correction

`inputs/d1_sender.py` changes in one way. Before each **real** transmission, it runs a non-blocking `select` plus `MSG_PEEK` to detect a peer-closed socket. If the peer has closed, it reconnects once and logs `reconnect_after_peer_close` with `before_index` to `sender_transport.jsonl`. Each sent row also records `connection_index`.

There is no retransmission, and the payload, stamp, generation ID and schedule are unchanged. The Docker source has no connection-generation field, and the tail after the reconnect is ungripped neutral. The reconnect is therefore not a D5 generation test and does not re-arm control.

The analyzer adds one check: a reconnect is legal only in B1 and only after at least 1.5 s of withheld samples. Anything else is `UNEXPLAINED_SENDER_RECONNECT`. The runner prefix changes to `s4cp18d4q2_`.

Host evidence (`preflight/host_regression.*`, 12/12 PASS) includes a loopback test that reproduces the original 1.5 s idle drop. In it, B1 I_FULL A750/F250 reconnects exactly once, before index 56, and every transmitted sample is received once. With no gap there is no reconnect.

## Targeted requalification

`qualification_schedule.csv` lists five cells:

- a fresh B0/shim pair at A750/F250, for the equivalence limits (5 ms, 0.02 rad);
- the two blocked cells, B1 I_FULL at A750/F250 and at A150/F100;
- B1 I_FULL at A000/F250, as an unchanged-path positive control that must still move.

Other D4Q1-qualified configurations use a byte-identical path except for a no-op `select` per send. Their D4Q1 qualification is reused only for the configuration evidence; they are not re-run. Each cell allows at most two retries, only before the barrier.

Formal D4 may be frozen only after all five cells qualify. D4 formal uses this D4Q2 implementation for every arm.
