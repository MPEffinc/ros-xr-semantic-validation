# Spes Quest Hardware Quantitative Summary

표본은 한 Quest 3 session의 valid T1 5회다. 아래 값은 descriptive summary이며 population inference 또는 유의성 검정이 아니다.

## Rates

- Emulated occurrence: `100%` (5/5)
- Downstream continuation: `100%` (5/5)
- No-user-rearm: `100%` (5/5)
- Jump-reject occurrence: `80%` (4/5)

## Descriptive metrics

| Metric | Mean | Median | Max |
| --- | ---: | ---: | ---: |
| Max linear target delta per trial (m) | 0.042538 | 0.038808 | 0.066858 |
| Max angular target delta per trial (rad) | 0.100209 | 0.092284 | 0.140119 |
| Loss→reacquired (ms) | 1604.3 | 1510.6 | 1989.3 |
| Emulated interval (ms) | 1604.3 | 1510.6 | 1989.3 |
| Reacquired→first accepted callback (ms) | 0.000 | 0.000 | 0.000 |
| Reacquired→recovery completion (ms) | 2508.9 | 2510.8 | 2511.6 |
| Longest callback interruption per trial (ms) | 28.545 | 31.241 | 46.114 |
| Longest rejected run per trial (frames) | 2.6 | 3.0 | 4 |
| Control packet progression | 367.8 | 359.0 | 403 |
| Server update progression | 368.0 | 360.0 | 403 |

Callback interruption은 loss detection부터 trial completion까지 연속 `callback_emitted=false` frame이 다음 accepted callback을 만날 때까지의 server monotonic duration으로 정의했다.

Machine-readable source: `/home/cclab/ros_xr/semantic_validation/logs/reanalysis/reanalyze_spes_hw_20260831T152922Z/reanalyzed.json`.
