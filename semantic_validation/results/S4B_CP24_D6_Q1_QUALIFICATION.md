# CP24 Docker D6Q1 setup result: 14/14 qualified

The campaign was frozen at `d5fd00b29a7187174cfa9f89ff123796f7254926`. All 14 first attempts ran once, reached the barrier and exited 0, and no retry was needed. The result is **D6_SETUP_COMPLETE**, with all 14 cells MEASUREMENT_QUALIFIED. The B0/shim pair passes, at 0.0568 ms and 0.004354 rad.

B1 I_FULL withholds slots 56–91 under R_EXPLICIT and 56–86 under R_AUTO. In both cases the source reconnected once, after the original receiver's 1.5 s idle drop, and the reconnect is legal under the idle-time rule, with the receiver's drop log matching one-to-one. No other cell reconnected.

Evidence is in `runs/s4b_cp24_d6q1_20260928T141053Z/`, with `raw/`, `analysis/d6_setup_summary.json` and `runtime_evidence_manifest.sha256`, which verifies. This is setup qualification only, not a policy score.
