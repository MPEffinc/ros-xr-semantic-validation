# S4-B runtime qualification

Status: **PARTIAL**. Qualification root: `runs/s4b_qualification_20260922T142928Z/`.
This is an environment/function qualification, not a B0–B3 defense comparison.
No defense ranking, method-gap decision, Quest run, physical robot, or S5 work was performed.

## 1. Frozen protocol and implementation identity

XRROS-S4-1.0.0 was verified before execution. The SHA-256 was
`3a40337121f8d687dc68036ff2ffc85a1bc6eda275a700ba7d9e8119cd322969`,
matching the detached file. The protocol, thresholds, recovery policies and
success criteria were not edited.

The tested implementation was the official
`autonomy-and-verification-uol/ROSMonitoring` repository at
`d03aa5b44e29b76c0e108a098817bdf5aa98e322`, package 3.0.0. It was mounted
read-only and installed into disposable Humble/Jazzy containers. The existing
`docker_teleop_sim` and `openvr_sim` containers were not modified or stopped.

## 2. Humble and Jazzy execution

| Item | Humble | Jazzy |
| --- | --- | --- |
| Base image | `docker-teleop-humble:local` (`ce5200f…`) | `openvr-jazzy-sim:local` (`73c0291…`) |
| Python/test environment | 3.10.12; pytest 8.3.3 | 3.12.3; Debian pytest 7.4.4 |
| Official generator + colcon integration test | PASS, 1 test | PASS, 1 test |
| Actual oracle connection | PASS | PASS |
| `PoseStamped` handling | PASS in official ordered-topic test | PASS in same test |
| filter allow/block | PASS | PASS |
| remap and transient-local verdict QoS | PASS | PASS |

The first Humble attempt failed before the monitor assertion because the base
image lacked `example_interfaces`; the retained log shows the missing test
dependency. Installing the distro package in the disposable image made the
unchanged official test pass. Jazzy's Debian-managed PyYAML/pytest were retained
rather than overwritten by pip; exact dependencies are in `environment.txt`.

## 3. Serialization, filter, oracle and failure behavior

An additional Humble trial generated official monitors for the original
Docker_Teleop `teleop_bridge_msgs/msg/ReceivedPoseStates`. A real WebSocket
oracle allowed `tracked=true` and rejected `tracked=false`; the allowed custom
message was received once and the rejected one was absent downstream. All five
assertions in `edge_probe_03.json` pass.

Oracle failure behavior is **fail-open** in the tested official implementation:

- no oracle at monitor startup: message forwarded with `verdict_raw=unknown`;
- connection closed after one positive response: the following message was
  forwarded; the empty receive was normalized as a non-negative verdict;
- oracle accepted but did not respond: after the configured 50 ms socket
  timeout, `oracle_error` was logged and the message was forwarded as unknown.

The hang trial's measured publisher-to-subscriber interval was about 51.5 ms,
consistent with the 50 ms configured socket timeout. This behavior is not a
final defense-performance result; it means the frozen safety policy cannot use
the unmodified B2 failure path as fail-closed.

Runs 01 and 02 are retained as fixture-debug evidence. Run 01 omitted
`publishers: [source]`, producing observation-only monitors with no `_mon`
subscriber. Run 02 fixed remapping but its fixture incorrectly looked for a
nested `data.tracked`; official custom-message events are flat, so it rejected
both messages. Run 03 corrected the oracle fixture and passed.

## 4. Source-state-command lineage

The qualification-only carrier in `lineage/contract_probe.jsonl` demonstrates
an exact explicit foreign-key scheme: sample ID, generation ID, native state,
source timestamp and repeat index survive from one source sample to every
derived command; the invalid sample produces no command and re-arm uses a new
generation. This validates the log contract only.

It does **not** qualify the original control paths. Static schema verification
shows why: `ReceivedPoseStates` has `tracked`, ROS header and a free-form source
string but no sample/generation ID; `TargetTwistStates` has a newly generated
header and selected booleans but no source timestamp or ID; downstream
`TwistStamped` likewise has no lineage fields. OpenVR's production
`PoseStamped` path also has no native `bPoseIsValid`/`eTrackingResult` or source
sample ID. Consequently exact source-to-repeated-command linkage is
**BLOCKED_INTEGRATION** until a non-defensive observational overlay or parallel
lineage channel is integrated and equivalence is measured. Approximate time
joining was not relabelled as exact lineage.

## 5. Docker stop/re-arm

No new Gazebo trial completed in this qualification root. Source inspection
still confirms the original chain's mechanisms: receiver stale timeout emits a
neutral state, mapper requires tracked state and resets its position session on
inactive input, bridge republishes zero `TwistStamped` when stale/untracked, and
a teleop false→true edge recaptures the reference. Prior S2 synthetic evidence
showed motion, tracked-false/timeout halt and reconnect reference capture, but
that evidence is not a new S4-B qualification PASS.

