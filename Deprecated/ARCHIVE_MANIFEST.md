# Archive Manifest — Deprecated XR-ROS Semantic-Validation Research

Archived: 2026-09-29 (KST)
Archived by: Hyojoong Ju (with Claude Code)
Backup tag (pre-move, pushed to origin): `archive/pre-authority-continuity-20260929`
  - tag object `6c27e2e9b4d76aaca9cdd73cafe51da414a0467e` → commit `e7799a7dc9b4b6734b44b1816cad7bd5d593843c`

## Status of the archived research item

- The archived research item is **closed**.
- S5 evidence audit verdict: **NO_METHOD_GAP for the tested conditions**
  (`Deprecated/semantic_validation/results/S5_EVIDENCE_AUDIT.md`,
  sha256 `5cfcaed22ff5548f1aa4a34c82308e22af071c7064f240d8aaa59b7e6560878e`, matches
  its `.sha256` sidecar).
- S6/S7 were **not started**. Frozen S4 protocols, qualification/formal results, logs and hash
  sidecars are preserved byte-for-byte. Nothing was re-run, regenerated or reclassified.

## What was done

Every pre-existing root entry except `.git/` was moved **unchanged** into `Deprecated/`.
Tracked content was moved with `git mv` (history follows via rename detection, e.g.
`git log --follow Deprecated/<path>`). Ignored/local-only content was moved with `mv` on the
same filesystem (rename; inodes preserved, no copy). **No archived file content was edited.**

Path mapping (old → new):

| Old path | New path | Tracked? | Notes |
|---|---|---|---|
| `.gitignore` | `Deprecated/.gitignore` | tracked | Git applies it relative to `Deprecated/`, so archived ignore semantics are unchanged (verified). A new root `.gitignore` was written. |
| `AUTHORIZATION_CONTINUITY_RESULTS.md` | `Deprecated/AUTHORIZATION_CONTINUITY_RESULTS.md` | tracked | |
| `DECISIVE_FOLLOWUP_RESULTS.md` | `Deprecated/DECISIVE_FOLLOWUP_RESULTS.md` | tracked | |
| `EXPERIMENT_RESULTS.md` | `Deprecated/EXPERIMENT_RESULTS.md` | tracked | |
| `RESEARCH_CONTEXT.md` | `Deprecated/RESEARCH_CONTEXT.md` | tracked | |
| `ROS_SETUP.md` | `Deprecated/ROS_SETUP.md` | tracked | |
| `TESTBED_CONTEXT.md` | `Deprecated/TESTBED_CONTEXT.md` | tracked | |
| `XR2ACT_DECISIVE_RESULTS.md` | `Deprecated/XR2ACT_DECISIVE_RESULTS.md` | tracked | |
| `XR_BRIDGE_ANALYSIS.md` | `Deprecated/XR_BRIDGE_ANALYSIS.md` | tracked | |
| `XR_NAV2_FEASIBILITY_RESULTS.md` | `Deprecated/XR_NAV2_FEASIBILITY_RESULTS.md` | tracked | |
| `quest_wireless_adb.sh` | `Deprecated/quest_wireless_adb.sh` | tracked | |
| `run_no_quest_validation.sh` | `Deprecated/run_no_quest_validation.sh` | tracked | |
| `authorization_env/` | `Deprecated/authorization_env/` | tracked (16 files) + ignored `__pycache__` | |
| `evidence/` | `Deprecated/evidence/` | tracked (19 files) | |
| `ros_env/` | `Deprecated/ros_env/` | tracked (9 files) + ignored build/install/log + nested `ros_tcp_endpoint` checkout | |
| `semantic_validation/` | `Deprecated/semantic_validation/` | tracked (132,945 files) + ignored logs/targets/pycache | ~20 GB on disk |
| `frameworks/` | `Deprecated/frameworks/` | ignored (never tracked) | 5 nested upstream checkouts (HORUS, HORUS SDK, horus_ros2, COMPAS XR ×2) |
| `local_artifacts/` | `Deprecated/local_artifacts/` | ignored | Quest APKs/builds, local only |
| `.cache/` | `Deprecated/.cache/` | ignored | Raspberry Pi image + install logs, local only |

Not moved (not project content): `.git/`; the empty local tool-state directories `.agents/`,
`.claude/`, `.codex/` (0 files each, never tracked; they are agent-tool config locations, now
ignored by the root `.gitignore`).

## Relative paths inside archived documents

Archived documents cite paths relative to the **old root** (e.g. `semantic_validation/results/...`,
`frameworks/horus_ros2/...`). They were intentionally **not rewritten**. Resolve any such path by
prefixing `Deprecated/`. Several `.sha256` sidecars list root-relative paths
(`semantic_validation/...`); verify them with `Deprecated/` as the working directory.

## Local-only material (not in Git, preserved on this machine only)

