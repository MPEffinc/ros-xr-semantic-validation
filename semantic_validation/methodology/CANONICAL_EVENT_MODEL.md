# Canonical Event Model V2

## 설계 원칙

이 모델은 universal raw-XR schema가 아니다. API별 raw semantic을 `native_semantics.raw`
에 원형대로 보존하고, 비교가 가능한 경우에만 별도 `canonical_event` transition
category를 부여한다. 존재하지 않는 raw field를 추측하거나 `AMBIGUOUS`/`UNMAPPED`를
강제 변환하지 않는다.

특히 `WebXR emulatedPosition`, OpenXR `POSITION_VALID`/`POSITION_TRACKED`, Unity
`isTracked`/`trackingState`, Meta SDK `IsTracked`, hand confidence/status는 자동으로
동등하지 않다. mapping evidence는 framework별 `SEMANTIC_MAP.md`에 남긴다.

## Event envelope

아래는 JSONL 한 record의 normative shape다. framework가 제공하지 않는 값은
`null` 또는 `inapplicable`로 두며 invented default를 넣지 않는다.

```json
{
  "run_id": "uuid-or-stable-run-id",
  "event_seq": 100,
  "capture_monotonic_ns": 0,
  "clock_domain": "unity_monotonic|openxr|browser_performance|host_monotonic",
  "native_semantics": {
    "api": "OpenXR|WebXR|UnityXR|MetaSDK|other",
    "raw": { "position_valid": true, "position_tracked": false }
  },
  "canonical_event": {
    "type": "SPATIAL_TRACKING_DEGRADED",
    "mapping_confidence": "DIRECT",
    "mapping_evidence": "framework/SEMANTIC_MAP.md#..."
  },
  "source": {
    "native_id": "optional-opaque-id",
    "kind": "controller|hand|hmd|fallback|unknown",
    "side": "left|right|none|unknown"
  },
  "pose": { "frame": "native frame if available", "position": null, "orientation": null },
  "source_time": { "value": null, "clock_domain": null, "sequence": null },
  "control": { "enabled": null },
  "lifecycle": { "focus": null, "session": null, "transport_generation": null }
}
```

`capture_monotonic_ns`는 capture process의 monotonic ordering 용도이며, remote ROS
wall clock이나 hardware source timestamp와 같다고 가정하지 않는다.

## Canonical transition type

| Type | 의미 | prerequisite |
| --- | --- | --- |
| `VALID_BASELINE` | framework native definition의 정상 spatial/control state | raw evidence와 mapping 필요 |
| `SPATIAL_TRACKING_DEGRADED` | spatial tracking quality/validity의 저하 | API-specific raw state transition |
| `SOURCE_TRANSITION` | source kind/side/device/fallback 전환 | native source evidence |
| `FRESHNESS_STALL` | stale, stalled, replayed, future source sample | source-time/sequence contract가 있는 boundary |
| `TRANSPORT_RECONNECT` | transport disconnect/reconnect 또는 registration generation 변화 | transport lifecycle evidence |
| `SESSION_INVALIDATION` | focus/background/pause/XR session invalidation | framework lifecycle concept |
| `RECOVERY` | preceding degradation/invalidation 뒤 recovery behavior | prior transition과 correlation |

`type`은 observed raw state를 대체하지 않는다. 예를 들어 `SPATIAL_TRACKING_DEGRADED`
record는 `position_valid=true`, `position_tracked=false`라는 OpenXR raw bit가 무엇을
의미하는지와 별개로 기록되어야 한다.

## Mapping confidence

| 값 | 사용 조건 |
| --- | --- |
| `DIRECT` | raw API field/event 자체가 canonical transition을 직접 표현한다. |
| `DOCUMENTED_EQUIVALENCE` | vendor/API 문서가 mapping의 의미를 명시한다. 문서 URI/revision을 함께 남긴다. |
| `IMPLEMENTATION_INFERRED` | source code/dataflow로 추론했으나 API-level equivalence는 직접 확인되지 않았다. |
| `AMBIGUOUS` | 둘 이상의 raw interpretation이 남는다. canonical 판정을 강제하지 않는다. |
| `UNMAPPED` | raw semantic 또는 mapping evidence가 없다. |

`DIRECT`와 `DOCUMENTED_EQUIVALENCE`만으로 cross-framework raw-field equality를
주장하지 않는다. 둘은 transition-category comparison에 충분한 confidence 수준일 뿐이다.

## Invariant binding

각 event 또는 event interval은 다음 invariant axis와 optional binding을 가진다.

| Invariant | Event model에서 확인할 값 |
| --- | --- |
| I1 tracking state | `native_semantics.raw`, `canonical_event`, pose/output gate |
| I2 source identity | `source.native_id/kind/side`, frame/modality transformation |
| I3 source-time/freshness | `source_time`, re-stamp/age gate/sequence policy |
| I4 session/generation | `lifecycle.session`, `transport_generation`, reset/registration behavior |
| I5 invalidation/re-arm | `control.enabled`, lifecycle invalidation, recovery and output policy |

Canonical event은 raw observation layer이고, invariant disposition은 production path
audit/runtime evidence에 근거한 result layer다. event 하나만으로 `DROPPED`를
판정하지 않는다.

## Cross-stream correlation

XR raw, application sideband, serialized packet, ROS, Pi, native consumer record는 모두
`run_id`를 보존한다. 한 stream이 `event_seq`를 전달하지 않으면 payload digest,
application sequence, causal marker, 명시한 offset으로 상관하고 방법을 run report에
적는다. 서로 다른 wall clock을 직접 빼서 latency 또는 causal ordering을 주장하지
않는다.

## Trace provenance

| Provenance | 허용 claim |
| --- | --- |
| `SYNTHETIC_CANONICAL_EVENT` | framework-native raw field가 아닌 controlled input/test double임 |
| `CONTROLLED_REPLAY` | chosen injection point와 bypassed logic까지 포함한 replay evidence |
| `HARDWARE_DERIVED_TRACE` | actual Quest raw trace를 기록했음; 다른 framework native frontend 실행 증거는 아님 |
| `NATIVE_HARDWARE_EVENT` | actual Quest가 해당 framework native frontend를 실행했고 raw event를 생성했음 |

`HARDWARE_DERIVED_TRACE`를 다른 framework에 replay해도 E5/E6으로 승격하지 않는다.
