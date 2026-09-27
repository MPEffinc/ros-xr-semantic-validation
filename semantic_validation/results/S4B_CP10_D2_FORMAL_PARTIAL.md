# S4-B CP10: Docker D2 frozen formal comparison

**Result: PARTIAL — 50 executed, 47 VALID_FORMAL_TRIAL, 3 INVALID_COMPARISON.** The original XRROS-S4-1.0.0 policy (SHA-256 `3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`) was not changed. Prospective implementation/schedule freeze `XRROS-S4B-D2F1-1.0.0` was committed and pushed as `f9e24c4b7d20ddee004a43326dc25f9a0eb5e871` before the first formal row. This is a new *synthetic-input, original Docker receiver/mapper/bridge → MoveIt Servo → Gazebo* experiment; it is neither actual Quest tracking loss nor physical-robot evidence. The original D1 campaign remains 50 executed/48 valid/2 invalid and is not pooled here.

## Design and execution

The trial-owned root is `runs/s4b_d2_formal_20260927T022400Z/`. The committed `schedule.csv` (SHA-256 `23a9d0a19e7f1626ea64abe5bcd1a103b4f330468d802791af53b61996990892`) contains five randomized repetitions of ten arms: B0 original, B0 observational shim, B1 I_NATIVE/I_FULL, official ROSMonitoring B2-native I_NATIVE/I_FULL, official ROSMonitoring plus ordinary health/stop integration B2-composed I_NATIVE/I_FULL, and B3 I_NATIVE/I_FULL. It uses seed 20260922. The normalized 120-index D2 fixture SHA-256 is `b92f6adc3a046c734ca6db937416665c8f3d4c9add5d4dd61b3be2a7cbe0191c`; active motion precedes `isTracked=false` at indices 56–75. The same Q3-qualified original `/code`, official monitor/oracle, Servo/controller image, no-network Gazebo-only launch, start ACK and clock checks were used for every arm. Each new container and its logs were retained. All 50 launches exited zero; each trial had 120 source indices and complete 100 ms resource capture. Launch success alone is not a policy verdict.

Commands and all actual Docker argv are in `runtime_commands.txt` and `commands.jsonl`; `raw/<trial_id>/` contains input, lineage, official monitor property/status when applicable, original/Servo/controller/joint records, resource/clock logs, stdout/stderr and exits. The frozen `analysis/formal_audit.py` produced `analysis/formal_summary.json`; it was not edited after freeze. The 54-entry `freeze_inputs.sha256` still verifies. The post-runtime `runtime_evidence_manifest.sha256` covers every new raw and analysis result. No raw record was removed or replaced.

## Comparison validity and policy observations

All five B0/shim pairs PASS the frozen 5 ms source schedule and 0.02 rad final per-joint criteria: maximum across pairs **0.504 ms** and **0.003239 rad**, respectively. All 45 matched source-schedule arm pairs PASS. B0 pre-fault Gazebo joint velocity was observed in every repetition (0.190–0.201 rad/s), establishing the moving fault condition. Source→original publication→Servo callback association is exact where IDs were recorded; Servo-output, controller-output and joint observations are separate interval consequences, not per-source causal joins.

| Arm | Valid / executed | Frozen policy result on valid trials | Maximum observed neutral request / settling after trigger |
| --- | ---: | --- | --- |
| B0 original | 5/5 | Control, not scored as a defense | Not applicable |
| B0 observational shim | 5/5 | Nondefensive equivalence control | Not applicable |
| B1 I_NATIVE / I_FULL | 5/5 each | 10 PASS_POLICY | 4.905 ms / 36.539 ms |
| B2-native I_NATIVE | 3/5 | 3 FAIL_POLICY; 2 INVALID_COMPARISON | No explicit neutral request / 297.213 ms |
| B2-native I_FULL | 4/5 | 4 FAIL_POLICY; 1 INVALID_COMPARISON | No explicit neutral request / 293.898 ms |
| B2-composed I_NATIVE / I_FULL | 5/5 each | 10 PASS_POLICY | 22.347 ms / 55.479 ms |
| B3 I_NATIVE / I_FULL | 5/5 each | 10 PASS_POLICY | 16.284 ms / 48.255 ms |

