# authority_continuity — Research Workspace

Working title (tentative, not a claim):
**Security Consistency Across Dynamic XR-ROS Control Authority and Robot Execution**

Candidate question (a hypothesis to be *refuted or confirmed*, not a presumed gap):

> When several XR operators control one ROS robot, and control authority is released, expires,
> is reassigned, or a connection is recovered, do (1) the XR session's authority state, (2) the
> bridge's command-admission state, and (3) the commands ROS has already accepted and the robot's
> actual execution state remain consistent?

## Evidence labels used throughout

| Label | Meaning |
|---|---|
| `AUTHOR_CLAIM` | Stated by a paper's authors; cited with section/page/URL. |
| `SOURCE_CONFIRMED` | Read in source code at a pinned commit (path, function, lines given). |
| `HYPOTHESIS` | Our conjecture; not yet tested. |
| `EXPERIMENT_CONFIRMED` | Observed in an experiment run **in this workspace**, with inputs/outputs/hashes. |
| `NOT_VERIFIED` | Could not be checked (no access, no artifact, not run). |
| `PRIOR_INTERNAL` | Result from the archived project in `../Deprecated/`; background only. |

Experiment outcomes: `PASS` / `FAIL` / `UNKNOWN` / `NOT_RUN`.

## Relationship to the archived work (`../Deprecated/`)

1. **S1–S5 semantic-validation track** (`Deprecated/semantic_validation/`): closed with
   S5 = **NO_METHOD_GAP for the tested conditions**. This workspace does not extend that
   methodology (semantic validation of teleoperation command streams).
2. **Overlap that must be disclosed.** The archived August-2026 tracks
   `Deprecated/AUTHORIZATION_CONTINUITY_RESULTS.md`, `Deprecated/DECISIVE_FOLLOWUP_RESULTS.md`,
   `Deprecated/XR_NAV2_FEASIBILITY_RESULTS.md` and `Deprecated/XR2ACT_DECISIVE_RESULTS.md` already
   studied HORUS lease semantics at the **same** `horus_ros2` commit `eca75cbf` (still upstream
   HEAD on 2026-09-29) and concluded **WEAK / CASE-STUDY ONLY**. The candidate question above is
   substantially the same problem family. Those results are `PRIOR_INTERNAL`: they inform what to
   check, but they are **not** new results of this workspace and are not re-labeled as such.
3. Archived data and harnesses may be reused as a testbed. Any reuse is recorded with the
   archived path and hash; archived files are never edited.
4. **Novelty of this item is undetermined.** A framework is developed only if PHASE 3–5 establish
   an independent, unresolved gap (see `hypotheses/GO_NO_GO.md`).

## Layout

| Path | Content |
|---|---|
| `RESEARCH_PLAN.md` | Phases, gates, kill criteria |
| `STATUS.md` | Per-phase status, commits, push verification |
| `literature/` | Key papers, verified citation graph, limitation matrix, source ledger |
| `audit/` | Architecture, trust boundaries, HORUS code audit, existing defenses |
| `hypotheses/` | Problem definition, threat model, RQs, GO/NO-GO |
| `experiments/` | Protocol, baselines, harness, tests (only if gated in) |
| `results/` | Run outputs (summaries + hashes; raw outputs in ignored `results/raw/`) |
| `references/` | Notes; upstream checkouts go in ignored `references/upstream/` |
