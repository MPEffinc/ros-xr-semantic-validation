# Framework Preparation Protocol V2

## Scope and non-interference

Each verified framework is processed independently in this order:

1. verify repository identity and pin revision;
2. record inclusion and lineage;
3. map the native source-to-downstream dataflow;
4. map raw semantic and canonical transition confidence;
5. locate the first relevant native decision/gate;
6. write injection/downstream boundary records;
7. create an isolated, disposable environment;
8. build and run synthetic production-path validation where feasible;
9. create replay adapter only after boundary classification;
10. integrate O3 Pi observer when actual ROS2 is applicable;
11. prepare original native consumer dry-run when feasible;
12. prepare Quest runbook/preflight, or record an exact blocker;
13. record result, tests, and Git milestone.

Do not change upstream production behavior to make it observable or safe: do not add
missing tracking fields, publisher gates, recovery policy, timestamp policy, or a production
transport schema field. Prefer detached monitor, wrapper, side-band logger, callback hook,
or observer. If source instrumentation is unavoidable, record original SHA, exact patch,
behavior-changing status, and non-interference checks. A behavior-changing output run is not
a semantic validation finding.

## Required framework package

For source-verified targets, use `semantic_validation/frameworks/<id>/`:

```text
manifest.yaml
PINNED_REVISION
SOURCE_MAP.md
SEMANTIC_MAP.md
INJECTION_BOUNDARY.md
DOWNSTREAM_BOUNDARY.md
README_RUN.md
setup/
harness/
replay/
instrumentation/
tests/
```

Upstream clone, build products, and large raw logs remain ignored; upstream source is never
committed into this repository. The manifest records original URL/SHA, not copied source.

## Source-map completion rule

`SOURCE_MAP.md` must trace the connected production path, not isolated grep hits:

```text
Native XR API
  → XR semantic state
  → first native semantic decision/gate
  → pose/control representation
  → serialization
  → transport/bridge
  → ROS publication
  → original downstream consumer
  → driver/actuator pre-write boundary
```

For every applicable link record file, function/class, field/message, source line and commit,
semantic transformation, and evidence for registration/scene/prefab/config/callback linkage.
If a link cannot be connected, stop at `SOURCE_PATH_UNCONFIRMED`; do not infer production
path from a token search.

## Injection boundary record

Before an adapter exists, `INJECTION_BOUNDARY.md` answers all of these:

- relevant native semantic source and raw field;
- first native decision/gate;
- chosen injection point;
- native logic that remains active;
- native logic bypassed;
- `UPSTREAM_FAITHFUL_REPLAY` or `BOUNDARY_LIMITED_REPLAY` classification;
- resulting evidence limitation.

An adapter may generate only the representation actually consumed by the framework. It may
not fabricate a raw native field absent from that framework. Loss of semantic in that
representation is a documented boundary fact, not a reason to extend the protocol schema.

## Isolation and safety

Isolation priority is: existing container, framework-specific container, Python venv,
isolated ROS workspace, host package only when unavoidable and justified. Unity projects use
a disposable staging directory. Do not alter host ROS/network configuration.

Never connect a physical motor/robot/actuator, launch an unknown robot driver, use arbitrary
sudo, chmod the Docker socket, disable firewall, modify research LAN `enp4s0`, persistently
modify host routing, copy private keys, commit secrets, force-push, or delete canonical
evidence. Privileged/manual needs are `BLOCKED_*` records, not workarounds.

## O3 and O4 preparation

Where ROS2 path is real, O3 may use the dedicated Desktop DDS → Ethernet → Pi
`semantic_robot_sink` route. It records only actual reception. For O4, prefer original
controller callback/MoveIt-Servo target acceptance/trajectory decision/driver pre-write
method connected to a mock, stub, or no-op backend. If original consumer cannot be run,
record `NATIVE_CONSUMER_UNAVAILABLE`, not a simulated replacement as native acceptance.

## Quest-ready package

Only verified commands are placed in a framework runbook. Where supported, package:

```text
verify_preflight.sh  start_backend.sh  start_pi_sink.sh
start_native_consumer.sh  start_logger.sh  collect_logs.sh  stop_all.sh
README_RUN.md  EXPERIMENT_T0.md  EXPERIMENT_T1.md  EXPERIMENT_T4.md
EXPERIMENT_T5.md  EXPECTED_OBSERVABLES.md
```

Absence of a verified command is an explicit blocker, not a guessed shell command. `R5
QUEST_READY` means only that the authenticated/authorized actual Quest session can be run;
it does not create an E5/E6 finding.

## Status and milestone requirements

Allowed preparation status: `READY`, `BLOCKED_ENV`, `BLOCKED_DEPENDENCY`,
`BLOCKED_PLATFORM`, `BLOCKED_HW`, `NOT_APPLICABLE`, `SOURCE_PATH_UNCONFIRMED`.
Do not turn a blocker into `PASS`.

At meaningful milestones run relevant tests, inspect `git status` and `git diff`, perform a
secret/large-file check, then commit/push and verify local/remote SHA if external Git access
is available. Never reset, rewrite history, force-push, or delete existing user changes.
