# Cross-stack normalized comparison

> Superseded by [`INVARIANT_MATRIX.md`](INVARIANT_MATRIX.md), which incorporates actual Quest evidence, PickNik connected-dataflow validation, NVIDIA revalidation, and the current evidence-level boundaries.

Canonical run: [`no_quest_20260830T142000Z`](../logs/no_quest/no_quest_20260830T142000Z/integrated_summary.jsonl). `R-SYN`은 actual target path + synthetic source, `SM`은 machine-checked static, `S`는 static, `HW`/`ENV`는 blocker다.

| Property | Spes | PickNik | Quest2ROS2 | NVIDIA |
| --- | --- | --- | --- | --- |
| Tracking validity | dropped — `R-SYN`; activation `HW` | absent in publisher — `SM`; behavior `HW` | not represented — callback `R-SYN`, producer `U/HW` | partial gate — release `S`, main `R-SYN` |
| Tracked vs inferred | dropped — `R-SYN`; actual emulation `HW` | dropped — `SM/HW` | not represented — `S`, producer `U/HW` | not preserved — `S/HW` |
| Source identity | controller/viewer collision — `R-SYN` | left/right only — `SM` | input frame dropped — `R-SYN` | left/right preserved — `S`; generation `U` |
| Source timestamp | absent — `R-SYN` | publication time only — `SM` | input stamp dropped — `R-SYN` | internal yes, ROS no — `S` |
| Freshness guard | absent, delayed accepted — `R-SYN` | absent — `SM` | absent, 10 s/future accepted — `R-SYN` | not found — `S` |
| Re-stamping | ROS wrapper now — `S/ENV` | `DateTime.UtcNow` — `SM` | callback now — `R-SYN` | ROS/payload now — `S` |
| Session isolation | no reconnect binding — `R-SYN` | registration delay only — `S`, runtime `ENV` | `U`; producer absent | inactive clear partial; reconnect generation `U` |
| Control invalidation | explicit move gate; source loss not coupled — `R-SYN` | pose invalidation hook absent — `SM/HW` | local allow gate — `S` | invalid grip hold/zero/rebaseline — main `R-SYN` |
| Reference identity | absent — `R-SYN` | fixed `quest`/child — `SM/HW` | input frame replaced — `R-SYN` | not end-to-end — `S/HW` |
| Runtime confirmed | frontend + actual WSS/server — `R-SYN` | no — `ENV` | actual callback only — `R-SYN`; ROS `ENV` | main pure-Python 10 tests — `R-SYN` |
| Needs Quest | actual controller loss/emulation/fallback activation — `HW` | Unity Transform during loss — `HW` | XR producer semantics — `HW/U` | native OpenXR/DeviceIO activation — `HW` |

## Cross-stack conclusion

1. Spes와 Quest2ROS2에서는 semantic distinction의 부재가 실제 target logic 실행 결과로 승격됐다.
2. PickNik은 같은 pattern을 source-level machine check로만 확인했으며 runtime으로 승격하지 않았다.
3. NVIDIA current main은 invalid state를 hold/zero/absence/rebaseline으로 처리하는 partial positive control을 runtime으로 보였다.
4. 네 stack 모두 검사한 ROS boundary에서 source timestamp lineage와 tracked-vs-inferred semantics를 완전하게 보존하는 positive control은 아니었다.
5. 실제 Quest 상태 발생과 physical consequence는 어느 stack에서도 증명하지 않았다.
