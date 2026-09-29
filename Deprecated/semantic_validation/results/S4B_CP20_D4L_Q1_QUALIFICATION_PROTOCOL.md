# XRROS-S4B-D4LQ1-1.0.0 — prospective Docker D4-L post-gate delivery-delay setup qualification

This campaign instantiates XRROS-S4-1.0.0 D4-L and does not change it. The research protocol SHA-256 is `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`.

The registered D4-L case is: "Same fresh sampled trajectory, queue delivery by 0, .05, .15, .35, .75 s **after** the B1 source decision; source stamp unchanged. Judge age at consumer as well as each gate. Distinguish delivery delay from old-but-prompt source stamps. Test current-time restamp does not conceal true age." The protocol also fixes the capture length: base fixture plus the registered delay plus 2 s, identical across arms at that delay. Queues are FIFO, with no early burst-drain and no restamp at release. F100/F250/F500 all apply.

D4 formal (`S4B_CP19_D4_FORMAL_FREEZE.md`) and all earlier results are unchanged.

## Implementation (declared delta vs D4Q2 inputs)

- **`d4l_timing.py`** holds the delay table L000/L050/L150/L350/L750. The capture length is 4.8 s + delay + 2 s, with ticks at 50 Hz. Without `XR_DELIVERY_DELAY`, the D4Q2 values (6 s, 300 ticks) are reproduced exactly.
- **`d1_sender.py`**, only when `XR_DELIVERY_DELAY` is set:
  - The sender queues every **allowed** sample after the B1 decision and releases it FIFO at `sample_ns + delay`.
  - The stamp is unchanged and fresh (condition A000).
  - Each release is logged in `delivery.jsonl`.
  - Without the variable, the direct-send path is identical to D4Q2.
- **`d1_probe.py`, `d1_stop_adapter.py`, `d3_tick_publisher.py`** take the capture end and tick count from `d4l_timing`.
- **`run_owned.py` and `run_qualification.py`** gain `--delay`, `XR_DELIVERY_DELAY` and the `s4cp20d4lq1_` prefix.

The following are unchanged: the receiver, mapper and bridge wrappers, the official monitor and oracle property, the predicate, the stop logic apart from the window length, and the Servo hook.

The analyzer (`analysis/d4_setup_audit.py`) adds a per-trial tick count derived from the registered delay. It uses a parameterized `monitor_events`, which is shown equal to Q6's frozen version at 300 ticks on real D4Q1 raw. It also adds a delivery audit: FIFO order, every allowed sample released once, the due time equal to `sample_ns + delay`, no early release, and lateness reported. B0/shim pairs are grouped by delay. `post_capture_audit` takes the tick count, with 300 as the default.

## Host preflight

`analysis/test_d4_preflight.py` passes 16/16, covering:

- all D4Q2 regressions;
- the timing values: 6 s/300 ticks by default, 7.55 s/377 ticks at L750, 6.8 s at L000;
- a delayed loopback at L000, L350 and L750. B1 decides on fresh input (age < 5 ms) and accepts all 120 samples. Every release happens at or after `sample_ns + delay`, in FIFO order, with the stamps unchanged;
- delivery-audit negatives for an early release and for reordering;
- `monitor_events` equivalence with Q6.

The first attempt, retained as `preflight/host_regression_attempt1_failed.*`, failed one assertion: a 24.7 ms release lateness measured while the D4 formal Gazebo run was loading the host. Reruns gave a median of 0.08–0.18 ms and a maximum below 1 ms. Lateness is therefore reported rather than used as a validity gate, because policy is judged on the measured source age at each boundary.

## Setup schedule and gate

`qualification_schedule.csv` lists 15 cells:

- all ten configurations at L750/F250. B0, the shim and every I_NATIVE arm plus B1 I_FULL must move. B2, B2-composed and B3 I_FULL need not move;
- a B0/shim pair and B3 I_FULL at L000/F250;
- B2-composed I_FULL at L150/F100;
- B3 I_FULL at L350/F500.

Each cell allows at most two retries, and only before the barrier. Each B0/shim pair must be within 5 ms and 0.02 rad. The qualification runs only **after the D4 formal run completes**, so the two campaigns do not share host load. D4-L formal requires a separate freeze. This setup campaign is not a policy score.
