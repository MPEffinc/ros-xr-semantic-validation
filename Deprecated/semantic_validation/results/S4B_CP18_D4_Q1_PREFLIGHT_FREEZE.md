# CP18 Docker D4Q1: source-freshness preflight and prospective setup freeze

**PREFLIGHT PASS. D4Q1 Gazebo qualification and D4 formal NOT_STARTED at this freeze.** Protocol XRROS-S4B-D4Q1-1.0.0 has SHA-256 `0d007be11008f0fc4b29db0517083c6ecc3550f0ed6faba58ed9249cbf925286` (`S4B_CP18_D4_Q1_QUALIFICATION_PROTOCOL.md`). It instantiates, without changing, XRROS-S4-1.0.0's D4 conditions:

- ages 0/50/150/350/750 ms;
- the historical epoch value 1.0, kept separate from an age offset;
- +1 s future;
- profiles F100/F250/F500;
- inclusive thresholds;
- a [−5 ms, 0] future tolerance;
- a 1 ms uncertainty band, inside which decisions are UNKNOWN.

The D3 formal result (commit `6f43392f4746ee9cad27f6f5fd621f694332064b`) and all earlier results are unchanged.

The root is `runs/s4b_cp18_d4q1_20260928T050614Z/`. `inputs/` started as a byte-identical copy of the Q6 inputs. `preflight/q6_to_d4q1_input_delta.txt` shows that only the declared files differ or are new:

- `d1_sender.py`
- `d1_contract.py`
- `d1_probe.py`
- `servo_callback_drain.py`
- `run_owned.py`
- `d4_age.py` (new)
- `d4_monitor_freshness_preflight.py` (new)
- `run_qualification.py` (new)

The vendor source, official monitor YAML/install, oracle property file, receiver/mapper/bridge/Stripper wrappers, stop adapter, Servo hook and tick publisher are unchanged.

## No-Gazebo preflight evidence

**Genuine official path.** The actual generated `d3_full_guard`/`d3_native_guard` monitors and the official TLOracle ran in trial-owned `--network none` containers (`preflight/official_{full_F100,full_F250,full_F500,native_F250}_freshness/`, with exact argv in `command.json`). All four returned PASS_COMPONENT_PREFLIGHT.

In I_FULL, under every profile:

| Event | Property | Official status | Guarded receipt |
| --- | --- | --- | --- |
| Age 0 | `VALID_D1`, safe | `forwarded` | yes |
| F − 20 ms | `VALID_D1`, safe | `forwarded` | yes |
| F + 30 ms | `STALE_SOURCE` | `blocked` | none |
| −1 s | `FUTURE_TIME` | `blocked` | none |
| Historical 1.0 s | `STALE_SOURCE` | `blocked` | none |
| Stale but ungripped | safe (intentional neutral) | `forwarded` | yes |
| Original neutral | safe | `forwarded` | yes |

Each message carried a freshly regenerated ROS header stamp, and age came from the original source stamp. In I_NATIVE, every event is forwarded with `NATIVE_WIRE_ONLY_UNOBSERVABLE_SOURCE_RECEIPT`, so freshness is unobservable to the defense.

**Host regressions** (`analysis/test_d4_preflight.py`, `preflight/host_regression.*`), 10/10 PASS:

- **Predicate:** under each profile, the threshold is inclusive (F accepted, F+1 ns rejected); −5 ms is accepted and −5 ms − 1 ns is rejected; future and historical stamps are rejected; stale-but-ungripped is intentional neutral; the default is F250.
- **Analyzer expectation:** the uncertainty band behaves as registered.
- **Sender loopback:** real TCP loopback ran for all seven conditions. The recorded stamp equals the wire stamp for every sample. Stamps are per-sample, and H1P0 alone reuses the literal value. B1 I_FULL withholds teleop samples 20–55 exactly when age exceeds F:
  - withheld: A350, A750, H1P0, FUT1S at F250; A150 at F100;
  - not withheld: A000, A050, A150 at F250; A350 at F500; A050 at F100.
  - B1 I_NATIVE and B0 never withhold.
- **Joins:** the D4 drain and callback joins accept a decoupled recorded stamp and reject a stamp mismatch.
- **Negative fixtures:** the fixture check rejects a regenerated stamp, a reused stamp and a wrong condition label.

The first regression run had 1/9 FAIL. It exposed a host-analyzer defect: the frozen Q6 analyzer import chain shadowed the D4 `servo_callback_drain`. The container runtime is not affected. The fix is an explicit import order plus a test that every module resolves to the D4 root. The rerun passed.

**Other checks.** The empty schedule returns NOT_RUN, and the Q1 official install hashes still match (`preflight/official_install_hash_check.stdout`).

## Frozen setup schedule and gate

`qualification_schedule.csv` lists 20 first-attempt cells:

- all ten configurations at A000/F250;
- B0/shim and the four I_FULL defenses at A750/F250;
- B1 full at A150/F100;
- B3 full at A350/F500;
- B2-composed full at H1P0/F250;
- B2-native full at FUT1S/F250.

Retries are pre-barrier only, at most two per cell. `freeze_inputs.sha256` covers:

- the protocols;
- all inputs and analysis files;
- the imported Q6/Q3/Q4 analyzer modules;
- the schedule;
- the component and regression evidence;
- this report.

The freeze must be committed and pushed, and local HEAD, `origin/main` and remote main must be equal, before the first D4Q1 Gazebo cell. Setup qualification is not a freshness-policy result. D4 formal needs a separate five-repetition schedule and policy analyzer, frozen afterwards. S5 remains INSUFFICIENT_EVIDENCE.
