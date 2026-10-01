# Archive Manifest — closed research workspaces (2026-10-01)

Archived: 2026-10-01 (KST), on branch `research/xr-ros-evidence-framework`
(base `main` = `25423a71c19f1ef74a0a8154d095336d6fe0559a`).
Archived by: Hyojoong Ju (with Claude Code).

Purpose: clear the repository root before the new `semantic_evidence_framework/` workspace is
created. **Nothing was deleted or edited.** Two closed workspaces were moved, unchanged, into this
directory. Everything else stays where it was.

## 1. Inventory of root entries before the move

| Root entry (on this branch) | Purpose | Status | Action |
|---|---|---|---|
| `Deprecated/` | Archive of the S1–S5 semantic-validation research and the August-2026 reports | closed; already an archive (`Deprecated/ARCHIVE_MANIFEST.md`) | **not moved** (no double archiving) |
| `authority_continuity/` | *Security consistency across dynamic XR-ROS control authority* (HORUS) | closed 2026-09-29: **IMPLEMENTATION_GAP_ONLY** (`hypotheses/GO_NO_GO.md` PHASE 7) | **moved here** |
| `xr_demo_integrity/` | *Integrity of XR-teleoperation demonstrations for robot learning* | closed 2026-09-30: **NO_REAL_THREAT_BOUNDARY** (`results/FINAL_REPORT.md`) | **moved here** |
| `README.md`, `.gitignore` | live root navigation and ignore rules | live | kept; README links updated, ignore rules **appended** (old lines kept) |
| `.git`, `.agents/`, `.claude/`, `.codex/` | git and agent-tool config | not research | not touched |
| `experiments/` | — | **does not exist on this branch** | see §4 |

## 2. Path mapping (old → new)

| Old path | New path | Tracked | Local-only (ignored) content moved with it |
|---|---|---|---|
| `authority_continuity/` | `archive/2026-10-01_closed_research/authority_continuity/` | 31 files (`git mv`, R100) | `references/upstream/` (2 checkouts), `results/raw/` (Phase-6 logs) |
| `xr_demo_integrity/` | `archive/2026-10-01_closed_research/xr_demo_integrity/` | 22 files (`git mv`, R100) | `references/upstream/` (5 checkouts), `references/papers/` |

Commit history follows with `git log --follow archive/2026-10-01_closed_research/<path>`.

## 3. How local-only content was preserved

The move was done in a separate worktree, `/home/cclab/ros_xr_evidence`, because the primary
checkout `/home/cclab/ros_xr` is on `research/n1-predictive-execution-mismatch` and holds N1/cross-flow
ignored data that would surface as untracked files on this branch.

1. The ignored directories listed in §2 were **copied** (`cp -a`) from `/home/cclab/ros_xr/<old path>`
   into the worktree at the *old* paths. The 7,917 regular files and 53 symlinks were hash-compared:
   identical.
2. `git mv` then renamed both directories, so the ignored content moved with them.
3. **The originals in `/home/cclab/ros_xr/<old path>` were left in place**, because that checkout's
   branch still uses the old layout. Both copies are identical (same per-file sha256 listing).

## 4. `experiments/` (exists only on other branches)

`experiments/` is not part of `main` or of this branch. It exists on
`research/n1-predictive-execution-mismatch` (`6ea081ec3c16601b92cdec5072d630ec1f710950`), which also
contains `research/crossflow-gap-validation` as an ancestor. It holds two closed items:

| Path (on that branch) | Verdict | Decision file |
|---|---|---|
| `experiments/crossflow_gap_validation_2026-09-30/` | **KILL** (2026-09-30) | `DECISION.md` |
| `experiments/n1_predictive_execution_mismatch/` | **IMPLEMENTATION_GAP_ONLY → KILL** (2026-09-30) | `DECISION.md` |

They were **not merged or copied** into this branch: the instructions say not to merge closed research
to read it. Read them with `git show 6ea081ec3:experiments/<path>`. Their local-only data stays in the
primary checkout:

- `/home/cclab/ros_xr/experiments/n1_predictive_execution_mismatch/results/raw/` (62 MB) and `ws/`
  (16 MB). `results/formal_raw_sha256.txt` verifies **50/50 OK** with cwd `results/raw/formal/`, and
  `results/analysis_sha256.txt` verifies 2/2 OK with cwd at the N1 directory (checked 2026-10-01).
