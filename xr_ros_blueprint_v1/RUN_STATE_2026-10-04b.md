# Run state: round 2026-10-04b (admitted delay, distant late trajectory, trust/permission/bypass)

This file is the progress log of the approved round, not research context.

| Item | Value |
|---|---|
| Start | 2026-10-04 07:05 KST; base 25b3279 (ff from 41a9fc1) |
| Budget | ≤ 8 h active; ≤ 66 scheduled formal trials; ≤ 72 formal attempts incl. invalid reruns (1A 18, 1B 6, M19 18, M12D/M17 24) |
| Formal ledger | 1A 18 · 1B 6 · M19 18 · M12D/M17 24 = **66/66 scheduled, 66 attempts, all valid, 0 reruns** |
| Probe/pre-flight ledger | 1A PF1–2 (6e5000f); 1B PF1–4 (e1f7201, 33fa310); M19 keys + PF1–PF19 (6ae3d38…8bd6465) + transport probes d1–d4; A04 socket probe (0755 ×1, 0777 ×2); M17 4 hung runs (7f6a177, raw deleted) + PF1–PF5 (795377f) |
| Execution rule | each campaign runs a `git archive` snapshot of its freeze commit (hash-verified per trial) |
| Resources created | no new image (M19/M17 use m3-ordering-mux:v1); SROS2 keystores under ignored M19_acl/run_snapshot/<sha>/keys |

## Steps

| Step | State | Freeze | Raw | Report |
|---|---|---|---|---|
| 1A M7 admitted delay | done | a810226 | experiments/M7_admit/raw (73 MB, 542 files) | R24 → R26 |
| 1B distant late trajectory | done | cb0eca9 | experiments/M3_far/raw (34 MB, 262 files) | R25 → R26 |
| 2 trust-boundary map + M18 audit | done (audit + probe) | — | audits/A04_probe | A04, A05 |
| 3 M19 controller access control | done | 7462f76 | experiments/M19_acl/raw (15 MB, 416 files) | R27 → R29 |
| 4 M12D/M17 false provenance | done | ce74cfe | experiments/M17_derive/raw (9.6 MB, 263 files) | R28 → R30 |
| 5 contract table | done | — | — | R31 |

## Log
- 07:05 ff to 25b3279 (clean). No applicable AGENTS.md (only archived upstream copies).
- 07:07–07:09 R24 pre-flight; 07:10 freeze a810226; 07:10–07:28 formal 18/18.
- 07:30–07:40 R25 pre-flight (stamped message rejected by JTC; zero-stamp variant); 07:41 freeze cb0eca9; formal 6/6.
- 07:44–08:01 M19 pre-flight iterations (domain, robot_description, policy service, cross-uid transport, payload repeat); two leftover trial containers of this experiment stopped (identified by mounts); 08:02 freeze 7462f76; formal 18/18.
- 08:05–08:12 A04 code audit and socket probe; A05 audit by a read-only subagent.
- 08:13–08:22 M17 pre-flight (first attempt hung; raw deleted); freeze ce74cfe; formal 24/24.
- End state: all approved steps complete; stopped at completion.

## Raw preservation

All raw data are on the same disk only (`/home`, nvme0n1p6) under ignored `experiments/*/raw/`. The hash lists are in each `results/`. A same-disk copy is not a recovery guarantee.

## Environment changes

No host change and no new image. Containers of this round run with `--network none` and are removed after use.
The other teams' containers were not touched.