The intended isolated follow-up was blocked when the execution platform refused
further Docker access after the successful ROSMonitoring runs because its
approval usage limit had been reached. Docker stop/re-arm qualification is
therefore **BLOCKED_ENV**, not failed and not PASS.

## 6. OpenVR stop/re-arm

No new OpenVR/Gazebo trial completed. Prior S3 evidence establishes only that
the unmodified program publishes while valid, gates `bPoseIsValid=false`, and
drops `eTrackingResult`. It does not qualify the frozen explicit/automatic
re-arm policies or measure an active stop against the 300 ms joint-settling
criterion. Inspection of prior logs identifies `/servo_node/pause_servo`, but a
new trial was required to establish API type, pending trajectory behavior,
actual joint settling and `/start_servo` re-arm. This item is **BLOCKED_ENV**.

Docker zero-twist behavior and OpenVR pose/trajectory cessation are not treated
as equivalent.

## 7. Clock and common start barrier

The local two-process primitive in `timing/start_barrier_probe.json` passed:
recorder-ready preceded release and the sender emitted only after release, all
on `CLOCK_MONOTONIC`. This validates the harness primitive, not ROS recorder or
Gazebo integration. Cross-container boot ID, monotonic offset, sender/monitor/
consumer timestamp capture, common initial joint tolerance and recorder-ready
ACK were not measured after Docker access became unavailable. The full item is
therefore **BLOCKED_ENV**.

ROS header/source time and storage/monotonic time remain separate domains. No
direct subtraction across domains was used.

## 8. Qualification decisions

| Required decision | Result | Basis |
| --- | --- | --- |
| A. Humble ROSMonitoring | PASS | Official generator/build/integration test and custom-message filter executed |
| B. Jazzy ROSMonitoring | PASS | Official generator/build/integration test executed |
| C. Exact source-state-command linkage | BLOCKED | Carrier works, but original message schemas erase IDs/source time before repeated commands |
| D. Docker stop/re-arm | BLOCKED | New Gazebo trial not executed after environment access refusal |
| E. OpenVR stop/re-arm | BLOCKED | New Gazebo trial and Servo API response not executed |
| F. Equal initial state/common barrier | BLOCKED | Local primitive passes; ROS/Gazebo/container integration unverified |
| G. Full protocol metrics/policy applicability | BLOCKED | C–F are prerequisites; no B0–B3 comparison may start |

## 9. Evidence and exclusions

Commands and exact environments are in `commands.txt` and `environment.txt`.
Primary evidence is under `stdout/`, `stderr/`, `rosmonitoring/humble/`,
`lineage/`, `timing/` and `analysis/`; hashes are in
`input_manifest.sha256` and `evidence_manifest.sha256`.

Failed/redundant generated workspaces 01/02 and the successful workspace's
colcon build/install/log plus duplicate message source were excluded:

| Local path | Size (`du -sb`) | Tree-manifest SHA-256 | Reason |
| --- | ---: | --- | --- |
| `.../edge_ws_01/` | 4,407,467 B | `b770f15f10fdf34a8d54218a4db3389109a169c010b398a77b5ca7393d7253c2` | failed fixture generated workspace |
| `.../edge_ws_02/` | 4,407,687 B | `048433410dfe3f73d9c8a92ac94f5662f62ee12bc560ec41ddc30aeb79d71ce5` | failed fixture generated workspace |
| `.../edge_ws_03/` | 4,407,687 B | `b9de0565110d7508d61cfdb30835255cd9f2e0289b3f496ff377303ffad2cb02` | build/install/log and duplicate message source excluded; generated official monitor source retained |

The hashes are SHA-256 over the sorted per-file SHA-256 manifest, not a hash of
a tar archive. The directories remain local under the qualification root
(ignored `build/`, `install/`, `log/` subtrees); a partial recoverable copy of
run 01 also exists at `/tmp/s4b_qualification_20260922T142928Z_excluded/` after
an ownership-limited move attempt. No credential, private key, APK, rosbag or
large binary is included.

## 10. Comparison readiness

**NOT_READY.** B0–B3 comparison must not start until exact observational
lineage is integrated without adding a defense to B0 and equivalence is shown;
Docker and OpenVR stop/re-arm trials pass their respective policy bounds; and
the recorder/joint-state common barrier plus cross-container clocks are
measured. ROSMonitoring itself is runnable in both target ROS distributions,
but its measured fail-open oracle-error behavior must be handled transparently
under the preregistered policy rather than silently counted as a safe block.