Across valid defense-arm trials the frozen scorer found zero explicit false rejection among eligible valid active source IDs and zero *new forbidden-source* nonzero Servo callbacks after local invalid observation. It separately retained 12–15 post-detection nonzero callbacks parented to an **earlier accepted cached source**; these are not relabelled as commands from the rejected sample. B1, B2-composed and B3 had an observed stop/neutral request and settled under the registered limit in their valid trials. All seven valid B2-native trials lacked the registered explicit neutralization request, hence FAIL_POLICY even though the original receiver/Servo timeout later yielded an interval-level settling observation. That ordinary timeout is not credited to the ROSMonitoring filter. The B2-composed result is official ROSMonitoring **plus** separate generic health/stop integration, not ROSMonitoring's native failure behavior. This case alone does not measure sender stall, oracle disconnection, freshness, re-arm or recovery.

The exact official monitor internal post-verdict publish timestamp and exact incremental added gate/transport latency remain UNKNOWN. The recorded source-to-first-Servo-callback p95 is descriptive, not substituted for that target. CPU/RSS raw is present per trial; no cross-arm overhead conclusion is drawn without an appropriate matched estimator. Normal source-state information is comparable within each I_NATIVE or I_FULL regime, not across regimes as though they were identical.

## Three retained invalid comparisons

The frozen scorer classified these as `B2_EVENT_ASSOCIATION_INCOMPLETE`; none is silently excluded from the 50 executed or counted as a policy failure.

| Trial | Exact raw boundary | What remains unknown |
| --- | --- | --- |
| `docker_b2_native_d2r01` | An original `stale_timeout` neutral, payload SHA-256 `8479fc72be6dd4093593d24f7ff8421cb5575ca8b59d00e2586da1737a25c22b`, was logged at barrier +9.188 s. Oracle property was safe=true, generated monitor status was `forwarded`, but no matching guarded downstream receipt was logged. | Whether the monitor/DDS did not deliver it or the downstream observer missed it. |
| `docker_b2_full_d2r01` | Original envelope event ID `2929602790856460`, payload SHA-256 `40fdf8e01403ccd1936c55f2a7ad0fd2e2a16da173ffa918ccd90676bc59aa9e`, was logged at barrier +9.230 s, with no matching oracle property or official status. | Whether it reached the official monitor subscription; a receiver publish log alone proves no such receipt. |
| `docker_b2_native_d2r03` | Original `stale_timeout` neutral, payload SHA-256 `310f523b46a77c10e34c26ef1a2681bee48cc3e8d0168ed0f844bb35bb7828cc`, was logged at barrier +9.226 s, with no matching oracle property/status or downstream receipt. | The precise loss/observation boundary. |

These were original-generated neutrals, **not sender source samples**, and occurred after the controlled six-second source sequence. Timing suggests a lifecycle boundary worth testing, but does not prove a shutdown race or monitor defect. A new prospectively frozen diagnostic must distinguish actual DDS delivery from recorder loss before any supplemental comparison. Do not relax completeness or replace these trial IDs; the current D2 result stays 47/50 valid.

## Evidence boundary and next action

The valid Docker D2 subset supports a limited claim: with this registered synthetic invalid-tracking fixture and equal within-regime source information, B1, B2-composed and B3 met the frozen stop policy, while B2-native filtering alone lacked an explicit neutralization request. It does **not** establish an XR-hardware or cross-stack method gap. The conventional composed solution worked in this condition; `NO_METHOD_GAP` remains possible. S5 remains INSUFFICIENT_EVIDENCE. D3 moving source-silence tick/health integration and qualification is the next independent fault case; first run no-Gazebo tick/no-byte tests and freeze a separate implementation. In parallel, targeted monitor-path diagnostics may explain the three D2 neutral gaps, but no unchanged repeated trial or post hoc analyzer rewrite is justified.