- `Deprecated/semantic_validation/logs/quest_hw/` — raw Quest 3 hardware JSONL captures (~307 MB;
  one file > 100 MB GitHub limit). sha256 of these and `local_artifacts/` files:
  `Deprecated/ARCHIVE_VERIFICATION/local_only_raw_sha256.txt` (57 files, all re-verified OK after move).
- `Deprecated/semantic_validation/targets/` — 19 nested upstream target checkouts;
  `Deprecated/frameworks/` — 5; `Deprecated/ros_env/ros2_ws/src/ros_tcp_endpoint/` — 1.
  URL + HEAD SHA of each: `Deprecated/ARCHIVE_VERIFICATION/nested_upstream_checkouts.txt`
  (all clean: 0 dirty entries). These remain untracked; no nested `.git` was imported.
- `Deprecated/semantic_validation/targets/spes_teleop/teleop/{key,cert}.pem` — upstream-provided
  TLS test material inside an ignored checkout. **Never tracked, never pushed.**
- Superseded/failed diagnostic runs listed in `Deprecated/.gitignore`.

## Preservation verification (performed 2026-09-29, before commit)

| Check | Before | After | Result |
|---|---|---|---|
| Tracked files (`git ls-files`) | 133,001 | 133,001 | equal |
| `git ls-files -s` (mode + blob SHA + path, `Deprecated/` prefix stripped), sha256 of listing | `ddd3eaaf…62bb` | `ddd3eaaf…62bb` | **identical** — every tracked blob unchanged |
| `git status` after move | — | 133,001 `R` (pure renames), 0 modified | pass |
| Ignored file set (prefix stripped), sha256 of sorted list | `2ef642e2…b5afb` (2,818 files) | same | **identical** |
| Untracked-but-visible files | 0 | 0 | equal (no ignored content newly exposed) |
| All 143 tracked `.sha256` sidecars (`sha256sum -c`) | 135 pass / 8 fail | 135 pass / 8 fail, identical per-file outcome (sha256 of outcome list `958a01af…97`) | **unchanged** |
| Local-only raw files (57) sha256 | recorded | all OK | pass |
| Filesystem (inode, size, mtime) of 154,135 files incl. ignored + nested `.git` | recorded | 154,131 identical | see note |

Note on the 4 stat differences: `.git/index` of four nested third-party checkouts
(`ros_tcp_endpoint`, `homebrew_vr_teleop`, `unity_ros_teleoperation`, `xarm_quest_teleop`) got a
new inode/mtime at 2026-09-29 21:12:21 KST — i.e. **before** the move (21:14), caused by the
read-only `git status` used to record their HEAD/dirty state (git refreshes its stat cache).
Sizes are identical and working trees are clean; no evidence file is involved.

The 8 pre-existing sidecar failures (not caused by this archive) and their causes:

| Sidecar | Cause observed before the move |
|---|---|
| `results/S4B_CP13_D3_Q3_QUALIFICATION_PROTOCOL.sha256` | bare hash without filename (format), not checkable by `sha256sum -c` |
| `results/runs/s1_trace_audit_20260922T075316Z/input_manifest.sha256` | references `../../hw_picknik_native_...` inputs relative to a different working directory |
| `results/runs/s2_docker_baseline_20260922T080640Z/input_manifest.sha256` | references `inputs/` relative to a different working directory |
| `results/runs/s4b_cp14_d3q4_20260928T015843Z/working_inputs.sha256` | working-copy inputs later edited within that run (as named) |
| `results/runs/s4b_cp18_d4q1_20260928T050614Z/preflight/q6_inputs_copied.sha256` | lists bare filenames of copied inputs relative to another directory |
| `results/runs/s4b_cp4b_preflight_20260923T044458Z/preflight_manifest.sha256` | `commands.jsonl`/`commands.txt` appended after the preflight snapshot |
| `results/runs/s4b_cp5b_measurement_20260923T054101Z/runtime_documents.sha256` | includes the living `SEMANTIC_VALIDATION_STATUS.md` |
| `results/runs/s4b_ovr_formal_20260928T192004Z/freeze_inputs.sha256` | lists a `__pycache__/*.pyc` that is ignored and not present |

These are recorded, not repaired, to avoid altering archived evidence.

Key evidence hashes after the move (sha256):

- `semantic_validation/results/S5_EVIDENCE_AUDIT.md` `5cfcaed22ff5548f1aa4a34c82308e22af071c7064f240d8aaa59b7e6560878e`
- `semantic_validation/results/S4B_CP29_CMON_FORMAL_FREEZE.md` `f2ef49f2a5040eb578c324819f6321ffe181b19f85485d2679f85f6573860bb7`
- `semantic_validation/results/S4B_OVR_FORMAL_FREEZE.md` `ab0f7d260925835922de508458564cb08c8bc69f946a094600240e190ef86122`

Per-file sidecar outcomes: `Deprecated/ARCHIVE_VERIFICATION/sha256_manifest_outcomes.txt`.

## Relationship to the new research

See `/README.md` and `/authority_continuity/`. Archived data is background evidence and a reusable
testbed only; it is not new experimental evidence.
