# Evidence Levels V2 and Claim Boundary

## Level definitions

| Level | 이름 | 이 연구에서 허용하는 claim | 허용하지 않는 claim |
| --- | --- | --- | --- |
| E0 | `DISCOVERED` | repository/document identity를 발견함 | production dataflow, runtime, hardware |
| E1 | `SOURCE_DATAFLOW_CONFIRMED` | pinned production source/config/callback/dataflow를 연결해 확인함 | runtime behavior 또는 hardware result |
| E2 | `SYNTHETIC_RUNTIME` | synthetic/test-double source로 production component/path를 실행함 | actual XR hardware 또는 actual ROS transport |
| E3 | `CONTROLLED_REPLAY` | production-compatible path의 trace replay 결과와 injection boundary | native XR end-to-end unless injection is proven upstream of all relevant logic |
| E4 | `HARDWARE_DERIVED_TRACE_REPLAY` | actual Quest raw trace를 record/replay함 | replayed framework가 native Quest frontend를 실행했다는 claim |
| E5 | `NATIVE_XR_TO_ROS` | actual Quest → framework-native frontend → native transport/bridge → actual ROS publish/receive | native downstream consumer acceptance 또는 actuator behavior |
| E6 | `NATIVE_XR_TO_NATIVE_CONSUMER` | actual Quest → native framework/control path → original downstream software consumer acceptance | physical actuator execution unless separately observed |

Physical actuator evidence는 이 project의 requirement가 아니다. 필요한 경우 only a
stub/mock/no-op endpoint at the pre-write boundary may yield
`ACTUATOR_STUB_COMMAND`; it is not robot movement.

## Replay subclasses

| Replay class | 조건 | interpretation |
| --- | --- | --- |
| `UPSTREAM_FAITHFUL_REPLAY` | chosen injection point가 relevant native semantic decision/gate 이전이고 that logic remains active | E3/E4 replay evidence; still not native hardware evidence |
| `BOUNDARY_LIMITED_REPLAY` | injection이 relevant gate 이후이거나 native semantic source/gate 일부를 bypass | boundary 이후 behavior만 evidence; native-gate outcome로 보고 금지 |

모든 E3/E4 record에는 source of trace, injection point, active native logic, bypassed
native logic, exact downstream boundary가 필요하다. canonical replay가 Transform/packet
후에 주입되어 prior `isTracked`/validity gate를 건너뛰었다면 outcome은 반드시
`BOUNDARY_LIMITED_REPLAY`다.

## Orthogonal result axes

### Semantic disposition

`PRESERVED`, `TRANSFORMED`, `REVALIDATED`, `GATED`, `DROPPED`, `UNKNOWN`, `N/A`.

### Downstream consequence

`NO_OUTPUT`, `APP_OUTPUT`, `TRANSPORT_SENT`, `ROS_PUBLISHED`, `PI_RECEIVED`,
`NATIVE_CONSUMER_ACCEPTED`, `ACTUATOR_STUB_COMMAND`, `UNKNOWN`, `N/A`.

Pi `semantic_robot_sink` sets only `PI_RECEIVED`: its implementation is an observation
endpoint with `ACCEPTED_NO_SEMANTIC_GATING`, not an original controller or safety
consumer. It must never be renamed `ACTIONABLE`, `UNSAFE`, `ROBOT_COMMAND_EXECUTED`, or
`ACTUATOR_EXECUTED`.

## Evidence record minimum fields

Each finding/report must contain:

1. finding or run id and pinned revision;
2. E-level plus replay subclass where applicable;
3. exact start/end boundary and observables used;
4. raw semantic mapping and its confidence;
5. semantic disposition and downstream consequence as two values;
6. valid/excluded trial counts for hardware experiments;
7. alternative explanations, blockers, and what was not observed;
8. artifact paths, command/environment identity, and non-interference status.

`PASS` means the stated checker/test passed at its own evidence level. It never upgrades a
stack-wide invariant, a blocker, a replay, or a static assertion to E5/E6.

## Legacy evidence migration

Prior names in `results/EVIDENCE_LEDGER.md` are retained as historical artifact labels.
V2 reports map them conservatively: `MACHINE_CHECKED_STATIC` → E1 where connected
production dataflow was confirmed (otherwise E0/static context); `RUNTIME_SYNTHETIC` and
`CONFIRMED_RUNTIME_SYNTHETIC_SOURCE` → E2; actual Quest to Spes server callback is
hardware evidence below E5 because no actual ROS boundary was included. Existing ledger
is not rewritten as a hardware ROS claim.

## Claim discipline

Without matching evidence, do not use: `vulnerable`, `unsafe`, `robot moved`, `actuator
executed`, `actual hardware confirmed`, `end-to-end confirmed`, `general across XR-ROS`,
`fail-safe`, or `secure`. Use the E-level, exact boundary, and unresolved condition instead.
