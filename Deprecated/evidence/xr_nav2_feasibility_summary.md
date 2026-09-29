# XR Mock -> HORUS -> Nav2 Canonical Evidence

## Canonical run

- Run ID: `xr-nav2-20260826T125755Z`
- Time: `2026-08-26T12:57:55.893Z` -- `2026-08-26T13:03:07.981Z`
- Result: `measurement_valid=true`, `trial_errors=0`
- Coverage: F0--F6, case별 5회, 총 `35/35` trial complete 및 cleanup clean
- Architecture: Mock OpenXR-style lifecycle -> actual HorusLink -> actual HORUS bridge/backend `Nav2ActionAdapter` -> actual Nav2 `NavigateToPose` -> `nav2_loopback_sim`
- Robot distance: 상수 속도 추정이 아니라 simulator가 발행한 실제 `/odom` 표본의 polyline 적분
- Hardware: XR hardware `false`; physical robot `false`

Fixed framework revisions checked clean by the runner:

| Component | Revision |
|---|---|
| `horus_ros2` | `eca75cbf559f09ff793d8993338b2f1ffed1adfd` |
| `horus` | `819cdfdc74f1a0c2bd73946dc14897a533f68b61` |
| `horus_sdk` | `f4f00dab41910676519d545515531ec243414044` |
| `compas_xr` | `b86e6fbbacdc8e84183fc08c846176a1c79304ca` |
| `compas_xr_unity_assembly` | `f1516ca568b101447507aebc28a594bdc358df3e` |

Runtime basis: ROS 2 Jazzy, Nav2 `1.3.12`, image `ros-xr-horus-nav2-jazzy:local`, ROS domain `95`, Docker `--network none`, official `nav2_bringup/tb3_loopback_simulation.launch.py`.

## Reproduce

From `/home/cclab/ros_xr`:

```bash
authorization_env/run_xr_nav2_feasibility.sh \
  --trials 5 \
  --cases F0,F1,F2,F3,F4,F5,F6 \
  --revocation-delay-sec 2 \
  --observation-sec 5 \
  --lease-ttl-ms 1200 \
  --timeout-sec 3600
```

The runner checks fixed revisions, reuses or builds the isolated image, starts actual HORUS and Nav2, writes the three evidence logs, continues across measurable case failures, and removes its process groups/container through traps.

## Results

Numbers are min / median / max over five independent trials. Distance is measured after the case event; `*` marks a 5 s right-censored observation and therefore a lower bound on continued travel.

| Case | Canonical outcome | Count | Post-event path (m) |
|---|---|---:|---:|
| F0 explicit cancel | `EXPLICIT_CANCEL_SAFE` | 5/5 | 0.066757 / 0.079426 / 0.084921 |
| F1 focus loss only (P1) | lease retained, Goal `EXECUTING`* | 5/5 | 2.351485 / 2.357993 / 2.371290* |
| F2 focus loss + release (P2) | lease revoked; no Nav2 cancel; Goal `EXECUTING`* | 5/5 | 2.351388 / 2.363350 / 2.372768* |
| F3 STOPPING + disconnect (P2) | lease removed; no Nav2 cancel; Goal `EXECUTING`* | 5/5 | 2.344652 / 2.359485 / 2.362556* |
| F4 heartbeat stop / TTL | no Nav2 cancel; Goal naturally `SUCCEEDED` | 5/5 | 1.734535 / 1.757236 / 2.008395 |
| F5 authority handoff | B preempted A; A `ABORTED`, B `EXECUTING`* | 5/5 | 0.624602 / 0.629290 / 0.659297* |
| F6 epoch capability probe | stale logical session reacquired and Goal accepted* | 5/5 | 0.886753 / 0.932142 / 1.200063* |

Key timing:

- F0 cancel -> HORUS cancel topic: `0.900 / 3.572 / 6.654 ms`; cancel -> A terminal: `22.251 / 24.738 / 29.866 ms`; cancel -> verified 0.5 s stop hold: `735.905 / 738.931 / 758.254 ms`.
- F2 control release -> observed lease removal: `0.848 / 1.209 / 1.882 ms`. Cancel topic, Nav2 `CANCELING`, terminal state, and stop were absent throughout all five measurement windows.
- F3 control release/disconnect -> observed lease removal: `0.537 / 0.920 / 2.925 ms`. Cancel topic, Nav2 `CANCELING`, terminal state, and stop were absent throughout all five measurement windows.
- F4 control inactive -> TTL expiry: `946.773 / 1439.974 / 1481.202 ms`; expiry -> natural success: `3836.037 / 3878.639 / 4488.081 ms`. A verified stop occurred in-window in 4/5; the remaining trial had already reached `SUCCEEDED` but its 0.5 s stop-hold check was right-censored at observation end.
- F5 A release -> B lease grant: `28.922 / 29.527 / 34.890 ms`; A release -> B Goal acceptance: `71.712 / 74.696 / 95.923 ms`; B send -> A `ABORTED`: `19.472 / 30.370 / 35.977 ms`.

