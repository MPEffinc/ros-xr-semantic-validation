# Quest2ROS2 actual ROS 2 transport validation

## Result

**`BLOCKED_ENV` — actual ROS 2 transport was not executed in this session.**

The current unprivileged shell can run the Docker client, but cannot connect to
the configured Docker daemon socket.  Per the experiment rules, no `sudo`,
socket permission change, group change, or approval request was attempted.
Consequently, the existing `F-Q2R-001/002` evidence level remains
`CONFIRMED_RUNTIME_SYNTHETIC_SOURCE`; it is **not** upgraded to
`ACTUAL ROS2 TRANSPORT + ACTUAL NODE` by this run.

Canonical probe run:
`quest2ros2_ros_runtime_20260831T150939Z` (2026-08-31 15:09:39 UTC,
2026-09-01 00:09:39 KST).

## Environment evidence

| Check | Observation | Status |
| --- | --- | --- |
| `id` | `uid=1000(cclab) gid=1000(cclab) groups=1000(cclab),65534(nogroup)` | observed |
| Docker socket | `/var/run/docker.sock`, `srw-rw----`, `nobody:nogroup`, mode `0660` | observed |
| Docker client | 29.1.3, API 1.52, default context | available |
| `docker info` | `permission denied while trying to connect to the docker API` | `BLOCKED_ENV` |
| `docker images` | same daemon permission failure | inventory unavailable, not evidence of absence |
| `docker ps -a` | same daemon permission failure | inventory unavailable, not evidence of absence |
| Docker Compose | 2.40.3; `ros_env/compose.yaml` parses successfully | client/config available |
| Compose project state | daemon socket `operation not permitted` | runtime state unavailable |
| Host `ros2` / `colcon` | not found in `PATH` | no host fallback |
| Expected Compose image | config names `ros-xr-humble:local` | configured only; installed-image presence unverified |
| Quest2ROS2 target | `07aaf65149c9e29103f1fc61deb466cef8a55cef` | clean before and after |

The raw command outputs, return codes, identity, socket metadata, Compose
configuration, and target provenance are preserved in
[`environment.jsonl`](../logs/quest2ros2_ros_runtime/quest2ros2_ros_runtime_20260831T150939Z/environment.jsonl).
The machine-readable disposition is
[`summary.json`](../logs/quest2ros2_ros_runtime/quest2ros2_ros_runtime_20260831T150939Z/summary.json).

## Requested transport and age sweep

The requested path was prepared but not executed:

```text
synthetic PoseStamped publisher
  -> actual RightArmController ROS subscription / production callback
  -> actual target PoseStamped publisher
  -> dummy target subscriber
```

| Input | Actual ROS arrival | Callback consumption | Output stamp/frame/pose |
| --- | --- | --- | --- |
| now - 10 ms | `NOT_EXECUTED` | `NOT_EXECUTED` | `NOT_EXECUTED` |
| now - 100 ms | `NOT_EXECUTED` | `NOT_EXECUTED` | `NOT_EXECUTED` |
| now - 500 ms | `NOT_EXECUTED` | `NOT_EXECUTED` | `NOT_EXECUTED` |
| now - 1 s | `NOT_EXECUTED` | `NOT_EXECUTED` | `NOT_EXECUTED` |
| now - 3 s | `NOT_EXECUTED` | `NOT_EXECUTED` | `NOT_EXECUTED` |
| now - 10 s | `NOT_EXECUTED` | `NOT_EXECUTED` | `NOT_EXECUTED` |
| now + 1 s | `NOT_EXECUTED` | `NOT_EXECUTED` | `NOT_EXECUTED` |

Frame-provenance inputs `xr_controller_A`, `xr_controller_B`,
`old_reference_space`, and `new_reference_space` likewise remain
`NOT_EXECUTED` on actual ROS transport.  No result from the older callback-only
test was copied into these cells.

## Robot-free rerun harness

Two Quest2ROS2-only harnesses are ready:

- [`run_quest2ros2_ros_runtime.py`](../harness/run_quest2ros2_ros_runtime.py)
  performs all environment probes, preserves raw output, copies the pinned
  target into a temporary workspace, and starts the test only if the daemon is
  accessible.
- [`quest2ros2_ros_transport_node.py`](../harness/quest2ros2_ros_transport_node.py)
  supplies a dummy static TF, publishes the seven timestamp cases through
  actual ROS topics, records actual subscription arrival and callback entry,
  delegates to the unchanged production callback, and captures the actual
  target subscriber output.

The container run is constrained to `--network none`, `--cap-drop ALL`,
`no-new-privileges`, no device mounts, no host networking, and no robot or
driver.  The callback wrapper records only a side-band entry timestamp before
calling `super()._pose_callback`; the upstream control calculation and output
publisher are not replaced.  The target checkout is copied rather than built
in place.

Syntax validation passed for both Python files.  Container execution remains
unverified because it is downstream of the Docker access blocker.

Rerun, without privileged changes, from an environment that already has
authorized daemon access:

```bash
cd /home/cclab/ros_xr
python3 semantic_validation/harness/run_quest2ros2_ros_runtime.py
```

The harness creates a new immutable evidence directory under
`semantic_validation/logs/quest2ros2_ros_runtime/` and reports `PASS`,
`DISPROVED`, `FAIL`, or `BLOCKED_ENV`.  A future `PASS` is required before any
Quest2ROS2 finding is relabeled as actual ROS 2 transport evidence.

## Scope boundary

- No actual Quest input was used.
- No robot, robot controller, gripper server, or hardware driver was connected.
- No Docker container was started in the canonical blocked run.
- No image/container inventory can be inferred from a permission-denied query.
- No upstream file changed; the pinned target was clean before and after.
- This result neither confirms nor disproves the callback-level stale re-stamp
  finding over DDS.  It records an environment blocker and a safe executable
  path for the missing validation.
