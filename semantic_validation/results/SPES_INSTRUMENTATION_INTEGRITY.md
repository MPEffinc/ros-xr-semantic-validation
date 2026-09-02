# Spes instrumentation integrity

## Result

**`INSTRUMENTATION_NON_INTERFERENCE_PASS`**

The canonical post-classifier-fix frontend and server observer passed independent
frontend and server differential checks without starting a server or using XR
hardware.  For the tested semantic inputs, the observation/operator layer did
not change the production `type:"pose"` bytes, send decision, callback result,
exception behavior, or `Teleop` control state.

Canonical run:
`spes_instrumentation_integrity_20260831T152759Z` (2026-08-31 15:27:59 UTC,
2026-09-01 00:27:59 KST).

The final integrated suite regenerated the frontend and repeated this differential as
`semantic_validation_20260831T153536Z/artifacts/instrumentation_integrity/dedicated`;
it also returned `INSTRUMENTATION_NON_INTERFERENCE_PASS` with the same source/generated
hashes. The final manifest generation time is `2026-08-31T15:35:48.789684+00:00`.

## Fixed source and artifact

- Upstream target: Spes `teleop` commit
  `c5d808155a87b584d6147a5943d4b87c34c92db0`.
- Upstream checkout: clean before and after the run.
- Upstream frontend SHA-256:
  `a15aca4a417eee3814bf24f190559c20ad234b486c1d96920750dc9027fe9596`.
- Upstream server SHA-256:
  `699c49fd016f3faf8d6625b15bde394d991f4e307d842cce3cbaf2ac735dbea4`.
- Generated frontend SHA-256:
  `5c7f2ae3e27c1d39c67bdf3b365022ea32fcf415d88a56ccf8986c03ea54bb96`.
- Semantic logger source/generated SHA-256:
  `8a117f03b7fac22ba68b70e7040c22788bab747b2fc725c3deba2b74012586c0`.
- Quest operator source/generated SHA-256:
  `5aacab70ad87d1577e54d99b31c5b9d9d303b12543e17f9fcd630c6898533ba9`.
- Manifest generation time: `2026-08-31T15:20:13.064372+00:00`.
- Cache buster: `5aacab70ad87d157`.

All manifest hashes matched the files on disk.  Calling the generator's pure
`instrument()` function in memory produced bytes identical to the canonical
generated `index.html`; no generated or upstream file was rewritten by this
integrity run.  All tracked source/artifact hashes were unchanged from run
start to run end.

## Frontend payload differential

The new matrix executed the actual upstream and generated inline WebXR
applications in matched Node VM sandboxes.  Comparison was performed on the
raw serialized production-WebSocket messages, not only parsed objects.

| Case | Pose sends | Send times (ms) | Result |
| --- | ---: | --- | --- |
| VR, controller pose, all controller fields | 1 | `20` | exact bytes equal |
| VR, controller null, viewer fallback | 1 | `20` | exact bytes equal |
| non-VR viewer, all UI fields | 1 | `20` | exact bytes equal |
| no controller/viewer pose | 0 | none | same fail-to-send decision |
| production WebSocket not connected | 0 | none | same fail-to-send decision |
| strict `time-lastSendTime > 10` boundary | 2 | `11, 22` | same throttle decision |
| controller state progression | 3 | `20, 40, 60` | exact bytes equal |

Across all seven cases:

- outer packet keys and serialized bytes were identical;
- the production data key set remained exactly `position`, `orientation`,
  `move`, `gripper`, `fps`, `scale`, `reservedButtonA`, `reservedButtonB`,
  `device`, and `message`;
- pose/orientation and `move`, gripper, scale, reserved buttons, device, FPS,
  and message values were identical;
- local UI state passed to `updateLocalStats` was identical;
- no experiment, phase, trial, classification, source, tracking,
  `emulatedPosition`, control index, or server ACK field appeared in a pose
  payload;
- the existing two-case frontend equivalence self-test also passed, including
  emulated-controller and controller-null/viewer-fallback paths.

## `Teleop.__update` wrapper differential

Two fresh, non-networked `Teleop` instances received deep-copied identical
messages.  One used the pristine bound class method; the other used the actual
`ServerObserver` instance wrapper, whose `original_update` binding was verified
to be the same upstream class method.

Twelve sequential trials covered:

- `move=false` notification/reset;
- first anchor and ordinary motion;
- `scale == 1`, `scale > 1`, and `scale < 1`;
- a small orientation change;
- jump rejection;
- automatic re-anchor and subsequent motion;
- gripper/reserved/device metadata;
- missing-`move` and missing-`position` exception parity.

Every trial had identical return/exception behavior, user callback count,
callback target matrix, callback message, and private control state
(`relative_pose_init`, `absolute_pose_init`, `previous_received_pose`, and
`pose`).  Neither input copy was mutated.  The jump-reject case emitted zero
user callbacks in both instances; all corresponding later re-anchor behavior
also matched.

Additional wrapper checks:

- the wrapper source contains one delegation call to `original_update`;
- the upstream class method object and source hash were unchanged before/after;
- the upstream server file hash was unchanged before/after;
- 12 wrapper update records and 12 side-band ACKs were produced;
- each observer `callback_emitted` flag matched the independent user callback;
- the existing observer self-test also passed its callback/jump/reset/ACK
  sequence.

## Evidence

- Machine summary:
  [`summary.json`](../logs/instrumentation_integrity/spes_instrumentation_integrity_20260831T152759Z/summary.json)
- Independent raw records:
  [`integrity.jsonl`](../logs/instrumentation_integrity/spes_instrumentation_integrity_20260831T152759Z/integrity.jsonl)
- Observer's own side-band records:
  [`server_observer.jsonl`](../logs/instrumentation_integrity/spes_instrumentation_integrity_20260831T152759Z/server_observer.jsonl)
- Frontend matrix harness:
  [`spes_payload_equivalence_matrix.mjs`](../harness/spes_payload_equivalence_matrix.mjs)
- Integrity orchestrator:
  [`spes_instrumentation_integrity.py`](../harness/spes_instrumentation_integrity.py)

Reproduce without starting the live server:

```bash
cd /home/cclab/ros_xr
PYTHONPATH=/tmp/ros_xr_semantic_deps \
  python3 semantic_validation/harness/spes_instrumentation_integrity.py
```

## Limitations

- Frontend execution used deterministic WebXR/WebSocket/browser test doubles
  around the actual application source.  It proves tested payload and send
  equivalence, not zero CPU/GPU overhead or identical scheduling on every
  browser/device.
- Server comparison invoked the actual control method directly without a live
  WSS endpoint.  It proves method/wrapper behavior for the 12-case sequence,
  not every possible malformed value or concurrency interleaving.
- ACK delivery used an in-process capture function; asynchronous client
  rendering and network overhead were outside this check.
- No conclusion about tracking semantics follows from this integrity test.  It
  only rules out the tested instrumentation paths as the cause of the observed
  production payload/control behavior.
- No live server, Quest session, ROS sink, robot, or hardware driver was started
  or changed.
