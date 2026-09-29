# XRROS-S4B-CMONQ1-1.0.0 — prospective Docker C-MON monitor/oracle-failure setup qualification and design report

This setup campaign applies XRROS-S4-1.0.0 C-MON (research protocol SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`) without changing it. The registered C-MON case covers three conditions for B2-native and B2-composed:

- oracle absent at startup;
- oracle disconnect during active input;
- nonresponding oracle.

It also covers the matched B1/B3 gate-process failure diagnostic. The protocol asks us to record native behavior and the common-watchdog effect separately, and not to assume a runtime failure mode from static code. Invalidation rules treat source faults and monitor faults as distinct triggers. The B2-native configuration reports UNKNOWN, error or no-verdict results as it actually behaves. B2-composed treats that health event as a stop request. A missing gate heartbeat for 250 ms triggers the common watchdog, and that watchdog is not attributed to ROSMonitoring. D1–D6 and C-ID are unchanged.

## Source and faults

The source is the valid, bound C-ID fixture with no injection (`CID_KIND=NONE`). It runs at 20 Hz for 120 slots (6 s), with the active phase at x=.35 over slots 36–55. Valid source input continues throughout every fault, and all 120 samples must be transmitted and received, so no trial becomes a source-silence trial.

Faults are injected only into trial-owned processes by `inputs/cmon_fault.py`, which runs inside the trial container. The target PID is identified by the PID file written at the process's exec and by `/proc/<pid>/cmdline`.

| Fault | Injection (at slot 45, moving, unless noted) | Proof recorded |
| --- | --- | --- |
| `ORACLE_ABSENT` | `launch.sh` never starts the official oracle. | No oracle PID file; the oracle port refuses connections before the barrier and at slot 45; the official monitor logs `could not connect to oracle`; no oracle property record exists. The pre-barrier source-path ACK is the official `unknown`-forwarded status plus an exact guarded receipt, with **zero** property records. |
| `ORACLE_DISCONNECT` | SIGKILL of the official TLOracle. | The oracle is proven owned and healthy (property records increasing over the preceding 100 ms). The process is gone after the kill. The official monitor records `oracle_error`. |
| `ORACLE_NONRESPONSIVE` | SIGSTOP of the oracle. | The process is alive in state `T`. The monitor's configured 50 ms socket timeout applies, and it records `oracle_error`. |
| `B1_GATE_FAIL` / `B3_GATE_FAIL` | A marker file; the gate component stops producing decisions and passes input through. | This is a fail-open crash model for a check that is embedded in the source or receiving process. It tests the common 250 ms verdict-heartbeat watchdog. |

**Genuine official component measurement** (`preflight/official_full_cmon_*`): 20 events were sent before and 20 after each fault. The actual behavior, measured rather than presumed:

- `HEALTHY`: all `currently_true`, forwarded, ≤ 1.8 ms.
- `ORACLE_ABSENT`: every event `unknown`, **forwarded**.
- `ORACLE_DISCONNECT`: 20 `oracle_error` (`Connection to remote host was lost` / `socket is already closed`), then `unknown`, **forwarded**.
- `ORACLE_NONRESPONSIVE`: 20 `oracle_error` (`Connection timed out`), then `unknown`, **forwarded**, with added latency up to 58.9 ms.

The official implementation is therefore **fail-open** in all three oracle faults.

## Declared implementation delta versus the C-ID Q1 inputs

The full delta is in `preflight/cidq1_to_cmonq1_input_delta.txt`.

- **`launch.sh`:** omits the oracle for ORACLE_ABSENT, writes the oracle PID file, starts the injector, and exempts only the intentionally killed oracle from the required-running check.
- **`source_path_readiness.py`:** adds the ORACLE_ABSENT ACK variant described above.
- **`d1_probe.py`:** under oracle faults, the post-capture official-monitor drain is not required, because pre-fault association is audited offline. The probe records `cmon_monitor_drain_not_required_intended_oracle_fault`.
- **Gate-failure markers:** `cid_sender.py` and `d3_source_gate_tick.py` handle the B1 marker; `d1_nodes.py` handles the B3 marker.
- **Runner:** `run_owned.py` / `run_qualification.py` gain `--fault`, and the container prefix is `s4cp28cmonq1_`.

The following are unchanged: the official monitor, oracle and YAML (50 ms timeout, `action: filter`); the stop adapter (it stops on `unknown`/`error`/`currently_false` or on a missing heartbeat, and never on anything else); and the vendor code.

## Host preflight

- `analysis/test_cmon_injector.py`, 5/5 pass, using a stand-in process named like the oracle: owned and healthy followed by SIGKILL; SIGSTOP leaves the process in state T; absence proof; both gate markers; refusal to signal an unowned process, with that process left untouched.
- The stand-in is used for the injector only. The official fault behavior comes from the genuine component tests above.

## Analyzer

`analysis/cmon_setup_audit.py` checks:

- the fault proof;
- **pre-fault** complete official association (for ABSENT, every event `unknown`-forwarded with a receipt and no property record);
- source continuity (120/120);
- the unchanged C-ID Q1 checks: ACK/clock, ticks, CPU/RSS, exact source→Servo callbacks, producer quiesce and Servo drain;
- calibration. Under ABSENT, the chain is checked without the non-existent oracle-decision element, and this is recorded explicitly.

A record missing *because of* the injected fault is not a recorder failure.

## Design report (minimum-sufficient scaling)

**Candidate matrix:** 3 oracle faults × {B2-native, B2-composed} × {I_NATIVE, I_FULL}, plus 2 gate faults × {native, full}, plus B0/shim = 18 cells × 5 = 90 trials.

**Essential per repetition (12):**

- B2-native and B2-composed I_FULL × 3 oracle faults (6). These show native fail-open versus composed health stop.
- B2-native and B2-composed I_NATIVE × DISCONNECT (2). Monitor health is observable without source time, so this is the regime check.
- B1 I_FULL gate failure and B3 I_FULL gate failure (2). These exercise the common watchdog.
- B0/shim (2), which have no monitor and valid input.

**Omitted, registered as NOT_RUN:**

- I_NATIVE × ABSENT/NONRESPONSIVE. The health path (official status plus adapter) is the same code in both regimes, and DISCONNECT is tested in both.
- I_NATIVE gate failures. The crash model and watchdog are identical in both regimes.

**Proposed formal campaign:** 60 trials (12 × 5), about 1 h, run sequentially with no concurrent load.

**Claims supported and not supported:**

- Supported: measured B2-native fail-open or fail-closed behavior per fault; B2-composed health-stop timing; watchdog stop timing for gate failures; separation of oracle fault, monitor-health stop, watchdog and original/Servo timeouts.
- Not supported: other failure times; oracle crash loops; host-level failures; OpenVR; physical devices.

## Setup schedule and gate

`qualification_schedule.csv` lists 12 cells. Every cell is expected to move except B2-composed under ABSENT, which is expected to stop at the first unknown verdict. At most two retries are allowed, and only before the barrier. The B0/shim pair must match within 5 ms and 0.02 rad, and every cell must be MEASUREMENT_QUALIFIED. This is not a policy score.