- `/home/cclab/ros_xr/experiments/crossflow_gap_validation_2026-09-30/results/raw/` (608 KB, pcap/csv).

## 5. Preservation verification (2026-10-01, before commit)

Files are in `ARCHIVE_VERIFICATION/`.

| Check | Before | After | Result |
|---|---|---|---|
| `git ls-files -s` (mode, blob, path; prefix stripped), 53 entries | `ee3b9b51…7115` | `ee3b9b51…7115` | **identical**; `git diff --cached -M`: 53 × R100, 0 modified |
| Local-only raw + papers (130 files) sha256 | `local_only_raw_and_papers_sha256.txt` | same | identical |
| Nested upstream checkouts, all regular files (7,787 incl. `.git`), per-file sha256 listing digest | `a2cf5ce8…baea` | `a2cf5ce8…baea` | identical; 7 checkouts clean, HEADs in `nested_upstream_checkouts.txt` |
| Symlinks in local-only trees (53) | listed | same targets | identical |
| Key evidence (`PHASE6_*`, `phase6_verdicts.json`, both `GO_NO_GO.md`, `FINAL_REPORT.md`) | sha256 | sha256 | identical |
| `PHASE6_RAW_SHA256.txt` (cwd `results/raw/`) | 72/72 OK | 72/72 OK | unchanged |
| 6 × `results/raw/*/inputs.sha256` | per-line outcomes | identical per-line outcomes (via old-root view, below) | unchanged |
| `references/papers_sha256.txt` (cwd `references/papers/`) | 16/16 OK | 16/16 OK | unchanged |
| `Deprecated/` | — | 0 changes in `git diff --cached` | untouched |

### Pre-existing sidecar failures (not caused by this move)

The four `smoke_*/inputs.sha256` files fail on `experiments/PROTOCOL.md` (all four) and
`experiments/harness/ac_probe.py` (three of them). Those files were edited after the smoke runs
and before the formal freeze. The two formal `ac6_formal_*/inputs.sha256` files pass 6/6. All 7 FAILED
lines were present before the move and are recorded, not repaired
(`sidecar_outcomes_before.txt`).

## 6. How to read archived paths and hashes

- Archived documents keep their **original** relative paths and hash records. They were not rewritten.
- `inputs.sha256` lists **old-repository-root** paths, mixing `authority_continuity/...` and
  `Deprecated/...`. Run it from a directory that recreates the old root. For example:

  ```bash
  V=$(mktemp -d); W=/home/cclab/ros_xr_evidence
  ln -s $W/archive/2026-10-01_closed_research/authority_continuity $V/
  ln -s $W/archive/2026-10-01_closed_research/xr_demo_integrity   $V/
  ln -s $W/Deprecated $V/
  cd $V && sha256sum -c authority_continuity/results/raw/ac6_formal_main/inputs.sha256
  ```

  If you run it from `archive/2026-10-01_closed_research/` directly, the `Deprecated/...` lines are
  reported missing. That is a path-resolution effect, not a content change.
- Links like `../Deprecated/...` inside the moved workspaces now resolve one level too shallow. Read them
  as `../../Deprecated/...` from the workspace root, and `../../../Deprecated/...` from a subdirectory
  that used `../../Deprecated/`. Their target content is unchanged.
- `scripts/run_phase6.sh` and `scripts/fetch_upstreams.sh` locate themselves through `dirname`, so
  they still work from the new location. The Docker images they use
  (`ros-xr-horus-nav2-jazzy:local` and others) are host-local and unaffected.

## 7. Verdicts preserved (cite as PRIOR_INTERNAL; not new results)

- S5 (`Deprecated/`): NO_METHOD_GAP for the tested synthetic Docker and fake-OpenVR conditions; S6/S7 not run.
- authority_continuity: IMPLEMENTATION_GAP_ONLY.
- xr_demo_integrity: NO_REAL_THREAT_BOUNDARY.
- cross-flow: KILL. N1: IMPLEMENTATION_GAP_ONLY → KILL. Both on the N1 branch, §4.