## Actual Nav2 versus the prior dummy ActionServer

| Question | Prior dummy | Canonical actual Nav2 result |
|---|---|---|
| Release / disconnect / TTL revokes an accepted Action | No | Still no: F2--F4 reproduced the propagation gap |
| A release alone stops robot execution | No | No: actual controller continued and `/odom` increased |
| B handoff leaves A and B simultaneously active | Yes | No: actual Nav2 preempted A in 5/5; A became `ABORTED`, B became `EXECUTING` |
| Explicit HORUS cancel works | Yes | Yes: F0 canceled and stopped in 5/5 |

Therefore, the old-goal continuation after authority revocation is not explained solely by the dummy ActionServer. The prior simultaneous-active A/B handoff result, however, does not generalize to stock Nav2: Nav2 preemption masks that specific dummy behavior once B sends a new Goal. Preemption is not evidence that A's earlier lease revocation propagated, because no cancel occurred before B arrived.

## Interpretation guardrails

- The XR client is a deterministic state machine implementing OpenXR-style lifecycle transitions. It did not receive real OpenXR runtime, Quest focus, headset-removal, or application-pause events. F1 shows that HORUS does not learn an unexported XR event; that alone is not a vulnerability.
- F2--F4 establish a software end-to-end mismatch: HORUS authority/lease state changed, but the already accepted actual Nav2 Goal received no corresponding cancel and produced further simulated odometry.
- Nav2 and its `NavigateToPose` action/controller behavior are actual software. `nav2_loopback_sim` is a kinematic plant that integrates `cmd_vel`; it does not model physical inertia, braking, wheel slip, collision dynamics, sensor noise, actuator faults, or a robot safety controller. Distances above are valid loopback-simulation distances, not physical-robot distance predictions.
- F2 and F3 distances are 5 s right-censored lower bounds. F5/F6 distances include motion under the newly accepted Goal and must not be attributed entirely to A's stale Goal.
- F5 demonstrates stock Nav2 preemption, not owner-correct revocation. A terminated as `ABORTED`, not as an authority-bound `CANCELED` Goal.
- In a post-measurement integrity check, ordinary HORUS cancellation of B missed in 5/5 and direct ROS Action cancel-all cleaned B in 5/5. Cleanup fallback events are excluded from all case metrics. This is consistent with the fixed adapter's late-A-result / single-`active_goal_handle` race, not proof of a production fix.
- In F6, the public Goal command has no session/lease epoch field. A stale client was blocked while B owned the live lease, then the old logical session identifier could reacquire after B released and send a Goal. This is an epoch-capability gap probe, not proof of cryptographic packet replay or authentication bypass.
- `35/35 clean` means all measurements completed without trial errors and all cleanup checks found no active Goal. It does not mean every security expectation passed.

## Evidence integrity and routing

The event timeline records share run ID `xr-nav2-20260826T125755Z`, paired `wall_utc` and `monotonic_ns` timestamps, and monotonically increasing sequence numbers `1..32997`. The two per-trial summary logs carry that run ID in their nested `started_at` / event metadata rather than a top-level `run_id` field.

| Evidence | Records | SHA-256 | Purpose |
|---|---:|---|---|
| [`xr_mock_timeline.log`](./xr_mock_timeline.log) | 32,997 | `1108870c60533aaf7cdad3c97aee37281a37238747c66b5a14c7596322ba8afd` | Event-level XR, lease, UUID status/feedback, `cmd_vel`, `/odom`, cleanup timeline |
| [`nav2_revocation_runtime.log`](./nav2_revocation_runtime.log) | 30 | `8fb5cbffd2c909b7e0fde9be9b654ff0a2171751b3cdffbd05188059f71d71f1` | F0--F4 and F6 per-trial measurements |
| [`nav2_handoff_runtime.log`](./nav2_handoff_runtime.log) | 5 | `4c82afd5cad559eeee5e1b59121fdf9ad2475f97eb6f74247a0d361c2240db4e` | F5 UUID-bound handoff/preemption measurements |

Canonical conclusion: **CONDITIONAL GO**. Actual Nav2 strengthens the revocation-to-execution mismatch result and rejects the dummy-only simultaneous-active handoff generalization. A real Quest/OpenXR application run and, separately, a physical-robot safety evaluation remain necessary before either XR-device-specific or physical-distance claims.
